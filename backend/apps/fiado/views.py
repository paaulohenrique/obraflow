from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view

from apps.core.pagination import StandardResultsSetPagination

from .filters import ContaFiadoFilter
from .models import ContaFiado, ItemFiado, PagamentoFiado
from .permissions import FiadoPermission
from .selectors import (
    get_conta_by_id,
    get_dashboard_fiado,
    get_historico_da_conta,
    get_item_by_id,
    get_itens_da_conta,
    get_pagamento_by_id,
    get_pagamentos_da_conta,
    search_contas,
)
from .serializers import (
    ContaFiadoCancelSerializer,
    ContaFiadoCreateSerializer,
    ContaFiadoDetailSerializer,
    ContaFiadoListSerializer,
    ContaFiadoUpdateSerializer,
    DashboardFiadoSerializer,
    HistoricoFiadoSerializer,
    ItemFiadoCancelSerializer,
    ItemFiadoCreateSerializer,
    ItemFiadoSerializer,
    PagamentoFiadoCancelSerializer,
    PagamentoFiadoCreateSerializer,
    PagamentoFiadoSerializer,
)
from .services import (
    abrir_conta_fiado,
    adicionar_item_fiado,
    cancelar_conta_fiado,
    cancelar_item_fiado,
    cancelar_pagamento_fiado,
    registrar_pagamento_fiado,
    update_conta_fiado,
)


_CONTA_ALLOWED_ORDERING = frozenset({
    "data_abertura",
    "-data_abertura",
    "data_vencimento",
    "-data_vencimento",
    "valor_total",
    "-valor_total",
    "valor_restante",
    "-valor_restante",
    "created_at",
    "-created_at",
})


class _FiadoViewSet(viewsets.GenericViewSet):
    permission_classes = [FiadoPermission]

    def _company_id(self):
        return getattr(self.request.user, "company_id", None)

    def _serializer_context(self):
        return {"request": self.request}

    def _paginated(self, qs, serializer_class):
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, self.request, view=self)
        return paginator.get_paginated_response(serializer_class(page, many=True).data)


@extend_schema_view(
    list=extend_schema(
        summary="Listar contas fiado",
        description="Lista contas fiado da empresa com filtros, busca, ordering e paginação.",
        tags=["Fiado - Contas"],
    ),
    create=extend_schema(
        summary="Abrir conta fiado",
        description="Abre uma conta fiado para um cliente ativo, não bloqueado e sem conta aberta.",
        request=ContaFiadoCreateSerializer,
        responses={201: ContaFiadoDetailSerializer},
        examples=[
            OpenApiExample(
                "Abrir conta",
                value={"cliente": "uuid", "data_vencimento": "2026-06-30"},
                request_only=True,
            )
        ],
        tags=["Fiado - Contas"],
    ),
    retrieve=extend_schema(summary="Detalhar conta fiado", tags=["Fiado - Contas"]),
    partial_update=extend_schema(
        summary="Atualizar vencimento/observação",
        request=ContaFiadoUpdateSerializer,
        responses={200: ContaFiadoDetailSerializer},
        tags=["Fiado - Contas"],
    ),
)
class ContaFiadoViewSet(_FiadoViewSet):
    queryset = ContaFiado.objects.none()
    serializer_class = ContaFiadoDetailSerializer
    filterset_class = ContaFiadoFilter
    search_fields = ["cliente__nome", "cliente__cpf_cnpj", "observacao"]
    ordering_fields = [
        "data_abertura",
        "data_vencimento",
        "valor_total",
        "valor_restante",
        "created_at",
    ]
    ordering = ["-created_at"]

    def list(self, request):
        filters = request.query_params.dict()
        qs = search_contas(company_id=self._company_id(), filters=filters)
        ordering = filters.get("ordering", "-created_at")
        qs = qs.order_by(ordering if ordering in _CONTA_ALLOWED_ORDERING else "-created_at")
        return self._paginated(qs, ContaFiadoListSerializer)

    def create(self, request):
        serializer = ContaFiadoCreateSerializer(
            data=request.data,
            context=self._serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        conta = abrir_conta_fiado(
            user=request.user,
            data=serializer.validated_data,
            request=request,
        )
        return Response(ContaFiadoDetailSerializer(conta).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        conta = get_conta_by_id(company_id=self._company_id(), conta_id=pk)
        self.check_object_permissions(request, conta)
        return Response(ContaFiadoDetailSerializer(conta).data)

    def partial_update(self, request, pk=None):
        conta = get_conta_by_id(company_id=self._company_id(), conta_id=pk)
        self.check_object_permissions(request, conta)
        serializer = ContaFiadoUpdateSerializer(
            conta,
            data=request.data,
            partial=True,
            context=self._serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        conta = update_conta_fiado(
            user=request.user,
            conta=conta,
            data=serializer.validated_data,
            request=request,
        )
        return Response(ContaFiadoDetailSerializer(conta).data)

    @extend_schema(
        summary="Cancelar conta fiado",
        description="Cancela uma conta sem pagamentos confirmados, revertendo itens ativos.",
        request=ContaFiadoCancelSerializer,
        responses={200: ContaFiadoDetailSerializer},
        examples=[
            OpenApiExample(
                "Cancelar conta",
                value={"motivo": "Conta aberta por engano", "observacao": "QA manual"},
                request_only=True,
            )
        ],
        tags=["Fiado - Contas"],
    )
    @action(detail=True, methods=["post"], url_path="cancelar")
    def cancelar(self, request, pk=None):
        conta = get_conta_by_id(company_id=self._company_id(), conta_id=pk)
        self.check_object_permissions(request, conta)
        serializer = ContaFiadoCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conta = cancelar_conta_fiado(
            user=request.user,
            conta=conta,
            **serializer.validated_data,
            request=request,
        )
        return Response(ContaFiadoDetailSerializer(conta).data)

    @extend_schema(
        summary="Listar/adicionar itens da conta",
        description="GET lista itens; POST adiciona item e baixa estoque automaticamente.",
        request=ItemFiadoCreateSerializer,
        responses={200: ItemFiadoSerializer(many=True), 201: ItemFiadoSerializer},
        examples=[
            OpenApiExample(
                "Adicionar item",
                value={
                    "produto": "uuid",
                    "quantidade": "10.000",
                    "observacao": "Teste QA",
                    "idempotency_key": "caixa-001",
                },
                request_only=True,
            )
        ],
        tags=["Fiado - Itens"],
    )
    @action(detail=True, methods=["get", "post"], url_path="itens")
    def itens(self, request, pk=None):
        conta = get_conta_by_id(company_id=self._company_id(), conta_id=pk)
        self.check_object_permissions(request, conta)
        if request.method == "GET":
            qs = get_itens_da_conta(company_id=self._company_id(), conta_id=conta.pk)
            return self._paginated(qs, ItemFiadoSerializer)

        serializer = ItemFiadoCreateSerializer(
            data=request.data,
            context=self._serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        item = adicionar_item_fiado(
            user=request.user,
            conta=conta,
            data=serializer.validated_data,
            request=request,
        )
        return Response(ItemFiadoSerializer(item).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Listar/registrar pagamentos da conta",
        description="GET lista pagamentos; POST registra pagamento parcial ou total.",
        request=PagamentoFiadoCreateSerializer,
        responses={200: PagamentoFiadoSerializer(many=True), 201: PagamentoFiadoSerializer},
        examples=[
            OpenApiExample(
                "Pagamento PIX",
                value={
                    "valor": "100.00",
                    "forma_pagamento": "PIX",
                    "observacao": "Pagamento parcial QA",
                    "idempotency_key": "pix-001",
                },
                request_only=True,
            )
        ],
        tags=["Fiado - Pagamentos"],
    )
    @action(detail=True, methods=["get", "post"], url_path="pagamentos")
    def pagamentos(self, request, pk=None):
        conta = get_conta_by_id(company_id=self._company_id(), conta_id=pk)
        self.check_object_permissions(request, conta)
        if request.method == "GET":
            qs = get_pagamentos_da_conta(company_id=self._company_id(), conta_id=conta.pk)
            return self._paginated(qs, PagamentoFiadoSerializer)

        serializer = PagamentoFiadoCreateSerializer(
            data=request.data,
            context=self._serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        pagamento = registrar_pagamento_fiado(
            user=request.user,
            conta=conta,
            data=serializer.validated_data,
            request=request,
        )
        return Response(PagamentoFiadoSerializer(pagamento).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Histórico operacional da conta fiado",
        responses={200: HistoricoFiadoSerializer(many=True)},
        tags=["Fiado - Histórico"],
    )
    @action(detail=True, methods=["get"], url_path="historico")
    def historico(self, request, pk=None):
        conta = get_conta_by_id(company_id=self._company_id(), conta_id=pk)
        self.check_object_permissions(request, conta)
        qs = get_historico_da_conta(company_id=self._company_id(), conta_id=conta.pk)
        return self._paginated(qs, HistoricoFiadoSerializer)


class ItemFiadoViewSet(_FiadoViewSet):
    queryset = ItemFiado.objects.none()
    serializer_class = ItemFiadoSerializer

    @extend_schema(
        summary="Cancelar item fiado",
        description="Marca item como cancelado e cria movimentação reversa no estoque.",
        request=ItemFiadoCancelSerializer,
        responses={200: ItemFiadoSerializer},
        examples=[
            OpenApiExample(
                "Cancelar item",
                value={"motivo": "Cliente desistiu do item", "observacao": "QA manual"},
                request_only=True,
            )
        ],
        tags=["Fiado - Itens"],
    )
    @action(detail=True, methods=["post"], url_path="cancelar")
    def cancelar(self, request, pk=None):
        item = get_item_by_id(company_id=self._company_id(), item_id=pk)
        self.check_object_permissions(request, item)
        serializer = ItemFiadoCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = cancelar_item_fiado(
            user=request.user,
            item=item,
            **serializer.validated_data,
            request=request,
        )
        return Response(ItemFiadoSerializer(item).data)


class PagamentoFiadoViewSet(_FiadoViewSet):
    queryset = PagamentoFiado.objects.none()
    serializer_class = PagamentoFiadoSerializer

    @extend_schema(
        summary="Cancelar pagamento fiado",
        description="Cancela pagamento confirmado e reabre a conta se ela estava fechada.",
        request=PagamentoFiadoCancelSerializer,
        responses={200: PagamentoFiadoSerializer},
        examples=[
            OpenApiExample(
                "Cancelar pagamento",
                value={"motivo": "Pagamento estornado", "observacao": "QA manual"},
                request_only=True,
            )
        ],
        tags=["Fiado - Pagamentos"],
    )
    @action(detail=True, methods=["post"], url_path="cancelar")
    def cancelar(self, request, pk=None):
        pagamento = get_pagamento_by_id(company_id=self._company_id(), pagamento_id=pk)
        self.check_object_permissions(request, pagamento)
        serializer = PagamentoFiadoCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pagamento = cancelar_pagamento_fiado(
            user=request.user,
            pagamento=pagamento,
            **serializer.validated_data,
            request=request,
        )
        return Response(PagamentoFiadoSerializer(pagamento).data)


class DashboardFiadoViewSet(_FiadoViewSet):
    queryset = ContaFiado.objects.none()
    serializer_class = DashboardFiadoSerializer

    @extend_schema(
        summary="Dashboard básico do fiado",
        responses={200: DashboardFiadoSerializer},
        tags=["Fiado - Dashboard"],
    )
    def list(self, request):
        data = get_dashboard_fiado(company_id=self._company_id())
        return Response(DashboardFiadoSerializer(data).data)
