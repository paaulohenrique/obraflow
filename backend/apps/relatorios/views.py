from __future__ import annotations

from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.response import Response

from apps.core.pagination import StandardResultsSetPagination

from .permissions import RelatorioPermission
from .selectors import (
    get_dashboard_executivo,
    get_relatorio_estoque,
    get_relatorio_fiado,
    get_relatorio_financeiro,
    get_relatorio_vendas,
    money,
)
from .services import (
    relatorio_pdf_filename,
    render_relatorio_fiado_pdf,
    render_relatorio_financeiro_pdf,
    render_relatorio_vendas_pdf,
)


class PDFRenderer(BaseRenderer):
    media_type = "application/pdf"
    format = "pdf"
    charset = None

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


def _date_or_none(value):
    if not value:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else value


def _serialize_conta_fiado(conta) -> dict:
    return {
        "id": conta.pk,
        "cliente_id": conta.cliente_id,
        "cliente": conta.cliente.nome,
        "status": conta.status,
        "valor_total": conta.valor_total,
        "valor_pago": conta.valor_pago,
        "valor_restante": conta.valor_restante,
        "data_abertura": conta.data_abertura,
        "data_vencimento": conta.data_vencimento,
        "dias_atraso": conta.dias_atraso,
    }


def _serialize_venda(venda) -> dict:
    return {
        "id": venda.pk,
        "numero": venda.numero,
        "cliente": venda.cliente.nome if venda.cliente_id and venda.cliente else "Consumidor final",
        "valor_total": venda.valor_total,
        "desconto": venda.desconto,
        "forma_pagamento": venda.forma_pagamento,
        "created_at": venda.created_at,
    }


def _serialize_conta_pagar(conta) -> dict:
    return {
        "id": conta.pk,
        "descricao": conta.descricao,
        "fornecedor": str(conta.fornecedor) if conta.fornecedor_id else "",
        "status": conta.status,
        "valor_total": conta.valor_total,
        "valor_pago": conta.valor_pago,
        "valor_restante": conta.valor_restante,
        "data_vencimento": conta.data_vencimento,
        "dias_atraso": conta.dias_atraso,
    }


def _serialize_produto(produto) -> dict:
    return {
        "id": produto.pk,
        "nome": produto.nome,
        "sku": produto.sku,
        "categoria": produto.categoria.nome,
        "estoque_atual": produto.estoque_atual,
        "estoque_minimo": produto.estoque_minimo,
        "custo_medio": produto.custo_medio,
        "valor_estoque": money(produto.estoque_atual * produto.custo_medio),
        "estoque_baixo": produto.estoque_baixo,
    }


class _RelatorioViewSet(viewsets.ViewSet):
    permission_classes = [RelatorioPermission]
    renderer_classes = [JSONRenderer]

    def _company_id(self):
        return getattr(self.request.user, "company_id", None)

    def _filters(self):
        return self.request.query_params.dict()

    def _paginated_payload(self, qs, serializer):
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, self.request, view=self)
        return {
            "count": paginator.page.paginator.count,
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
            "total_pages": paginator.page.paginator.num_pages,
            "current_page": paginator.page.number,
            "results": [serializer(item) for item in page],
        }


class DashboardExecutivoViewSet(_RelatorioViewSet):
    @extend_schema(
        summary="Dashboard executivo",
        description="Indicadores gerenciais consolidados a partir de dados reais da operação.",
        tags=["Relatórios"],
    )
    def list(self, request):
        return Response(get_dashboard_executivo(company_id=self._company_id()))


class RelatorioFiadoViewSet(_RelatorioViewSet):
    @extend_schema(summary="Relatório gerencial de fiado", tags=["Relatórios"])
    def list(self, request):
        data, qs = get_relatorio_fiado(company_id=self._company_id(), filters=self._filters())
        data["resultados"] = self._paginated_payload(qs, _serialize_conta_fiado)
        return Response(data)

    @extend_schema(
        summary="Exportar relatório de fiado em PDF",
        responses={(200, "application/pdf"): OpenApiTypes.BINARY},
        tags=["Relatórios"],
    )
    @action(detail=False, methods=["get"], url_path="pdf", renderer_classes=[PDFRenderer])
    def pdf(self, request):
        data, _ = get_relatorio_fiado(company_id=self._company_id(), filters=self._filters())
        content = render_relatorio_fiado_pdf(company=request.user.company, data=data)
        response = HttpResponse(content, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="{relatorio_pdf_filename("fiado")}"'
        )
        return response


class RelatorioVendasViewSet(_RelatorioViewSet):
    @extend_schema(summary="Relatório gerencial de vendas", tags=["Relatórios"])
    def list(self, request):
        data, qs = get_relatorio_vendas(company_id=self._company_id(), filters=self._filters())
        data["resultados"] = self._paginated_payload(qs, _serialize_venda)
        return Response(data)

    @extend_schema(
        summary="Exportar relatório de vendas em PDF",
        responses={(200, "application/pdf"): OpenApiTypes.BINARY},
        tags=["Relatórios"],
    )
    @action(detail=False, methods=["get"], url_path="pdf", renderer_classes=[PDFRenderer])
    def pdf(self, request):
        data, _ = get_relatorio_vendas(company_id=self._company_id(), filters=self._filters())
        content = render_relatorio_vendas_pdf(company=request.user.company, data=data)
        response = HttpResponse(content, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="{relatorio_pdf_filename("vendas")}"'
        )
        return response


class RelatorioFinanceiroViewSet(_RelatorioViewSet):
    @extend_schema(summary="Relatório gerencial financeiro", tags=["Relatórios"])
    def list(self, request):
        data, qs = get_relatorio_financeiro(company_id=self._company_id(), filters=self._filters())
        data["resultados"] = self._paginated_payload(qs, _serialize_conta_pagar)
        return Response(data)

    @extend_schema(
        summary="Exportar relatório financeiro em PDF",
        responses={(200, "application/pdf"): OpenApiTypes.BINARY},
        tags=["Relatórios"],
    )
    @action(detail=False, methods=["get"], url_path="pdf", renderer_classes=[PDFRenderer])
    def pdf(self, request):
        data, _ = get_relatorio_financeiro(company_id=self._company_id(), filters=self._filters())
        content = render_relatorio_financeiro_pdf(company=request.user.company, data=data)
        response = HttpResponse(content, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="{relatorio_pdf_filename("financeiro")}"'
        )
        return response


class RelatorioEstoqueViewSet(_RelatorioViewSet):
    @extend_schema(summary="Relatório gerencial de estoque", tags=["Relatórios"])
    def list(self, request):
        data, qs = get_relatorio_estoque(company_id=self._company_id(), filters=self._filters())
        data["resultados"] = self._paginated_payload(qs, _serialize_produto)
        return Response(data)
