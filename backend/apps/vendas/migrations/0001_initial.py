import django.db.models.deletion
import django.utils.timezone
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0003_user_company_fk"),
        ("clientes", "0004_cliente_codigo_pais_cliente_contribuinte_icms_and_more"),
        ("empresas", "0002_rename_empresas_em_cnpj_idx_empresas_em_cnpj_fe5b68_idx_and_more"),
        ("estoque", "0005_produto_aliquota_cofins_produto_aliquota_icms_and_more"),
        ("financeiro", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Venda",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("numero", models.CharField(blank=True, max_length=20)),
                ("status", models.CharField(
                    choices=[("CONCLUIDA", "Concluída"), ("CANCELADA", "Cancelada")],
                    default="CONCLUIDA",
                    max_length=20,
                )),
                ("valor_subtotal", models.DecimalField(
                    decimal_places=2, default=Decimal("0.00"), max_digits=14,
                )),
                ("desconto", models.DecimalField(
                    decimal_places=2, default=Decimal("0.00"), max_digits=14,
                )),
                ("valor_total", models.DecimalField(
                    decimal_places=2, default=Decimal("0.00"), max_digits=14,
                )),
                ("forma_pagamento", models.CharField(
                    choices=[
                        ("DINHEIRO", "Dinheiro"),
                        ("PIX", "PIX"),
                        ("CARTAO", "Cartão"),
                        ("TRANSFERENCIA", "Transferência"),
                    ],
                    max_length=20,
                )),
                ("observacao", models.TextField(blank=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("motivo_cancelamento", models.TextField(blank=True)),
                ("company", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="vendas",
                    to="empresas.empresa",
                )),
                ("cliente", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="vendas",
                    to="clientes.cliente",
                )),
                ("conta_financeira", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="vendas",
                    to="financeiro.contafinanceira",
                )),
                ("lancamento_financeiro", models.OneToOneField(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="venda",
                    to="financeiro.lancamentofinanceiro",
                )),
                ("created_by", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="vendas_criadas",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("cancelled_by", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="vendas_canceladas",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"verbose_name": "Venda", "verbose_name_plural": "Vendas", "ordering": ["-created_at"], "abstract": False},
        ),
        migrations.CreateModel(
            name="ItemVenda",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("quantidade_informada", models.DecimalField(decimal_places=3, max_digits=15)),
                ("quantidade", models.DecimalField(decimal_places=3, max_digits=15)),
                ("preco_unitario", models.DecimalField(decimal_places=2, max_digits=14)),
                ("subtotal", models.DecimalField(decimal_places=2, max_digits=14)),
                ("company", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="itens_venda",
                    to="empresas.empresa",
                )),
                ("venda", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="itens",
                    to="vendas.venda",
                )),
                ("produto", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="itens_venda",
                    to="estoque.produto",
                )),
                ("forma_venda", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="itens_venda",
                    to="estoque.formavendaproduto",
                )),
                ("movimentacao_estoque", models.OneToOneField(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="item_venda",
                    to="estoque.movimentacaoestoque",
                )),
            ],
            options={"verbose_name": "Item de Venda", "verbose_name_plural": "Itens de Venda", "ordering": ["-created_at"], "abstract": False},
        ),
        migrations.AddIndex(
            model_name="venda",
            index=models.Index(fields=["company", "status", "created_at"], name="vendas_ve_company_status_idx"),
        ),
        migrations.AddIndex(
            model_name="venda",
            index=models.Index(fields=["company", "numero"], name="vendas_ve_company_numero_idx"),
        ),
        migrations.AddIndex(
            model_name="venda",
            index=models.Index(fields=["company", "cliente", "created_at"], name="vendas_ve_company_cliente_idx"),
        ),
        migrations.AddIndex(
            model_name="venda",
            index=models.Index(fields=["company", "created_at"], name="vendas_ve_company_created_idx"),
        ),
        migrations.AddIndex(
            model_name="itemvenda",
            index=models.Index(fields=["company", "venda"], name="vendas_iv_company_venda_idx"),
        ),
        migrations.AddIndex(
            model_name="itemvenda",
            index=models.Index(fields=["company", "produto"], name="vendas_iv_company_produto_idx"),
        ),
    ]
