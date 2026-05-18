import django_filters

from .models import Cliente


class ClienteFilter(django_filters.FilterSet):
    bloqueado = django_filters.BooleanFilter()
    tipo_pessoa = django_filters.ChoiceFilter(choices=Cliente.TIPO_CHOICES)
    cidade = django_filters.CharFilter(lookup_expr="icontains")
    estado = django_filters.CharFilter(lookup_expr="iexact")
    saldo_devedor__gt = django_filters.NumberFilter(
        field_name="saldo_devedor", lookup_expr="gt"
    )
    saldo_devedor__gte = django_filters.NumberFilter(
        field_name="saldo_devedor", lookup_expr="gte"
    )
    is_active = django_filters.BooleanFilter()
    nome = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Cliente
        fields = [
            "bloqueado",
            "tipo_pessoa",
            "cidade",
            "estado",
            "is_active",
        ]
