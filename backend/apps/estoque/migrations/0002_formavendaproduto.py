"""Adiciona FormaVendaProduto e campos forma_venda/quantidade_informada em MovimentacaoEstoque."""
import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("estoque", "0001_initial"),
        ("empresas", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="FormaVendaProduto",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("company", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="formas_venda_produto",
                    to="empresas.empresa",
                )),
                ("produto", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="formas_venda",
                    to="estoque.produto",
                )),
                ("nome", models.CharField(max_length=120)),
                ("codigo", models.CharField(blank=True, max_length=40)),
                ("unidade", models.CharField(max_length=20)),
                ("fator_conversao", models.DecimalField(
                    decimal_places=6,
                    max_digits=14,
                    validators=[django.core.validators.MinValueValidator(Decimal("0.000001"))],
                )),
                ("preco_venda", models.DecimalField(
                    decimal_places=2,
                    default=Decimal("0.00"),
                    max_digits=12,
                    validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                )),
                ("ativo", models.BooleanField(default=True)),
                ("padrao", models.BooleanField(default=False)),
                ("permite_fracionado", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Forma de Venda do Produto",
                "verbose_name_plural": "Formas de Venda dos Produtos",
                "ordering": ["-created_at"],
                "abstract": False,
            },
        ),
        migrations.AddConstraint(
            model_name="formavendaproduto",
            constraint=models.UniqueConstraint(
                condition=models.Q(deleted_at__isnull=True, codigo__gt=""),
                fields=["company", "produto", "codigo"],
                name="estoque_unique_forma_venda_codigo",
            ),
        ),
        migrations.AddConstraint(
            model_name="formavendaproduto",
            constraint=models.UniqueConstraint(
                condition=models.Q(deleted_at__isnull=True, padrao=True, ativo=True),
                fields=["company", "produto"],
                name="estoque_unique_forma_venda_padrao_por_produto",
            ),
        ),
        migrations.AddConstraint(
            model_name="formavendaproduto",
            constraint=models.CheckConstraint(
                condition=models.Q(fator_conversao__gt=0),
                name="estoque_forma_venda_fator_gt_zero",
            ),
        ),
        migrations.AddConstraint(
            model_name="formavendaproduto",
            constraint=models.CheckConstraint(
                condition=models.Q(preco_venda__gte=0),
                name="estoque_forma_venda_preco_gte_zero",
            ),
        ),
        migrations.AddIndex(
            model_name="formavendaproduto",
            index=models.Index(fields=["company", "produto", "ativo"], name="estoque_formavendaproduto_company_produto_ativo"),
        ),
        migrations.AddIndex(
            model_name="formavendaproduto",
            index=models.Index(fields=["company", "produto", "padrao"], name="estoque_formavendaproduto_company_produto_padrao"),
        ),
        migrations.AddField(
            model_name="movimentacaoestoque",
            name="forma_venda",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="movimentacoes",
                to="estoque.formavendaproduto",
            ),
        ),
        migrations.AddField(
            model_name="movimentacaoestoque",
            name="quantidade_informada",
            field=models.DecimalField(blank=True, decimal_places=3, max_digits=14, null=True),
        ),
    ]
