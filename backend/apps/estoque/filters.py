import django_filters
from django.db.models import Q

from .models import MovimentacaoEstoque, Produto


class ProdutoFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_search")
    categoria = django_filters.UUIDFilter(field_name="categoria_id")
    fornecedor = django_filters.UUIDFilter(field_name="fornecedor_principal_id")
    unidade = django_filters.UUIDFilter(field_name="unidade_id")
    is_active = django_filters.BooleanFilter()
    estoque_baixo = django_filters.BooleanFilter(method="filter_estoque_baixo")
    preco_venda__gte = django_filters.NumberFilter(field_name="preco_venda", lookup_expr="gte")
    preco_venda__lte = django_filters.NumberFilter(field_name="preco_venda", lookup_expr="lte")

    class Meta:
        model = Produto
        fields = [
            "search",
            "categoria",
            "fornecedor",
            "unidade",
            "is_active",
            "estoque_baixo",
            "preco_venda__gte",
            "preco_venda__lte",
        ]

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(nome__icontains=value)
            | Q(sku__icontains=value)
            | Q(codigo_barras__icontains=value)
            | Q(descricao__icontains=value)
        )

    def filter_estoque_baixo(self, queryset, name, value):
        if value is None:
            return queryset
        from django.db.models import F

        low_stock = queryset.filter(estoque_atual__lte=F("estoque_minimo"))
        if value:
            return low_stock
        return queryset.exclude(pk__in=low_stock.values("pk"))


class MovimentacaoFilter(django_filters.FilterSet):
    produto = django_filters.UUIDFilter(field_name="produto_id")
    tipo = django_filters.ChoiceFilter(choices=MovimentacaoEstoque.TIPO_CHOICES)
    status = django_filters.ChoiceFilter(choices=MovimentacaoEstoque.STATUS_CHOICES)
    fornecedor = django_filters.UUIDFilter(field_name="fornecedor_id")
    created_by = django_filters.UUIDFilter(field_name="created_by_id")
    created_at_after = django_filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_at_before = django_filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = MovimentacaoEstoque
        fields = [
            "produto",
            "tipo",
            "status",
            "fornecedor",
            "created_by",
            "created_at_after",
            "created_at_before",
        ]
