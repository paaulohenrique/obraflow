from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.core.pagination import StandardResultsSetPagination

from .filters import VendaFilter
from .models import Venda
from .permissions import VendaPermission
from .selectors import get_dashboard_vendas, get_venda_by_id, search_vendas
from .serializers import (
    CancelarVendaSerializer,
    DashboardVendasSerializer,
    VendaCreateSerializer,
    VendaDetailSerializer,
    VendaListSerializer,
)
from .services import cancelar_venda, criar_venda
from .services.pdf import render_venda_pdf, venda_pdf_filename


_ORDERING = {
    "created_at", "-created_at",
    "updated_at", "-updated_at",
    "valor_total", "-valor_total",
    "numero", "-numero",
}


@extend_schema_view(
    list=extend_schema(summary="Listar vendas", tags=["PDV - Vendas"]),
    create=extend_schema(
        summary="Criar venda (PDV)",
        request=VendaCreateSerializer,
        responses={201: VendaDetailSerializer},
        tags=["PDV - Vendas"],
    ),
    retrieve=extend_schema(summary="Detalhar venda", tags=["PDV - Vendas"]),
)
class VendaViewSet(viewsets.GenericViewSet):
    queryset = Venda.objects.none()
    serializer_class = VendaDetailSerializer
    permission_classes = [VendaPermission]
    filterset_class = VendaFilter

    def _company_id(self):
        return getattr(self.request.user, "company_id", None)

    def _serializer_context(self):
        return {"request": self.request}

    def _paginated(self, qs, serializer_class):
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, self.request, view=self)
        return paginator.get_paginated_response(serializer_class(page, many=True).data)

    def _ordering(self, default="-created_at"):
        ordering = self.request.query_params.get("ordering", default)
        return ordering if ordering in _ORDERING else default

    def list(self, request):
        qs = search_vendas(
            company_id=self._company_id(),
            filters=request.query_params.dict(),
        ).order_by(self._ordering())
        return self._paginated(qs, VendaListSerializer)

    def create(self, request):
        serializer = VendaCreateSerializer(data=request.data, context=self._serializer_context())
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data
        venda = criar_venda(
            user=request.user,
            data={
                "itens": [
                    {
                        "produto": item["produto"].pk,
                        "forma_venda": item.get("forma_venda"),
                        "quantidade_informada": item["quantidade_informada"],
                        "preco_unitario": item["preco_unitario"],
                    }
                    for item in vd["itens"]
                ],
                "forma_pagamento": vd["forma_pagamento"],
                "conta_financeira": vd["conta_financeira"],
                "cliente": vd.get("cliente"),
                "desconto": vd.get("desconto", "0.00"),
                "observacao": vd.get("observacao", ""),
            },
            request=request,
        )
        return Response(VendaDetailSerializer(venda).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        venda = get_venda_by_id(company_id=self._company_id(), venda_id=pk)
        self.check_object_permissions(request, venda)
        return Response(VendaDetailSerializer(venda).data)

    @extend_schema(
        summary="Cancelar venda",
        request=CancelarVendaSerializer,
        responses={200: VendaDetailSerializer},
        tags=["PDV - Vendas"],
    )
    @action(detail=True, methods=["post"], url_path="cancelar")
    def cancelar(self, request, pk=None):
        venda = get_venda_by_id(company_id=self._company_id(), venda_id=pk)
        self.check_object_permissions(request, venda)
        serializer = CancelarVendaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        venda = cancelar_venda(
            user=request.user,
            venda=venda,
            motivo=serializer.validated_data["motivo"],
            request=request,
        )
        return Response(VendaDetailSerializer(venda).data)

    @extend_schema(
        summary="Comprovante PDF da venda",
        responses={200: bytes},
        tags=["PDV - Vendas"],
    )
    @action(detail=True, methods=["get"], url_path="pdf")
    def pdf(self, request, pk=None):
        venda = get_venda_by_id(company_id=self._company_id(), venda_id=pk)
        self.check_object_permissions(request, venda)
        itens = venda.itens.select_related(
            "produto", "forma_venda"
        ).filter(deleted_at__isnull=True)
        pdf_bytes = render_venda_pdf(venda=venda, itens=itens)
        filename = venda_pdf_filename(venda)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @extend_schema(
        summary="Dashboard de vendas",
        responses={200: DashboardVendasSerializer},
        tags=["PDV - Dashboard"],
    )
    @action(detail=False, methods=["get"], url_path="dashboard")
    def dashboard(self, request):
        data = get_dashboard_vendas(company_id=self._company_id())
        return Response(DashboardVendasSerializer(data).data)
