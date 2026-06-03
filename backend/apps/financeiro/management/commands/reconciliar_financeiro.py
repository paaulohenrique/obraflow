"""
Reconcilia ContaFinanceira.saldo_atual recalculando a partir dos lançamentos confirmados.

Uso:
    python manage.py reconciliar_financeiro              # aplica correções
    python manage.py reconciliar_financeiro --dry-run    # apenas exibe divergências
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q, Sum

from apps.financeiro.models import ContaFinanceira, LancamentoFinanceiro


ZERO = Decimal("0.00")


def _money(v) -> Decimal:
    return (v or ZERO).quantize(Decimal("0.01"))


class Command(BaseCommand):
    help = "Reconcilia ContaFinanceira.saldo_atual com base nos lançamentos confirmados"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Apenas exibe divergências, sem alterar")

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]

        self.stdout.write(self.style.SUCCESS(
            f"\nReconciliação financeira {'[DRY RUN] ' if dry_run else ''}— {self._ts()}"
        ))
        self.stdout.write("=" * 70)

        contas = ContaFinanceira.objects.filter(
            deleted_at__isnull=True,
            ativo=True,
        ).order_by("company_id", "nome")

        stats = {"contas": 0, "divergentes": 0, "corrigidas": 0, "total_diff": ZERO}

        for conta in contas:
            stats["contas"] += 1
            saldo_calculado = self._calcular_saldo(conta)
            saldo_atual = _money(conta.saldo_atual)

            if saldo_calculado != saldo_atual:
                diff = saldo_calculado - saldo_atual
                stats["divergentes"] += 1
                stats["total_diff"] += abs(diff)
                self.stdout.write(
                    f"  DIVERGÊNCIA  {conta.nome[:35]:<35} "
                    f"atual={saldo_atual:>10.2f}  "
                    f"correto={saldo_calculado:>10.2f}  "
                    f"Δ={diff:>+10.2f}"
                )
                if not dry_run:
                    with transaction.atomic():
                        conta_locked = (
                            ContaFinanceira.objects
                            .select_for_update()
                            .get(pk=conta.pk)
                        )
                        # Bypass da proteção do model (apenas esta função tem permissão)
                        conta_locked._allow_saldo_update = True
                        conta_locked.saldo_atual = saldo_calculado
                        conta_locked.save(update_fields=["saldo_atual", "updated_at"])
                    stats["corrigidas"] += 1

        self.stdout.write("=" * 70)
        self.stdout.write(f"  Contas verificadas : {stats['contas']}")
        self.stdout.write(f"  Com divergência    : {stats['divergentes']}")
        if not dry_run:
            self.stdout.write(f"  Corrigidas         : {stats['corrigidas']}")
        self.stdout.write(f"  Δ total            : R$ {stats['total_diff']:.2f}")

        if dry_run and stats["divergentes"] > 0:
            self.stdout.write(self.style.WARNING("\n  [DRY RUN] Nenhuma alteração aplicada."))
        elif not dry_run:
            self.stdout.write(self.style.SUCCESS("\n  Reconciliação concluída."))
        else:
            self.stdout.write(self.style.SUCCESS("\n  Sem divergências encontradas."))

    def _calcular_saldo(self, conta: ContaFinanceira) -> Decimal:
        """Saldo = soma das ENTRADAS confirmadas − soma das SAÍDAS confirmadas."""
        agg = LancamentoFinanceiro.objects.filter(
            conta_financeira=conta,
            status=LancamentoFinanceiro.STATUS_CONFIRMADO,
            deleted_at__isnull=True,
        ).aggregate(
            entradas=Sum("valor", filter=Q(tipo=LancamentoFinanceiro.TIPO_ENTRADA)),
            saidas=Sum("valor", filter=Q(tipo=LancamentoFinanceiro.TIPO_SAIDA)),
        )
        entradas = _money(agg["entradas"] or ZERO)
        saidas = _money(agg["saidas"] or ZERO)
        return _money(entradas - saidas)

    def _ts(self) -> str:
        from django.utils import timezone
        return timezone.now().strftime("%Y-%m-%d %H:%M:%S")
