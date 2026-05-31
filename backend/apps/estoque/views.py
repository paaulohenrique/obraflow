from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view

from apps.core.pagination import StandardResultsSetPagination

from .filters import MovimentacaoFilter, ProdutoFilter
from .models import (
    CategoriaProduto,
    Fornecedor,
    MovimentacaoEstoque,
    Produto,
    UnidadeMedida,
)
from .permissions import EstoquePermission
from .selectors import (
    get_categoria_by_id,
    get_categorias,
    get_fornecedor_by_id,
    get_fornecedores,
    get_movimentacao_by_id,
    get_movimentacoes,
    get_produto_by_id,
    get_unidade_by_id,
    get_unidades,
    produtos_baixo_estoque,
    search_movimentacoes,
    search_produtos,
)
from .serializers import (
    AjusteEstoqueSerializer,
    CancelamentoSerializer,
    CategoriaSerializer,
    DevolucaoEstoqueSerializer,
    EntradaEstoqueSerializer,
    FornecedorSerializer,
    MovimentacaoSerializer,
    ProdutoCreateSerializer,
    ProdutoDetailSerializer,
    ProdutoListSerializer,
    ProdutoUpdateSerializer,
    SaidaEstoqueSerializer,
    UnidadeSerializer,
)
from .services import (
    ajuste_estoque,
    ativar_produto,
    cancelar_movimentacao,
    create_categoria,
    create_fornecedor,
    create_unidade,
    create_produto,
    devolucao_estoque,
    entrada_estoque,
    inativar_produto,
    saida_estoque,
    soft_delete_categoria,
    soft_delete_fornecedor,
    soft_delete_produto,
    soft_delete_unidade,
    update_categoria,
    update_fornecedor,
    update_produto,
    update_unidade,
)


_PRODUTO_ALLOWED_ORDERING = frozenset({
    "nome", "-nome",
    "created_at", "-created_at",
    "estoque_atual", "-estoque_atual",
    "preco_venda", "-preco_venda",
})
_MOV_ALLOWED_ORDERING = frozenset({
    "created_at", "-created_at",
    "tipo", "-tipo",
    "quantidade_delta", "-quantidade_delta",
})


class _TenantViewSet(viewsets.GenericViewSet):
    permission_classes = [EstoquePermission]

    def _company_id(self):
        return getattr(self.request.user, "company_id", None)

    def _serializer_context(self):
        return {"request": self.request}

    def _paginated(self, qs, serializer_class):
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, self.request, view=self)
        return paginator.get_paginated_response(serializer_class(page, many=True).data)


class _CatalogViewSet(_TenantViewSet):
    serializer_class = None
    list_selector = None
    get_selector = None
    create_service = None
    update_service = None
    delete_service = None
    lookup_arg = None

    def list(self, request):
        qs = self.list_selector(company_id=self._company_id())
        return self._paginated(qs, self.serializer_class)

    def create(self, request):
        serializer = self.serializer_class(data=request.data, context=self._serializer_context())
        serializer.is_valid(raise_exception=True)
        obj = self.create_service(
            user=request.user,
            data=serializer.validated_data,
            request=request,
        )
        return Response(self.serializer_class(obj).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        obj = self.get_selector(company_id=self._company_id(), **{self.lookup_arg: pk})
        self.check_object_permissions(request, obj)
        return Response(self.serializer_class(obj).data)

    def update(self, request, pk=None):
        obj = self.get_selector(company_id=self._company_id(), **{self.lookup_arg: pk})
        self.check_object_permissions(request, obj)
        serializer = self.serializer_class(
            obj,
            data=request.data,
            context=self._serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        obj = self.update_service(
            user=request.user,
            **{self.lookup_arg.replace("_id", ""): obj},
            data=serializer.validated_data,
            request=request,
        )
        return Response(self.serializer_class(obj).data)

    def partial_update(self, request, pk=None):
        obj = self.get_selector(company_id=self._company_id(), **{self.lookup_arg: pk})
        self.check_object_permissions(request, obj)
        serializer = self.serializer_class(
            obj,
            data=request.data,
            partial=True,
            context=self._serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        obj = self.update_service(
            user=request.user,
            **{self.lookup_arg.replace("_id", ""): obj},
            data=serializer.validated_data,
            request=request,
        )
        return Response(self.serializer_class(obj).data)

    def destroy(self, request, pk=None):
        obj = self.get_selector(company_id=self._company_id(), **{self.lookup_arg: pk})
        self.check_object_permissions(request, obj)
        self.delete_service(
            user=request.user,
            **{self.lookup_arg.replace("_id", ""): obj},
            request=request,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    list=extend_schema(summary="Listar unidades de medida", tags=["Estoque - Unidades"]),
    create=extend_schema(summary="Criar unidade de medida", tags=["Estoque - Unidades"]),
    retrieve=extend_schema(summary="Detalhar unidade de medida", tags=["Estoque - Unidades"]),
    update=extend_schema(summary="Atualizar unidade de medida", tags=["Estoque - Unidades"]),
    partial_update=extend_schema(summary="Atualizar parcialmente unidade", tags=["Estoque - Unidades"]),
    destroy=extend_schema(summary="Remover unidade de medida", tags=["Estoque - Unidades"]),
)
class UnidadeViewSet(_CatalogViewSet):
    queryset = UnidadeMedida.objects.none()
    serializer_class = UnidadeSerializer
    list_selector = staticmethod(get_unidades)
    get_selector = staticmethod(get_unidade_by_id)
    create_service = staticmethod(create_unidade)
    update_service = staticmethod(update_unidade)
    delete_service = staticmethod(soft_delete_unidade)
    lookup_arg = "unidade_id"


@extend_schema_view(
    list=extend_schema(summary="Listar categorias", tags=["Estoque - Categorias"]),
    create=extend_schema(summary="Criar categoria", tags=["Estoque - Categorias"]),
    retrieve=extend_schema(summary="Detalhar categoria", tags=["Estoque - Categorias"]),
    update=extend_schema(summary="Atualizar categoria", tags=["Estoque - Categorias"]),
    partial_update=extend_schema(summary="Atualizar parcialmente categoria", tags=["Estoque - Categorias"]),
    destroy=extend_schema(summary="Remover categoria", tags=["Estoque - Categorias"]),
)
class CategoriaViewSet(_CatalogViewSet):
    queryset = CategoriaProduto.objects.none()
    serializer_class = CategoriaSerializer
    list_selector = staticmethod(get_categorias)
    get_selector = staticmethod(get_categoria_by_id)
    create_service = staticmethod(create_categoria)
    update_service = staticmethod(update_categoria)
    delete_service = staticmethod(soft_delete_categoria)
    lookup_arg = "categoria_id"


@extend_schema_view(
    list=extend_schema(summary="Listar fornecedores", tags=["Estoque - Fornecedores"]),
    create=extend_schema(summary="Criar fornecedor", tags=["Estoque - Fornecedores"]),
    retrieve=extend_schema(summary="Detalhar fornecedor", tags=["Estoque - Fornecedores"]),
    update=extend_schema(summary="Atualizar fornecedor", tags=["Estoque - Fornecedores"]),
    partial_update=extend_schema(summary="Atualizar parcialmente fornecedor", tags=["Estoque - Fornecedores"]),
    destroy=extend_schema(summary="Remover fornecedor", tags=["Estoque - Fornecedores"]),
)
class FornecedorViewSet(_CatalogViewSet):
    queryset = Fornecedor.objects.none()
    serializer_class = FornecedorSerializer
    list_selector = staticmethod(get_fornecedores)
    get_selector = staticmethod(get_fornecedor_by_id)
    create_service = staticmethod(create_fornecedor)
    update_service = staticmethod(update_fornecedor)
    delete_service = staticmethod(soft_delete_fornecedor)
    lookup_arg = "fornecedor_id"


@extend_schema_view(
    list=extend_schema(
        summary="Listar produtos",
        description="Lista produtos ativos e inativos da empresa com filtros e paginação.",
        tags=["Estoque - Produtos"],
    ),
    create=extend_schema(
        summary="Criar produto",
        description="Cria produto com estoque inicial zero. Estoque muda apenas por movimentações.",
        tags=["Estoque - Produtos"],
    ),
    retrieve=extend_schema(summary="Detalhar produto", tags=["Estoque - Produtos"]),
    update=extend_schema(summary="Atualizar produto", tags=["Estoque - Produtos"]),
    partial_update=extend_schema(summary="Atualizar parcialmente produto", tags=["Estoque - Produtos"]),
    destroy=extend_schema(summary="Remover produto", tags=["Estoque - Produtos"]),
)
class ProdutoViewSet(_TenantViewSet):
    queryset = Produto.objects.none()
    serializer_class = ProdutoDetailSerializer
    filterset_class = ProdutoFilter
    search_fields = ["nome", "sku", "codigo_barras", "descricao"]
    ordering_fields = ["nome", "created_at", "estoque_atual", "preco_venda"]
    ordering = ["nome"]

    def list(self, request):
        filters = request.query_params.dict()
        qs = search_produtos(company_id=self._company_id(), filters=filters)
        ordering = filters.get("ordering", "nome")
        qs = qs.order_by(ordering if ordering in _PRODUTO_ALLOWED_ORDERING else "nome")
        return self._paginated(qs, ProdutoListSerializer)

    def create(self, request):
        serializer = ProdutoCreateSerializer(data=request.data, context=self._serializer_context())
        serializer.is_valid(raise_exception=True)
        produto = create_produto(
            user=request.user,
            data=serializer.validated_data,
            request=request,
        )
        return Response(ProdutoDetailSerializer(produto).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        produto = get_produto_by_id(company_id=self._company_id(), produto_id=pk)
        self.check_object_permissions(request, produto)
        return Response(ProdutoDetailSerializer(produto).data)

    def update(self, request, pk=None):
        produto = get_produto_by_id(company_id=self._company_id(), produto_id=pk)
        self.check_object_permissions(request, produto)
        serializer = ProdutoUpdateSerializer(
            produto,
            data=request.data,
            context=self._serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        produto = update_produto(
            user=request.user,
            produto=produto,
            data=serializer.validated_data,
            request=request,
        )
        return Response(ProdutoDetailSerializer(produto).data)

    def partial_update(self, request, pk=None):
        produto = get_produto_by_id(company_id=self._company_id(), produto_id=pk)
        self.check_object_permissions(request, produto)
        serializer = ProdutoUpdateSerializer(
            produto,
            data=request.data,
            partial=True,
            context=self._serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        produto = update_produto(
            user=request.user,
            produto=produto,
            data=serializer.validated_data,
            request=request,
        )
        return Response(ProdutoDetailSerializer(produto).data)

    def destroy(self, request, pk=None):
        produto = get_produto_by_id(company_id=self._company_id(), produto_id=pk)
        self.check_object_permissions(request, produto)
        soft_delete_produto(user=request.user, produto=produto, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        summary="Ativar produto",
        description="Reativa um produto previamente inativado.",
        responses={200: ProdutoDetailSerializer},
        tags=["Estoque - Produtos"],
    )
    @action(detail=True, methods=["post"], url_path="ativar")
    def ativar(self, request, pk=None):
        produto = get_produto_by_id(company_id=self._company_id(), produto_id=pk)
        self.check_object_permissions(request, produto)
        produto = ativar_produto(user=request.user, produto=produto, request=request)
        return Response(ProdutoDetailSerializer(produto).data)

    @extend_schema(
        summary="Inativar produto",
        description="Impede novas movimentações operacionais para o produto.",
        responses={200: ProdutoDetailSerializer},
        tags=["Estoque - Produtos"],
    )
    @action(detail=True, methods=["post"], url_path="inativar")
    def inativar(self, request, pk=None):
        produto = get_produto_by_id(company_id=self._company_id(), produto_id=pk)
        self.check_object_permissions(request, produto)
        produto = inativar_produto(user=request.user, produto=produto, request=request)
        return Response(ProdutoDetailSerializer(produto).data)

    @extend_schema(
        summary="Produtos com estoque baixo",
        description="Lista produtos ativos cujo estoque atual está menor ou igual ao estoque mínimo.",
        responses={200: ProdutoListSerializer(many=True)},
        tags=["Estoque - Produtos"],
    )
    @action(detail=False, methods=["get"], url_path="baixo-estoque")
    def baixo_estoque(self, request):
        qs = produtos_baixo_estoque(company_id=self._company_id()).order_by("nome")
        return self._paginated(qs, ProdutoListSerializer)

    @extend_schema(
        summary="Movimentações do produto",
        description="Lista o histórico permanente de movimentações de estoque de um produto.",
        responses={200: MovimentacaoSerializer(many=True)},
        tags=["Estoque - Produtos"],
    )
    @action(detail=True, methods=["get"], url_path="movimentacoes")
    def movimentacoes(self, request, pk=None):
        produto = get_produto_by_id(company_id=self._company_id(), produto_id=pk)
        self.check_object_permissions(request, produto)
        qs = get_movimentacoes(company_id=self._company_id()).filter(produto_id=produto.pk)
        return self._paginated(qs.order_by("-created_at"), MovimentacaoSerializer)


@extend_schema_view(
    list=extend_schema(
        summary="Listar movimentações",
        description="Lista o ledger permanente de movimentações da empresa.",
        tags=["Estoque - Movimentações"],
    ),
    retrieve=extend_schema(summary="Detalhar movimentação", tags=["Estoque - Movimentações"]),
)
class MovimentacaoViewSet(_TenantViewSet):
    queryset = MovimentacaoEstoque.objects.none()
    serializer_class = MovimentacaoSerializer
    filterset_class = MovimentacaoFilter
    ordering_fields = ["created_at", "tipo", "quantidade_delta"]
    ordering = ["-created_at"]

    def list(self, request):
        filters = request.query_params.dict()
        qs = search_movimentacoes(company_id=self._company_id(), filters=filters)
        ordering = filters.get("ordering", "-created_at")
        qs = qs.order_by(ordering if ordering in _MOV_ALLOWED_ORDERING else "-created_at")
        return self._paginated(qs, MovimentacaoSerializer)

    def retrieve(self, request, pk=None):
        movimentacao = get_movimentacao_by_id(
            company_id=self._company_id(),
            movimentacao_id=pk,
        )
        self.check_object_permissions(request, movimentacao)
        return Response(MovimentacaoSerializer(movimentacao).data)

    def _movement_action(self, request, serializer_class, service):
        serializer = serializer_class(data=request.data, context=self._serializer_context())
        serializer.is_valid(raise_exception=True)
        movimentacao = service(
            user=request.user,
            **serializer.validated_data,
            request=request,
        )
        return Response(MovimentacaoSerializer(movimentacao).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Registrar entrada de estoque",
        description="Aumenta o estoque do produto com lock transacional.",
        request=EntradaEstoqueSerializer,
        responses={201: MovimentacaoSerializer},
        examples=[
            OpenApiExample(
                "Entrada de compra",
                value={"produto": "uuid", "quantidade": "10.000", "custo_unitario": "25.50"},
                request_only=True,
            )
        ],
        tags=["Estoque - Movimentações"],
    )
    @action(detail=False, methods=["post"], url_path="entrada")
    def entrada(self, request):
        return self._movement_action(request, EntradaEstoqueSerializer, entrada_estoque)

    @extend_schema(
        summary="Registrar saída de estoque",
        description="Reduz o estoque do produto e rejeita saldo negativo.",
        request=SaidaEstoqueSerializer,
        responses={201: MovimentacaoSerializer},
        tags=["Estoque - Movimentações"],
    )
    @action(detail=False, methods=["post"], url_path="saida")
    def saida(self, request):
        return self._movement_action(request, SaidaEstoqueSerializer, saida_estoque)

    @extend_schema(
        summary="Registrar ajuste de estoque",
        description="Ajusta o saldo para mais ou para menos; motivo é obrigatório.",
        request=AjusteEstoqueSerializer,
        responses={201: MovimentacaoSerializer},
        tags=["Estoque - Movimentações"],
    )
    @action(detail=False, methods=["post"], url_path="ajuste")
    def ajuste(self, request):
        return self._movement_action(request, AjusteEstoqueSerializer, ajuste_estoque)

    @extend_schema(
        summary="Registrar devolução ao estoque",
        description="Aumenta o estoque por devolução de mercadoria.",
        request=DevolucaoEstoqueSerializer,
        responses={201: MovimentacaoSerializer},
        tags=["Estoque - Movimentações"],
    )
    @action(detail=False, methods=["post"], url_path="devolucao")
    def devolucao(self, request):
        return self._movement_action(request, DevolucaoEstoqueSerializer, devolucao_estoque)

    @extend_schema(
        summary="Cancelar movimentação",
        description="Cria uma movimentação reversa e marca a original como cancelada.",
        request=CancelamentoSerializer,
        responses={201: MovimentacaoSerializer},
        tags=["Estoque - Movimentações"],
    )
    @action(detail=True, methods=["post"], url_path="cancelar")
    def cancelar(self, request, pk=None):
        movimentacao = get_movimentacao_by_id(
            company_id=self._company_id(),
            movimentacao_id=pk,
        )
        self.check_object_permissions(request, movimentacao)
        serializer = CancelamentoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cancelamento = cancelar_movimentacao(
            user=request.user,
            movimentacao=movimentacao,
            **serializer.validated_data,
            request=request,
        )
        return Response(MovimentacaoSerializer(cancelamento).data, status=status.HTTP_201_CREATED)
