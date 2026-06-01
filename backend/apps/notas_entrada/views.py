from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view

from apps.core.pagination import StandardResultsSetPagination

from .filters import NotaFiscalEntradaFilter
from .models import NotaFiscalEntrada
from .permissions import NotaEntradaPermission
from .selectors import (
    get_dashboard,
    get_historico,
    get_item_by_id,
    get_itens,
    get_nota_by_id,
    get_notas_visiveis,
)
from .serializers import (
    ConfirmarNotaSerializer,
    DashboardNotasSerializer,
    HistoricoNotaSerializer,
    ImportarChaveSerializer,
    ItemNotaListSerializer,
    ItemNotaUpdateSerializer,
    NotaFiscalEntradaDetailSerializer,
    NotaFiscalEntradaListSerializer,
    RejeitarNotaSerializer,
    SugestoesProdutoSerializer,
    UploadXMLSerializer,
    VincularFornecedorSerializer,
)
from .services.confirmacao import confirmar_nota
from .services.matching import sugestoes_produto
from .services.nota import _UNSET, importar_xml_nota, rejeitar_nota, vincular_fornecedor, vincular_produto_item


_ORDERING = {
    "created_at", "-created_at",
    "data_emissao", "-data_emissao",
    "valor_total", "-valor_total",
    "status", "-status",
    "numero", "-numero",
}


@extend_schema_view(
    list=extend_schema(summary="Listar notas fiscais de entrada", tags=["Notas de Entrada"]),
    retrieve=extend_schema(summary="Detalhar nota fiscal de entrada", tags=["Notas de Entrada"]),
)
class NotaFiscalEntradaViewSet(viewsets.GenericViewSet):
    queryset = NotaFiscalEntrada.objects.none()
    serializer_class = NotaFiscalEntradaDetailSerializer
    permission_classes = [NotaEntradaPermission]
    filterset_class = NotaFiscalEntradaFilter

    def _ctx(self):
        return {"request": self.request}

    def _paginated(self, qs, serializer_class):
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, self.request, view=self)
        return paginator.get_paginated_response(serializer_class(page, many=True, context=self._ctx()).data)

    def _ordering(self):
        ordering = self.request.query_params.get("ordering", "-created_at")
        return ordering if ordering in _ORDERING else "-created_at"

    def get_object(self):
        nota = get_nota_by_id(user=self.request.user, nota_id=self.kwargs["pk"])
        self.check_object_permissions(self.request, nota)
        return nota

    # ── List / Retrieve ───────────────────────────────────────────────────────

    def list(self, request):
        qs = get_notas_visiveis(user=request.user).order_by(self._ordering())
        filterset = NotaFiscalEntradaFilter(request.query_params, queryset=qs)
        return self._paginated(filterset.qs, NotaFiscalEntradaListSerializer)

    def retrieve(self, request, pk=None):
        nota = self.get_object()
        return Response(NotaFiscalEntradaDetailSerializer(nota, context=self._ctx()).data)

    # ── Upload XML ────────────────────────────────────────────────────────────

    @extend_schema(
        summary="Importar NF-e por upload de XML",
        request=UploadXMLSerializer,
        responses={201: NotaFiscalEntradaDetailSerializer},
        tags=["Notas de Entrada"],
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="upload",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload(self, request):
        serializer = UploadXMLSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        nota = importar_xml_nota(
            user=request.user,
            arquivo=serializer.validated_data["arquivo"],
            observacao=serializer.validated_data.get("observacao", ""),
            idempotency_key=serializer.validated_data.get("idempotency_key", ""),
            request=request,
        )
        return Response(
            NotaFiscalEntradaDetailSerializer(nota, context=self._ctx()).data,
            status=status.HTTP_201_CREATED,
        )

    # ── Importar por Chave (501 na V1) ────────────────────────────────────────

    @extend_schema(
        summary="Importar NF-e por chave de acesso (disponível na V2)",
        request=ImportarChaveSerializer,
        responses={501: None},
        tags=["Notas de Entrada"],
    )
    @action(detail=False, methods=["post"], url_path="importar-chave")
    def importar_chave(self, request):
        serializer = ImportarChaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            {"detail": "Importação por chave de acesso disponível na V2."},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )

    # ── Vincular Fornecedor ───────────────────────────────────────────────────

    @extend_schema(
        summary="Vincular fornecedor à nota fiscal",
        request=VincularFornecedorSerializer,
        responses={200: NotaFiscalEntradaDetailSerializer},
        tags=["Notas de Entrada"],
    )
    @action(detail=True, methods=["post"], url_path="vincular-fornecedor")
    def vincular_fornecedor(self, request, pk=None):
        nota = self.get_object()
        serializer = VincularFornecedorSerializer(data=request.data, context=self._ctx())
        serializer.is_valid(raise_exception=True)
        nota = vincular_fornecedor(
            user=request.user,
            nota=nota,
            fornecedor=serializer.validated_data["fornecedor"],
            request=request,
        )
        return Response(NotaFiscalEntradaDetailSerializer(nota, context=self._ctx()).data)

    # ── Confirmar ─────────────────────────────────────────────────────────────

    @extend_schema(
        summary="Confirmar nota fiscal e lançar no estoque",
        request=ConfirmarNotaSerializer,
        responses={200: NotaFiscalEntradaDetailSerializer},
        tags=["Notas de Entrada"],
    )
    @action(detail=True, methods=["post"], url_path="confirmar")
    def confirmar(self, request, pk=None):
        self.get_object()  # verifica permissão de objeto
        serializer = ConfirmarNotaSerializer(data=request.data, context=self._ctx())
        serializer.is_valid(raise_exception=True)

        dados_cp = serializer.validated_data.get("dados_conta_pagar")
        nota = confirmar_nota(
            user=request.user,
            nota_id=pk,
            criar_conta_pagar_flag=serializer.validated_data.get("criar_conta_pagar", False),
            dados_conta_pagar=dados_cp,
            request=request,
        )
        return Response(NotaFiscalEntradaDetailSerializer(nota, context=self._ctx()).data)

    # ── Rejeitar ──────────────────────────────────────────────────────────────

    @extend_schema(
        summary="Rejeitar nota fiscal de entrada",
        request=RejeitarNotaSerializer,
        responses={200: NotaFiscalEntradaDetailSerializer},
        tags=["Notas de Entrada"],
    )
    @action(detail=True, methods=["post"], url_path="rejeitar")
    def rejeitar(self, request, pk=None):
        nota = self.get_object()
        serializer = RejeitarNotaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        nota = rejeitar_nota(
            user=request.user,
            nota=nota,
            motivo=serializer.validated_data["motivo"],
            request=request,
        )
        return Response(NotaFiscalEntradaDetailSerializer(nota, context=self._ctx()).data)

    # ── Itens ─────────────────────────────────────────────────────────────────

    @extend_schema(
        summary="Listar itens da nota fiscal",
        responses={200: ItemNotaListSerializer(many=True)},
        tags=["Notas de Entrada"],
    )
    @action(detail=True, methods=["get"], url_path="itens")
    def itens(self, request, pk=None):
        self.get_object()
        qs = get_itens(user=request.user, nota_id=pk)
        return self._paginated(qs, ItemNotaListSerializer)

    @extend_schema(
        summary="Detalhar item da nota fiscal",
        responses={200: ItemNotaListSerializer},
        tags=["Notas de Entrada"],
    )
    @action(detail=True, methods=["get"], url_path=r"itens/(?P<item_id>[^/.]+)/detalhe")
    def item_detalhe(self, request, pk=None, item_id=None):
        item = get_item_by_id(user=request.user, nota_id=pk, item_id=item_id)
        return Response(ItemNotaListSerializer(item, context=self._ctx()).data)

    @extend_schema(
        summary="Atualizar item da nota (vincular produto / ignorar)",
        request=ItemNotaUpdateSerializer,
        responses={200: ItemNotaListSerializer},
        tags=["Notas de Entrada"],
    )
    @action(detail=True, methods=["patch"], url_path=r"itens/(?P<item_id>[^/.]+)")
    def vincular_item(self, request, pk=None, item_id=None):
        item = get_item_by_id(user=request.user, nota_id=pk, item_id=item_id)
        serializer = ItemNotaUpdateSerializer(data=request.data, context=self._ctx())
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Usa sentinel para distinguir "não enviado" de "enviado como null"
        forma_venda = data["forma_venda"] if "forma_venda" in data else _UNSET

        item = vincular_produto_item(
            user=request.user,
            item=item,
            produto=data.get("produto", item.produto),
            custo_unitario=data.get("custo_unitario"),
            ignorado=data.get("ignorado"),
            forma_venda=forma_venda,
            request=request,
        )
        return Response(ItemNotaListSerializer(item, context=self._ctx()).data)

    @extend_schema(
        summary="Sugestões de produto para item da nota (TrigramSimilarity)",
        responses={200: SugestoesProdutoSerializer(many=True)},
        tags=["Notas de Entrada"],
    )
    @action(detail=True, methods=["get"], url_path=r"itens/(?P<item_id>[^/.]+)/sugestoes-produto")
    def sugestoes_produto(self, request, pk=None, item_id=None):
        item = get_item_by_id(user=request.user, nota_id=pk, item_id=item_id)
        qs = sugestoes_produto(
            descricao=item.descricao_original,
            company_id=request.user.company_id,
        )
        return Response(SugestoesProdutoSerializer(qs, many=True, context=self._ctx()).data)

    # ── Histórico ─────────────────────────────────────────────────────────────

    @extend_schema(
        summary="Histórico operacional da nota fiscal",
        responses={200: HistoricoNotaSerializer(many=True)},
        tags=["Notas de Entrada"],
    )
    @action(detail=True, methods=["get"], url_path="historico")
    def historico(self, request, pk=None):
        self.get_object()
        qs = get_historico(user=request.user, nota_id=pk)
        return self._paginated(qs, HistoricoNotaSerializer)

    # ── Dashboard ─────────────────────────────────────────────────────────────

    @extend_schema(
        summary="Dashboard de notas fiscais de entrada",
        responses={200: DashboardNotasSerializer},
        tags=["Notas de Entrada"],
    )
    @action(detail=False, methods=["get"], url_path="dashboard")
    def dashboard(self, request):
        data = get_dashboard(user=request.user)
        return Response(DashboardNotasSerializer(data).data)
