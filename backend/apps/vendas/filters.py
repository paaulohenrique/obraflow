import django_filters

from .models import Venda


class VendaFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=Venda.STATUS_CHOICES)
    forma_pagamento = django_filters.ChoiceFilter(choices=Venda.FORMA_CHOICES)
    data_inicio = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    data_fim = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model = Venda
        fields = ["status", "forma_pagamento", "data_inicio", "data_fim"]
