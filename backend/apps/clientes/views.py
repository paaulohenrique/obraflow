from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.core.pagination import StandardResultsSetPagination

from .filters import ClienteFilter
from .models import Cliente
from .permissions import ClientePermission
from .selectors import (
    get_clientes_bloqueados,
    get_clientes_inadimplentes,
    get_cliente_by_id,
    search_clientes,
)
from .serializers import (
    ClienteCreateSerializer,
    ClienteDetailSerializer,
    ClienteListSerializer,
    ClienteUpdateSerializer,
)
from .services import (
    create_cliente,
    update_cliente,
    bloquear_cliente,
    desbloquear_cliente,
    soft_delete_cliente,
)

_ALLOWED_ORDERING = frozenset({
    "nome", "-nome",
    "created_at", "-created_at",
    "saldo_devedor", "-saldo_devedor",
    "limite_credito", "-limite_credito",
})


@extend_schema_view(
    list=extend_schema(
        summary="Listar clientes",
        description="Retorna todos os clientes ativos da empresa com paginação e filtros.",
        tags=["Clientes"],
    ),
    create=extend_schema(
        summary="Cadastrar cliente",
        description="Cria um novo cliente. CPF/CNPJ é validado e armazenado sem máscara.",
        tags=["Clientes"],
    ),
    retrieve=extend_schema(
        summary="Detalhar cliente",
        description="Retorna todos os dados de um cliente pelo ID.",
        tags=["Clientes"],
    ),
    partial_update=extend_schema(
        summary="Atualizar cliente",
        description="Atualiza parcialmente os dados de um cliente.",
        tags=["Clientes"],
    ),
    destroy=extend_schema(
        summary="Remover cliente (soft delete)",
        description="Remove logicamente o cliente. O registro permanece no banco.",
        tags=["Clientes"],
    ),
)
class ClienteViewSet(viewsets.GenericViewSet):
    queryset = Cliente.objects.none()
    serializer_class = ClienteDetailSerializer
    permission_classes = [ClientePermission]
    # filterset_class kept for drf-spectacular OpenAPI schema generation only.
    filterset_class = ClienteFilter
    search_fields = ["nome", "cpf_cnpj", "telefone", "whatsapp", "email"]
    ordering_fields = ["nome", "created_at", "saldo_devedor", "limite_credito"]
    ordering = ["nome"]

    def _company_id(self):
        return getattr(self.request.user, "company_id", None)

    # ── list ─────────────────────────────────────────────────────────────────

    def list(self, request):
        # Single source of truth: search_clientes handles all filter/search logic.
        # query_params.dict() flattens multi-value keys to the last value, which
        # is the expected behaviour for our single-value filter params.
        filters = request.query_params.dict()
        qs = search_clientes(company_id=self._company_id(), filters=filters)

        ordering = filters.get("ordering", "nome")
        if ordering in _ALLOWED_ORDERING:
            qs = qs.order_by(ordering)
        else:
            qs = qs.order_by("nome")

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(ClienteListSerializer(page, many=True).data)

    # ── create ───────────────────────────────────────────────────────────────

    def create(self, request):
        serializer = ClienteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cliente = create_cliente(
            user=request.user,
            data=serializer.validated_data,
            request=request,
        )
        return Response(
            ClienteDetailSerializer(cliente).data,
            status=status.HTTP_201_CREATED,
        )

    # ── retrieve ─────────────────────────────────────────────────────────────

    def retrieve(self, request, pk=None):
        cliente = get_cliente_by_id(
            company_id=self._company_id(), cliente_id=pk
        )
        self.check_object_permissions(request, cliente)
        return Response(ClienteDetailSerializer(cliente).data)

    # ── partial_update (PATCH) ────────────────────────────────────────────────

    def partial_update(self, request, pk=None):
        cliente = get_cliente_by_id(
            company_id=self._company_id(), cliente_id=pk
        )
        self.check_object_permissions(request, cliente)

        serializer = ClienteUpdateSerializer(
            cliente, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)

        cliente = update_cliente(
            user=request.user,
            cliente=cliente,
            data=serializer.validated_data,
            request=request,
        )
        return Response(ClienteDetailSerializer(cliente).data)

    # ── destroy (soft delete) ─────────────────────────────────────────────────

    def destroy(self, request, pk=None):
        cliente = get_cliente_by_id(
            company_id=self._company_id(), cliente_id=pk
        )
        self.check_object_permissions(request, cliente)
        soft_delete_cliente(user=request.user, cliente=cliente, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ── custom actions ────────────────────────────────────────────────────────

    @extend_schema(
        summary="Clientes inadimplentes",
        description="Lista clientes com saldo devedor acima de R$ 0,00.",
        tags=["Clientes"],
    )
    @action(detail=False, methods=["get"], url_path="inadimplentes")
    def inadimplentes(self, request):
        qs = get_clientes_inadimplentes(company_id=self._company_id())
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(ClienteListSerializer(page, many=True).data)

    @extend_schema(
        summary="Clientes bloqueados",
        description="Lista clientes com a flag 'bloqueado' ativa.",
        tags=["Clientes"],
    )
    @action(detail=False, methods=["get"], url_path="bloqueados")
    def bloqueados(self, request):
        qs = get_clientes_bloqueados(company_id=self._company_id())
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(ClienteListSerializer(page, many=True).data)

    @extend_schema(
        summary="Bloquear cliente",
        description="Marca o cliente como bloqueado, impedindo novas compras no fiado.",
        tags=["Clientes"],
        responses={200: ClienteDetailSerializer},
    )
    @action(detail=True, methods=["post"], url_path="bloquear")
    def bloquear(self, request, pk=None):
        cliente = get_cliente_by_id(company_id=self._company_id(), cliente_id=pk)
        self.check_object_permissions(request, cliente)
        cliente = bloquear_cliente(user=request.user, cliente=cliente, request=request)
        return Response(ClienteDetailSerializer(cliente).data)

    @extend_schema(
        summary="Desbloquear cliente",
        description="Remove o bloqueio do cliente, permitindo novas compras no fiado.",
        tags=["Clientes"],
        responses={200: ClienteDetailSerializer},
    )
    @action(detail=True, methods=["post"], url_path="desbloquear")
    def desbloquear(self, request, pk=None):
        cliente = get_cliente_by_id(company_id=self._company_id(), cliente_id=pk)
        self.check_object_permissions(request, cliente)
        cliente = desbloquear_cliente(user=request.user, cliente=cliente, request=request)
        return Response(ClienteDetailSerializer(cliente).data)
