import django_filters
from django.db.models import Q

from .models import Notificacao, TemplateNotificacao


class NotificacaoFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=Notificacao.STATUS_CHOICES)
    tipo = django_filters.ChoiceFilter(choices=Notificacao.TIPO_CHOICES)
    canal = django_filters.UUIDFilter(field_name="canal_id")
    template = django_filters.UUIDFilter(field_name="template_id")
    origem_tipo = django_filters.CharFilter(field_name="origem_tipo", lookup_expr="iexact")
    created_at_after = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    created_at_before = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")
    sent_at_after = django_filters.DateFilter(field_name="sent_at", lookup_expr="date__gte")
    sent_at_before = django_filters.DateFilter(field_name="sent_at", lookup_expr="date__lte")
    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = Notificacao
        fields = [
            "status",
            "tipo",
            "canal",
            "template",
            "origem_tipo",
            "created_at_after",
            "created_at_before",
            "sent_at_after",
            "sent_at_before",
            "search",
        ]

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(destinatario_nome__icontains=value)
            | Q(destinatario_contato__icontains=value)
            | Q(provider_message_id__icontains=value)
        )


class TemplateNotificacaoFilter(django_filters.FilterSet):
    tipo = django_filters.ChoiceFilter(choices=TemplateNotificacao.TIPO_CHOICES)
    canal = django_filters.UUIDFilter(field_name="canal_id")
    ativo = django_filters.BooleanFilter()

    class Meta:
        model = TemplateNotificacao
        fields = ["tipo", "canal", "ativo"]
