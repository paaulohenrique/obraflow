"""Adiciona forma_venda e quantidade_informada ao ItemNotaFiscalEntrada."""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notas_entrada", "0002_alter_itemnotafiscalentrada_options"),
        ("estoque", "0002_formavendaproduto"),
    ]

    operations = [
        migrations.AddField(
            model_name="itemnotafiscalentrada",
            name="forma_venda",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="itens_nota_entrada",
                to="estoque.formavendaproduto",
            ),
        ),
        migrations.AddField(
            model_name="itemnotafiscalentrada",
            name="quantidade_informada",
            field=models.DecimalField(blank=True, decimal_places=3, max_digits=14, null=True),
        ),
    ]
