"""Data migration: cria FormaVendaProduto padrão para todos os produtos existentes.

Para cada produto existente, cria uma única FormaVendaProduto com:
- nome = sigla da unidade de medida do produto
- unidade = sigla da unidade de medida do produto
- fator_conversao = 1
- padrao = True
- ativo = True
- preco_venda = preco_venda do produto

Garante que nenhum produto existente perca sua capacidade de venda.
"""
from decimal import Decimal

from django.db import migrations


def criar_formas_padrao(apps, schema_editor):
    Produto = apps.get_model("estoque", "Produto")
    FormaVendaProduto = apps.get_model("estoque", "FormaVendaProduto")

    formas = []
    for produto in Produto.objects.filter(deleted_at__isnull=True).select_related("unidade"):
        sigla = (produto.unidade.sigla or "UN").strip().upper()
        nome = produto.unidade.nome or sigla
        formas.append(
            FormaVendaProduto(
                company=produto.company,
                produto=produto,
                nome=nome,
                codigo=sigla,
                unidade=sigla,
                fator_conversao=Decimal("1.000000"),
                preco_venda=produto.preco_venda,
                ativo=True,
                padrao=True,
                permite_fracionado=True,
            )
        )

    if formas:
        FormaVendaProduto.objects.bulk_create(formas, ignore_conflicts=False)


def reverter_formas_padrao(apps, schema_editor):
    FormaVendaProduto = apps.get_model("estoque", "FormaVendaProduto")
    FormaVendaProduto.objects.filter(padrao=True, fator_conversao=Decimal("1.000000")).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("estoque", "0002_formavendaproduto"),
    ]

    operations = [
        migrations.RunPython(criar_formas_padrao, reverter_formas_padrao),
    ]
