import django_filters
from django.db.models import Q

from .models import BoletoOCR


class BoletoOCRFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=BoletoOCR.STATUS_CHOICES)
    tipo_arquivo = django_filters.ChoiceFilter(choices=BoletoOCR.TIPO_CHOICES)
    fornecedor = django_filters.UUIDFilter(field_name="fornecedor_id")
    conta_pagar = django_filters.UUIDFilter(field_name="conta_pagar_id")
    vencimento_after = django_filters.DateFilter(field_name="vencimento", lookup_expr="gte")
    vencimento_before = django_filters.DateFilter(field_name="vencimento", lookup_expr="lte")
    valor_gte = django_filters.NumberFilter(field_name="valor", lookup_expr="gte")
    valor_lte = django_filters.NumberFilter(field_name="valor", lookup_expr="lte")
    confianca_lte = django_filters.NumberFilter(field_name="confianca_ocr", lookup_expr="lte")
    created_at_after = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    created_at_before = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")
    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = BoletoOCR
        fields = [
            "status",
            "tipo_arquivo",
            "fornecedor",
            "conta_pagar",
            "vencimento_after",
            "vencimento_before",
            "valor_gte",
            "valor_lte",
            "confianca_lte",
            "created_at_after",
            "created_at_before",
            "search",
        ]

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(fornecedor_nome__icontains=value)
            | Q(banco_nome__icontains=value)
            | Q(linha_digitavel__icontains=value)
            | Q(codigo_barras__icontains=value)
            | Q(arquivo_nome_original__icontains=value)
        )
