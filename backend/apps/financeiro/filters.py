import django_filters
from django.db.models import Q
from django.utils import timezone

from .models import CaixaDiario, ContaPagar, LancamentoFinanceiro


class LancamentoFinanceiroFilter(django_filters.FilterSet):
    conta_financeira = django_filters.UUIDFilter(field_name="conta_financeira_id")
    categoria = django_filters.UUIDFilter(field_name="categoria_id")
    tipo = django_filters.ChoiceFilter(choices=LancamentoFinanceiro.TIPO_CHOICES)
    status = django_filters.ChoiceFilter(choices=LancamentoFinanceiro.STATUS_CHOICES)
    origem_tipo = django_filters.ChoiceFilter(choices=LancamentoFinanceiro.ORIGEM_CHOICES)
    forma_pagamento = django_filters.ChoiceFilter(choices=LancamentoFinanceiro.FORMA_CHOICES)
    data_lancamento_after = django_filters.DateFilter(
        field_name="data_lancamento",
        lookup_expr="date__gte",
    )
    data_lancamento_before = django_filters.DateFilter(
        field_name="data_lancamento",
        lookup_expr="date__lte",
    )
    valor_gte = django_filters.NumberFilter(field_name="valor", lookup_expr="gte")
    valor_lte = django_filters.NumberFilter(field_name="valor", lookup_expr="lte")
    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = LancamentoFinanceiro
        fields = [
            "conta_financeira",
            "categoria",
            "tipo",
            "status",
            "origem_tipo",
            "forma_pagamento",
            "data_lancamento_after",
            "data_lancamento_before",
            "valor_gte",
            "valor_lte",
            "search",
        ]

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(descricao__icontains=value)
            | Q(conta_financeira__nome__icontains=value)
            | Q(categoria__nome__icontains=value)
            | Q(idempotency_key__icontains=value)
        )


class ContaPagarFilter(django_filters.FilterSet):
    fornecedor = django_filters.UUIDFilter(field_name="fornecedor_id")
    categoria = django_filters.UUIDFilter(field_name="categoria_id")
    status = django_filters.ChoiceFilter(choices=ContaPagar.STATUS_CHOICES)
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
    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = ContaPagar
        fields = [
            "fornecedor",
            "categoria",
            "status",
            "situacao",
            "data_vencimento_before",
            "data_vencimento_after",
            "valor_restante_gte",
            "valor_restante_lte",
            "search",
        ]

    def filter_situacao(self, queryset, name, value):
        if not value:
            return queryset
        value = value.lower()
        if value == "parcial":
            return queryset.filter(
                status=ContaPagar.STATUS_ABERTA,
                valor_pago__gt=0,
                valor_restante__gt=0,
            )
        if value == "atrasada":
            return queryset.filter(
                status=ContaPagar.STATUS_ABERTA,
                data_vencimento__lt=timezone.localdate(),
                valor_restante__gt=0,
            )
        return queryset

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(descricao__icontains=value)
            | Q(observacao__icontains=value)
            | Q(fornecedor__razao_social__icontains=value)
            | Q(fornecedor__nome_fantasia__icontains=value)
            | Q(categoria__nome__icontains=value)
        )


class CaixaDiarioFilter(django_filters.FilterSet):
    data = django_filters.DateFilter(field_name="data")
    status = django_filters.ChoiceFilter(choices=CaixaDiario.STATUS_CHOICES)
    conta_financeira = django_filters.UUIDFilter(field_name="conta_financeira_id")

    class Meta:
        model = CaixaDiario
        fields = ["data", "status", "conta_financeira"]
