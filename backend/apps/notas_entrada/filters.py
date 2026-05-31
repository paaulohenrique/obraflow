import django_filters
from django.db.models import Q

from .models import NotaFiscalEntrada


class NotaFiscalEntradaFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=NotaFiscalEntrada.STATUS_CHOICES)
    fornecedor = django_filters.UUIDFilter(field_name="fornecedor_id")
    data_emissao_inicio = django_filters.DateFilter(field_name="data_emissao", lookup_expr="gte")
    data_emissao_fim = django_filters.DateFilter(field_name="data_emissao", lookup_expr="lte")
    valor_total_gte = django_filters.NumberFilter(field_name="valor_total", lookup_expr="gte")
    valor_total_lte = django_filters.NumberFilter(field_name="valor_total", lookup_expr="lte")
    created_at_after = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    created_at_before = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")
    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = NotaFiscalEntrada
        fields = [
            "status",
            "fornecedor",
            "data_emissao_inicio",
            "data_emissao_fim",
            "valor_total_gte",
            "valor_total_lte",
            "created_at_after",
            "created_at_before",
            "search",
        ]

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(numero__icontains=value)
            | Q(fornecedor_nome_xml__icontains=value)
            | Q(fornecedor_cnpj_xml__icontains=value)
            | Q(chave_acesso__icontains=value)
            | Q(fornecedor__razao_social__icontains=value)
        )
