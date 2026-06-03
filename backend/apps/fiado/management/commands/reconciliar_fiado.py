"""
Reconcilia saldo_devedor de todos os clientes com base nas contas fiado abertas.

Uso:
    python manage.py reconciliar_fiado              # aplica correções
    python manage.py reconciliar_fiado --dry-run    # apenas mostra divergências
    python manage.py reconciliar_fiado --empresa admin@mp.com
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q, Sum

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.fiado.models import ContaFiado, ItemFiado, PagamentoFiado


ZERO = Decimal("0.00")


def _money(v) -> Decimal:
    return (v or ZERO).quantize(Decimal("0.01"))


class Command(BaseCommand):
    help = "Reconcilia cliente.saldo_devedor com base nos dados reais de fiado"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Apenas exibe divergências, sem alterar")
        parser.add_argument("--empresa", metavar="EMAIL", help="Limitar a um email de admin específico")

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        empresa_email: str | None = options.get("empresa")

        self.stdout.write(self.style.SUCCESS(
            f"\nReconciliação de fiado {'[DRY RUN] ' if dry_run else ''}— {self._ts()}"
        ))
        self.stdout.write("=" * 60)

        # Determina empresas a processar
        if empresa_email:
            users = User.objects.filter(email=empresa_email, is_active=True, deleted_at__isnull=True)
            if not users.exists():
                self.stderr.write(f"Usuário {empresa_email} não encontrado.")
                return
            company_ids = list(users.values_list("company_id", flat=True).distinct())
        else:
            company_ids = list(
                User.objects.filter(is_active=True, deleted_at__isnull=True)
                .exclude(company_id=None)
                .values_list("company_id", flat=True)
                .distinct()
            )

        stats = {"clientes_verificados": 0, "divergentes": 0, "corrigidos": 0, "total_diff": ZERO}

        for company_id in company_ids:
            self._reconciliar_empresa(company_id, dry_run, stats)

        self.stdout.write("=" * 60)
        self.stdout.write(f"  Clientes verificados : {stats['clientes_verificados']}")
        self.stdout.write(f"  Com divergência      : {stats['divergentes']}")
        if not dry_run:
            self.stdout.write(f"  Corrigidos           : {stats['corrigidos']}")
        self.stdout.write(f"  Δ total              : R$ {stats['total_diff']:.2f}")

        if dry_run and stats["divergentes"] > 0:
            self.stdout.write(self.style.WARNING("\n  [DRY RUN] Nenhuma alteração aplicada."))
        elif not dry_run:
            self.stdout.write(self.style.SUCCESS("\n  Reconciliação concluída."))
        else:
            self.stdout.write(self.style.SUCCESS("\n  Sem divergências encontradas."))

    def _reconciliar_empresa(self, company_id, dry_run: bool, stats: dict) -> None:
        clientes = Cliente.objects.filter(company_id=company_id, deleted_at__isnull=True)

        for cliente in clientes:
            stats["clientes_verificados"] += 1
            saldo_calculado = self._calcular_saldo_devedor(cliente, company_id)
            saldo_atual = _money(cliente.saldo_devedor)

            if saldo_calculado != saldo_atual:
                diff = saldo_calculado - saldo_atual
                stats["divergentes"] += 1
                stats["total_diff"] += abs(diff)
                self.stdout.write(
                    f"  DIVERGÊNCIA  {cliente.nome[:40]:<40} "
                    f"atual={saldo_atual:>10.2f}  "
                    f"correto={saldo_calculado:>10.2f}  "
                    f"Δ={diff:>+10.2f}"
                )
                if not dry_run:
                    with transaction.atomic():
                        # Busca com lock para evitar race condition
                        cli_locked = Cliente.objects.select_for_update().get(pk=cliente.pk)
                        cli_locked.saldo_devedor = saldo_calculado
                        cli_locked.save(update_fields=["saldo_devedor", "updated_at"])
                    stats["corrigidos"] += 1

    def _calcular_saldo_devedor(self, cliente: Cliente, company_id) -> Decimal:
        """Soma valor_restante de todas as contas fiado abertas do cliente."""
        contas_abertas = ContaFiado.objects.filter(
            company_id=company_id,
            cliente=cliente,
            status=ContaFiado.STATUS_ABERTA,
            deleted_at__isnull=True,
        )

        total = ZERO
        for conta in contas_abertas:
            # Recalcula a partir dos itens e pagamentos para maior precisão
            itens = _money(
                ItemFiado.objects.filter(
                    conta=conta, company_id=company_id,
                    status=ItemFiado.STATUS_ATIVO, deleted_at__isnull=True,
                ).aggregate(total=Sum("subtotal"))["total"] or ZERO
            )
            pagamentos = _money(
                PagamentoFiado.objects.filter(
                    conta=conta, company_id=company_id,
                    status=PagamentoFiado.STATUS_CONFIRMADO, deleted_at__isnull=True,
                ).aggregate(total=Sum("valor"))["total"] or ZERO
            )
            total += max(ZERO, itens - pagamentos)

        return _money(total)

    def _ts(self) -> str:
        from django.utils import timezone
        return timezone.now().strftime("%Y-%m-%d %H:%M:%S")
