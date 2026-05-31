import django_filters
from django.db.models import Q
from django.utils import timezone

from .models import ContaFiado


class ContaFiadoFilter(django_filters.FilterSet):
    cliente = django_filters.UUIDFilter(field_name="cliente_id")
    status = django_filters.ChoiceFilter(choices=ContaFiado.STATUS_CHOICES)
    situacao = django_filters.CharFilter(method="filter_situacao")
    data_vencimento_before = django_filters.DateFilter(
        field_name="data_vencimento",
        lookup_expr="lte",
    )
    data_vencimento_after = django_filters.DateFilter(
        field_name="data_vencimento",
        lookup_expr="gte",
    )
    valor_restante_gte = django_filters.NumberFilter(
        field_name="valor_restante",
        lookup_expr="gte",
    )
    valor_restante_lte = django_filters.NumberFilter(
        field_name="valor_restante",
        lookup_expr="lte",
    )
    created_by = django_filters.UUIDFilter(field_name="created_by_id")
    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = ContaFiado
        fields = [
            "cliente",
            "status",
            "situacao",
            "data_vencimento_before",
            "data_vencimento_after",
            "valor_restante_gte",
            "valor_restante_lte",
            "created_by",
            "search",
        ]

    def filter_situacao(self, queryset, name, value):
        if not value:
            return queryset
        value = value.lower()
        if value == "parcial":
            return queryset.filter(
                status=ContaFiado.STATUS_ABERTA,
                valor_pago__gt=0,
                valor_restante__gt=0,
            )
        if value == "atrasada":
            return queryset.filter(
                status=ContaFiado.STATUS_ABERTA,
                data_vencimento__lt=timezone.localdate(),
                valor_restante__gt=0,
            )
        return queryset

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(cliente__nome__icontains=value)
            | Q(cliente__cpf_cnpj__icontains=value)
            | Q(observacao__icontains=value)
        )
