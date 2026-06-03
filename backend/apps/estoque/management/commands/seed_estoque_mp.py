"""
Seed operacional de estoque — MP Construções.

Popula o sistema com produtos, formas de venda e estoque inicial reais,
facilitando testes de PDV, Fiado, Estoque, Financeiro, Relatórios, Cobranças e NF-e.

Idempotente: pode ser executado múltiplas vezes sem duplicar registros.

Uso:
    python manage.py seed_estoque_mp
"""

from decimal import Decimal
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.estoque.models import CategoriaProduto, FormaVendaProduto, Produto, UnidadeMedida
from apps.estoque.services.forma_venda import criar_forma_venda, inativar_forma_venda
from apps.estoque.services.movimentacao import entrada_estoque
from apps.estoque.services.produto import create_produto

D = Decimal
ADMIN_EMAIL = "admin@mp.com"


def _fmt_comp(c: Decimal) -> str:
    """Formata comprimento para exibição: 3 → '3', 2.5 → '2,5'."""
    if c == c.to_integral_value():
        return str(int(c))
    return str(c).replace(".", ",")


class Command(BaseCommand):
    help = "Seed de estoque operacional da MP Construções (idempotente)"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stats: dict[str, int] = {
            "categorias": 0,
            "unidades": 0,
            "produtos": 0,
            "formas": 0,
            "entradas": 0,
        }

    def handle(self, *args, **options):
        try:
            user = User.objects.select_related("company").get(
                email=ADMIN_EMAIL,
                deleted_at__isnull=True,
                is_active=True,
            )
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Usuário {ADMIN_EMAIL} não encontrado ou inativo."))
            return

        if not user.company_id:
            self.stderr.write(self.style.ERROR("Usuário não possui empresa vinculada."))
            return

        self.stdout.write(self.style.SUCCESS(f"\nEmpresa: {user.company}"))
        self.stdout.write("=" * 60)

        with transaction.atomic():
            unidades = self._setup_unidades(user)
            categorias = self._setup_categorias(user)
            self._setup_cimento(user, unidades, categorias)
            self._setup_argamassas(user, unidades, categorias)
            self._setup_tintas(user, unidades, categorias)
            self._setup_caibros(user, unidades, categorias)
            self._setup_ripas(user, unidades, categorias)
            self._setup_linhas(user, unidades, categorias, "3x5")
            self._setup_linhas(user, unidades, categorias, "3x6")
            self._setup_brita(user, unidades, categorias)

        self._print_relatorio()

    # ── Helpers genéricos ──────────────────────────────────────────────────────

    def _get_or_create_unidade(self, user, sigla: str, nome: str) -> UnidadeMedida:
        obj = UnidadeMedida.objects.filter(
            company=user.company, sigla=sigla, deleted_at__isnull=True
        ).first()
        if obj:
            return obj
        obj = UnidadeMedida(company=user.company, sigla=sigla, nome=nome, descricao="")
        obj.full_clean()
        obj.save()
        self._stats["unidades"] += 1
        self.stdout.write(f"  + Unidade: {sigla}")
        return obj

    def _get_or_create_categoria(self, user, nome: str) -> CategoriaProduto:
        obj = CategoriaProduto.objects.filter(
            company=user.company, nome=nome, deleted_at__isnull=True
        ).first()
        if obj:
            return obj
        obj = CategoriaProduto(company=user.company, nome=nome, descricao="")
        obj.full_clean()
        obj.save()
        self._stats["categorias"] += 1
        self.stdout.write(f"  + Categoria: {nome}")
        return obj

    def _get_or_create_produto(
        self, user, sku: str, data: dict[str, Any]
    ) -> tuple[Produto, bool]:
        existing = Produto.objects.filter(
            company=user.company, sku=sku.upper(), deleted_at__isnull=True
        ).first()
        if existing:
            return existing, False
        produto = create_produto(user=user, data={**data, "sku": sku})
        self._stats["produtos"] += 1
        self.stdout.write(f"  + Produto:  {produto.nome}")
        return produto, True

    def _get_or_create_forma(
        self, user, produto: Produto, data: dict[str, Any]
    ) -> tuple[FormaVendaProduto, bool]:
        existing = FormaVendaProduto.objects.filter(
            company=user.company,
            produto=produto,
            nome=data["nome"],
            deleted_at__isnull=True,
        ).first()
        if existing:
            return existing, False
        forma = criar_forma_venda(user=user, produto=produto, data=data)
        self._stats["formas"] += 1
        return forma, True

    def _inativar_forma_unidade_padrao(self, user, produto: Produto) -> None:
        """Inativa a forma genérica 'Unidade' criada automaticamente pelo backend."""
        tem_outras = (
            FormaVendaProduto.objects.filter(
                company=user.company,
                produto=produto,
                ativo=True,
                deleted_at__isnull=True,
            )
            .exclude(nome="Unidade")
            .exists()
        )
        if not tem_outras:
            return
        generica = FormaVendaProduto.objects.filter(
            company=user.company,
            produto=produto,
            nome="Unidade",
            ativo=True,
            deleted_at__isnull=True,
        ).first()
        if generica:
            inativar_forma_venda(user=user, forma_venda=generica)

    def _entrada_se_zerado(self, user, produto: Produto, quantidade: Decimal) -> None:
        """Registra entrada de estoque somente se o produto estiver zerado."""
        produto.refresh_from_db(fields=["estoque_atual"])
        if produto.estoque_atual > D("0"):
            return
        entrada_estoque(
            user=user,
            produto=produto,
            quantidade=quantidade,
            motivo="Estoque inicial — seed_estoque_mp",
        )
        self._stats["entradas"] += 1
        self.stdout.write(
            f"    → Entrada: {quantidade} {produto.unidade.sigla}"
        )

    def _setup_madeira(
        self,
        user,
        sku: str,
        nome: str,
        comprimento: Decimal,
        pecas: int,
        categoria: CategoriaProduto,
        unidade_m: UnidadeMedida,
    ) -> None:
        """Cria produto de madeira com formas Metro e Peça completa."""
        label = _fmt_comp(comprimento)
        estoque_inicial = comprimento * pecas
        estoque_minimo = comprimento * 5  # 5 peças mínimas

        produto, _ = self._get_or_create_produto(user, sku, {
            "nome": nome,
            "categoria": categoria,
            "unidade": unidade_m,
            "preco_compra": D("0.00"),
            "preco_venda": D("0.00"),
            "estoque_minimo": estoque_minimo,
        })

        self._get_or_create_forma(user, produto, {
            "nome": "Metro",
            "unidade": "M",
            "fator_conversao": D("1"),
            "preco_venda": D("0.00"),
            "permite_fracionado": True,
            "padrao": False,
        })
        self._get_or_create_forma(user, produto, {
            "nome": f"Peça {label}m",
            "unidade": "PÇ",
            "fator_conversao": comprimento,
            "preco_venda": D("0.00"),
            "permite_fracionado": False,
            "padrao": True,
        })
        self._inativar_forma_unidade_padrao(user, produto)
        produto.refresh_from_db()
        self._entrada_se_zerado(user, produto, estoque_inicial)

    # ── Setup de unidades e categorias ────────────────────────────────────────

    def _setup_unidades(self, user) -> dict[str, UnidadeMedida]:
        self.stdout.write("\nUNIDADES")
        return {
            "KG":   self._get_or_create_unidade(user, "KG",   "Quilograma"),
            "SACO": self._get_or_create_unidade(user, "SACO", "Saco"),
            "UN":   self._get_or_create_unidade(user, "UN",   "Unidade"),
            "LATA": self._get_or_create_unidade(user, "LATA", "Lata"),
            "M":    self._get_or_create_unidade(user, "M",    "Metro"),
            "M3":   self._get_or_create_unidade(user, "M3",   "Metro Cúbico"),
        }

    def _setup_categorias(self, user) -> dict[str, CategoriaProduto]:
        self.stdout.write("\nCATEGORIAS")
        return {
            "Cimento":   self._get_or_create_categoria(user, "Cimento"),
            "Argamassa": self._get_or_create_categoria(user, "Argamassa"),
            "Tintas":    self._get_or_create_categoria(user, "Tintas"),
            "Madeira":   self._get_or_create_categoria(user, "Madeira"),
            "Brita":     self._get_or_create_categoria(user, "Brita"),
        }

    # ── Setup por categoria ────────────────────────────────────────────────────

    def _setup_cimento(self, user, unidades, categorias) -> None:
        self.stdout.write("\nCIMENTO")
        produto, _ = self._get_or_create_produto(user, "CIM-50KG", {
            "nome": "Cimento 50kg",
            "categoria": categorias["Cimento"],
            "unidade": unidades["KG"],
            "preco_compra": D("38.00"),
            "preco_venda": D("44.00"),
            "estoque_minimo": D("500"),
        })
        # KG — venda fracionada
        self._get_or_create_forma(user, produto, {
            "nome": "KG",
            "unidade": "KG",
            "fator_conversao": D("1"),
            "preco_venda": D("0.90"),
            "permite_fracionado": True,
            "padrao": False,
        })
        # Saco 50kg — padrão
        self._get_or_create_forma(user, produto, {
            "nome": "Saco 50kg",
            "unidade": "SACO",
            "fator_conversao": D("50"),
            "preco_venda": D("44.00"),
            "permite_fracionado": False,
            "padrao": True,
        })
        self._inativar_forma_unidade_padrao(user, produto)
        produto.refresh_from_db()
        # 100 sacos × 50 KG = 5.000 KG
        self._entrada_se_zerado(user, produto, D("5000"))

    def _setup_argamassas(self, user, unidades, categorias) -> None:
        self.stdout.write("\nARGAMASSAS")
        tipos = [
            ("ARG-ACI-15KG",   "Argamassa AC-I 15kg",   D("14.00")),
            ("ARG-ACII-15KG",  "Argamassa AC-II 15kg",  D("22.00")),
            ("ARG-ACIII-15KG", "Argamassa AC-III 15kg", D("32.00")),
        ]
        for sku, nome, preco in tipos:
            produto, _ = self._get_or_create_produto(user, sku, {
                "nome": nome,
                "categoria": categorias["Argamassa"],
                "unidade": unidades["SACO"],
                "preco_compra": (preco * D("0.75")).quantize(D("0.01")),
                "preco_venda": preco,
                "estoque_minimo": D("10"),
            })
            self._get_or_create_forma(user, produto, {
                "nome": "Saco 15kg",
                "unidade": "SACO",
                "fator_conversao": D("1"),
                "preco_venda": preco,
                "permite_fracionado": False,
                "padrao": True,
            })
            self._inativar_forma_unidade_padrao(user, produto)
            produto.refresh_from_db()
            self._entrada_se_zerado(user, produto, D("50"))  # 50 sacos

    def _setup_tintas(self, user, unidades, categorias) -> None:
        self.stdout.write("\nTINTAS")
        # (sku, nome, nome_forma, preco)
        tintas = [
            ("TIN-FORTNIL-900ML", "Tinta Óleo Fortnil 900ml", "Lata 900ml",  D("28.00")),
            ("TIN-FORTNIL-36L",   "Tinta Óleo Fortnil 3,6L",  "Galão 3,6L",  D("95.00")),
            ("TIN-IQUINE-900ML",  "Tinta Óleo Iquine 900ml",  "Lata 900ml",  D("35.00")),
            ("TIN-IQUINE-36L",    "Tinta Óleo Iquine 3,6L",   "Galão 3,6L",  D("125.00")),
        ]
        for sku, nome, forma_nome, preco in tintas:
            produto, _ = self._get_or_create_produto(user, sku, {
                "nome": nome,
                "categoria": categorias["Tintas"],
                "unidade": unidades["UN"],
                "preco_compra": (preco * D("0.70")).quantize(D("0.01")),
                "preco_venda": preco,
                "estoque_minimo": D("5"),
            })
            self._get_or_create_forma(user, produto, {
                "nome": forma_nome,
                "unidade": "UN",
                "fator_conversao": D("1"),
                "preco_venda": preco,
                "permite_fracionado": False,
                "padrao": True,
            })
            self._inativar_forma_unidade_padrao(user, produto)
            produto.refresh_from_db()
            self._entrada_se_zerado(user, produto, D("20"))  # 20 unidades

    def _setup_caibros(self, user, unidades, categorias) -> None:
        self.stdout.write("\nCAIBROS")
        for comp_int in (3, 4, 5, 6):
            self._setup_madeira(
                user=user,
                sku=f"MAD-CAIBRO-{comp_int}M",
                nome=f"Caibro {comp_int}m",
                comprimento=D(comp_int),
                pecas=30,
                categoria=categorias["Madeira"],
                unidade_m=unidades["M"],
            )

    def _setup_ripas(self, user, unidades, categorias) -> None:
        self.stdout.write("\nRIPAS")
        # (sku_suffix, comprimento decimal, quantidade de peças)
        ripas = [
            ("2",  D("2")),
            ("25", D("2.5")),
            ("3",  D("3")),
            ("35", D("3.5")),
            ("4",  D("4")),
            ("45", D("4.5")),
            ("5",  D("5")),
            ("55", D("5.5")),
        ]
        for suffix, comp in ripas:
            self._setup_madeira(
                user=user,
                sku=f"MAD-RIPA-{suffix}M",
                nome=f"Ripa {_fmt_comp(comp)}m",
                comprimento=comp,
                pecas=50,
                categoria=categorias["Madeira"],
                unidade_m=unidades["M"],
            )

    def _setup_linhas(self, user, unidades, categorias, tipo: str) -> None:
        self.stdout.write(f"\nLINHA {tipo}")
        sku_tipo = tipo.replace("x", "")  # "35" ou "36"
        linhas = [
            ("3",  D("3")),
            ("4",  D("4")),
            ("5",  D("5")),
            ("6",  D("6")),
            ("65", D("6.5")),
        ]
        for suffix, comp in linhas:
            self._setup_madeira(
                user=user,
                sku=f"MAD-LINHA{sku_tipo}-{suffix}M",
                nome=f"Linha {tipo} {_fmt_comp(comp)}m",
                comprimento=comp,
                pecas=20,
                categoria=categorias["Madeira"],
                unidade_m=unidades["M"],
            )

    def _setup_brita(self, user, unidades, categorias) -> None:
        self.stdout.write("\nBRITA")
        produto, _ = self._get_or_create_produto(user, "BRI-M3", {
            "nome": "Brita",
            "categoria": categorias["Brita"],
            "unidade": unidades["M3"],
            "preco_compra": D("120.00"),
            "preco_venda": D("150.00"),
            "estoque_minimo": D("3"),
        })
        # Metro cúbico — padrão e fracionado
        self._get_or_create_forma(user, produto, {
            "nome": "Metro cúbico",
            "unidade": "M3",
            "fator_conversao": D("1"),
            "preco_venda": D("150.00"),
            "permite_fracionado": True,
            "padrao": True,
        })
        # Lata — 1 lata = 0,018 m³
        self._get_or_create_forma(user, produto, {
            "nome": "Lata",
            "unidade": "LATA",
            "fator_conversao": D("0.018"),
            "preco_venda": D("5.00"),
            "permite_fracionado": False,
            "padrao": False,
        })
        self._inativar_forma_unidade_padrao(user, produto)
        produto.refresh_from_db()
        self._entrada_se_zerado(user, produto, D("20"))  # 20 m³

    # ── Relatório final ────────────────────────────────────────────────────────

    def _print_relatorio(self) -> None:
        s = self._stats
        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write(self.style.SUCCESS("SEED CONCLUÍDO"))
        self.stdout.write(f"{'=' * 60}")
        self.stdout.write(f"  Categorias criadas     : {s['categorias']}")
        self.stdout.write(f"  Unidades criadas       : {s['unidades']}")
        self.stdout.write(f"  Produtos criados       : {s['produtos']}")
        self.stdout.write(f"  Formas de venda criadas: {s['formas']}")
        self.stdout.write(f"  Entradas de estoque    : {s['entradas']}")
        self.stdout.write(f"{'=' * 60}")

        if all(v == 0 for v in s.values()):
            self.stdout.write(self.style.WARNING("  ↳ Nenhum registro novo (seed já executado anteriormente)"))
        else:
            self.stdout.write(
                "Estoque populado com produtos reais da MP Construções, "
                "permitindo testes completos de PDV, Fiado, Estoque, Financeiro e Relatórios."
            )
