from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view

from apps.core.pagination import StandardResultsSetPagination

from .filters import CaixaDiarioFilter, ContaPagarFilter, LancamentoFinanceiroFilter
from .models import (
    CaixaDiario,
    CategoriaFinanceira,
    ConfiguracaoFinanceiraOperacional,
    ContaFinanceira,
    ContaPagar,
    LancamentoFinanceiro,
)
from .permissions import FinanceiroPermission
from .selectors import (
    get_caixa_by_id,
    get_categoria_by_id,
    get_conta_financeira_by_id,
    get_conta_pagar_by_id,
    get_dashboard_financeiro,
    get_lancamento_by_id,
    get_caixas,
    get_categorias_financeiras,
    get_contas_financeiras,
    search_caixas,
    search_contas_pagar,
    search_lancamentos,
)
from .serializers import (
    AbrirCaixaSerializer,
    AjusteSaldoSerializer,
    CaixaDiarioDetailSerializer,
    CaixaDiarioListSerializer,
    CancelarContaPagarSerializer,
    CancelarLancamentoSerializer,
    CategoriaFinanceiraSerializer,
    ConfiguracaoFinanceiraOperacionalSerializer,
    ContaFinanceiraCreateSerializer,
    ContaFinanceiraDetailSerializer,
    ContaFinanceiraListSerializer,
    ContaFinanceiraUpdateSerializer,
    ContaPagarCreateSerializer,
    ContaPagarDetailSerializer,
    ContaPagarListSerializer,
    ContaPagarUpdateSerializer,
    DashboardFinanceiroSerializer,
    FecharCaixaSerializer,
    LancamentoFinanceiroCreateSerializer,
    LancamentoFinanceiroDetailSerializer,
    LancamentoFinanceiroListSerializer,
    PagarContaPagarSerializer,
    ReabrirCaixaSerializer,
)
from .services import (
    abrir_caixa,
    ajustar_saldo_conta,
    atualizar_configuracao_financeira_operacional,
    cancelar_conta_pagar,
    cancelar_lancamento_financeiro,
    criar_categoria_financeira,
    criar_conta_financeira,
    criar_conta_pagar,
    criar_lancamento_financeiro,
    fechar_caixa,
    get_or_create_configuracao_financeira_operacional,
    inativar_categoria_financeira,
    inativar_conta_financeira,
    pagar_conta_pagar,
    reabrir_caixa,
    update_categoria_financeira,
    update_conta_financeira,
)


_ORDERING = {
    "created_at",
    "-created_at",
    "updated_at",
    "-updated_at",
    "nome",
    "-nome",
    "data_lancamento",
    "-data_lancamento",
    "valor",
    "-valor",
    "data_vencimento",
    "-data_vencimento",
    "valor_restante",
    "-valor_restante",
    "data",
    "-data",
}


class _FinanceiroViewSet(viewsets.GenericViewSet):
    permission_classes = [FinanceiroPermission]

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


@extend_schema_view(
    list=extend_schema(summary="Listar contas financeiras", tags=["Financeiro - Contas"]),
    create=extend_schema(
        summary="Criar conta financeira",
        request=ContaFinanceiraCreateSerializer,
        responses={201: ContaFinanceiraDetailSerializer},
        examples=[
            OpenApiExample(
                "Conta banco",
                value={"nome": "Banco principal", "tipo": "BANCO", "observacao": "PIX"},
                request_only=True,
            )
        ],
        tags=["Financeiro - Contas"],
    ),
    retrieve=extend_schema(summary="Detalhar conta financeira", tags=["Financeiro - Contas"]),
    partial_update=extend_schema(
        summary="Atualizar conta financeira",
        request=ContaFinanceiraUpdateSerializer,
        responses={200: ContaFinanceiraDetailSerializer},
        tags=["Financeiro - Contas"],
    ),
)
class ContaFinanceiraViewSet(_FinanceiroViewSet):
    queryset = ContaFinanceira.objects.none()
    serializer_class = ContaFinanceiraDetailSerializer

    def list(self, request):
        qs = get_contas_financeiras(company_id=self._company_id()).order_by(self._ordering("nome"))
        return self._paginated(qs, ContaFinanceiraListSerializer)

    def create(self, request):
        serializer = ContaFinanceiraCreateSerializer(data=request.data, context=self._serializer_context())
        serializer.is_valid(raise_exception=True)
        conta = criar_conta_financeira(user=request.user, data=serializer.validated_data, request=request)
        return Response(ContaFinanceiraDetailSerializer(conta).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        conta = get_conta_financeira_by_id(company_id=self._company_id(), conta_id=pk)
        self.check_object_permissions(request, conta)
        return Response(ContaFinanceiraDetailSerializer(conta).data)

    def partial_update(self, request, pk=None):
        conta = get_conta_financeira_by_id(company_id=self._company_id(), conta_id=pk)
        self.check_object_permissions(request, conta)
        serializer = ContaFinanceiraUpdateSerializer(conta, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        conta = update_conta_financeira(
            user=request.user,
            conta=conta,
            data=serializer.validated_data,
            request=request,
        )
        return Response(ContaFinanceiraDetailSerializer(conta).data)

    @extend_schema(
        summary="Ajustar saldo da conta",
        description="Cria lançamento financeiro de ajuste; não altera saldo diretamente.",
        request=AjusteSaldoSerializer,
        responses={201: LancamentoFinanceiroDetailSerializer},
        examples=[
            OpenApiExample(
                "Ajuste inicial",
                value={"tipo": "ENTRADA", "valor": "1000.00", "descricao": "Saldo inicial"},
                request_only=True,
            )
        ],
        tags=["Financeiro - Contas"],
    )
    @action(detail=True, methods=["post"], url_path="ajustar-saldo")
    def ajustar_saldo(self, request, pk=None):
        conta = get_conta_financeira_by_id(company_id=self._company_id(), conta_id=pk)
        self.check_object_permissions(request, conta)
        serializer = AjusteSaldoSerializer(data=request.data, context=self._serializer_context())
        serializer.is_valid(raise_exception=True)
        lancamento = ajustar_saldo_conta(
            user=request.user,
            conta=conta,
            data=serializer.validated_data,
            request=request,
        )
        return Response(LancamentoFinanceiroDetailSerializer(lancamento).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Inativar conta financeira",
        responses={200: ContaFinanceiraDetailSerializer},
        tags=["Financeiro - Contas"],
    )
    @action(detail=True, methods=["post"], url_path="inativar")
    def inativar(self, request, pk=None):
        conta = get_conta_financeira_by_id(company_id=self._company_id(), conta_id=pk)
        self.check_object_permissions(request, conta)
        conta = inativar_conta_financeira(user=request.user, conta=conta, request=request)
        return Response(ContaFinanceiraDetailSerializer(conta).data)


class ConfiguracaoFinanceiraOperacionalViewSet(_FinanceiroViewSet):
    queryset = ConfiguracaoFinanceiraOperacional.objects.none()
    serializer_class = ConfiguracaoFinanceiraOperacionalSerializer

    @extend_schema(
        summary="Configuração financeira operacional",
        responses={200: ConfiguracaoFinanceiraOperacionalSerializer},
        tags=["Financeiro - Configurações"],
    )
    def list(self, request):
        config = get_or_create_configuracao_financeira_operacional(company_id=self._company_id())
        return Response(ConfiguracaoFinanceiraOperacionalSerializer(config, context=self._serializer_context()).data)

    @extend_schema(
        summary="Atualizar configuração financeira operacional",
        request=ConfiguracaoFinanceiraOperacionalSerializer,
        responses={200: ConfiguracaoFinanceiraOperacionalSerializer},
        tags=["Financeiro - Configurações"],
    )
    @action(detail=False, methods=["patch"], url_path="atualizar")
    def atualizar(self, request):
        config = get_or_create_configuracao_financeira_operacional(company_id=self._company_id())
        serializer = ConfiguracaoFinanceiraOperacionalSerializer(
            config,
            data=request.data,
            partial=True,
            context=self._serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        config = atualizar_configuracao_financeira_operacional(
            user=request.user,
            config=config,
            data=serializer.validated_data,
            request=request,
        )
        return Response(ConfiguracaoFinanceiraOperacionalSerializer(config, context=self._serializer_context()).data)


class CategoriaFinanceiraViewSet(_FinanceiroViewSet):
    queryset = CategoriaFinanceira.objects.none()
    serializer_class = CategoriaFinanceiraSerializer

    @extend_schema(summary="Listar categorias financeiras", tags=["Financeiro - Categorias"])
    def list(self, request):
        qs = get_categorias_financeiras(company_id=self._company_id()).order_by("tipo", "nome")
        return self._paginated(qs, CategoriaFinanceiraSerializer)

    @extend_schema(
        summary="Criar categoria financeira",
        request=CategoriaFinanceiraSerializer,
        responses={201: CategoriaFinanceiraSerializer},
        tags=["Financeiro - Categorias"],
    )
    def create(self, request):
        serializer = CategoriaFinanceiraSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        categoria = criar_categoria_financeira(
            user=request.user,
            data=serializer.validated_data,
            request=request,
        )
        return Response(CategoriaFinanceiraSerializer(categoria).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Detalhar categoria financeira", tags=["Financeiro - Categorias"])
    def retrieve(self, request, pk=None):
        categoria = get_categoria_by_id(company_id=self._company_id(), categoria_id=pk)
        self.check_object_permissions(request, categoria)
        return Response(CategoriaFinanceiraSerializer(categoria).data)

    @extend_schema(
        summary="Atualizar categoria financeira",
        request=CategoriaFinanceiraSerializer,
        responses={200: CategoriaFinanceiraSerializer},
        tags=["Financeiro - Categorias"],
    )
    def partial_update(self, request, pk=None):
        categoria = get_categoria_by_id(company_id=self._company_id(), categoria_id=pk)
        self.check_object_permissions(request, categoria)
        serializer = CategoriaFinanceiraSerializer(categoria, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        categoria = update_categoria_financeira(
            user=request.user,
            categoria=categoria,
            data=serializer.validated_data,
            request=request,
        )
        return Response(CategoriaFinanceiraSerializer(categoria).data)

    @extend_schema(
        summary="Inativar categoria financeira",
        responses={200: CategoriaFinanceiraSerializer},
        tags=["Financeiro - Categorias"],
    )
    @action(detail=True, methods=["post"], url_path="inativar")
    def inativar(self, request, pk=None):
        categoria = get_categoria_by_id(company_id=self._company_id(), categoria_id=pk)
        self.check_object_permissions(request, categoria)
        categoria = inativar_categoria_financeira(user=request.user, categoria=categoria, request=request)
        return Response(CategoriaFinanceiraSerializer(categoria).data)


class LancamentoFinanceiroViewSet(_FinanceiroViewSet):
    queryset = LancamentoFinanceiro.objects.none()
    serializer_class = LancamentoFinanceiroDetailSerializer
    filterset_class = LancamentoFinanceiroFilter

    @extend_schema(summary="Listar lançamentos financeiros", tags=["Financeiro - Lançamentos"])
    def list(self, request):
        qs = search_lancamentos(company_id=self._company_id(), filters=request.query_params.dict())
        qs = qs.order_by(self._ordering("-data_lancamento"))
        return self._paginated(qs, LancamentoFinanceiroListSerializer)

    @extend_schema(
        summary="Criar lançamento manual",
        request=LancamentoFinanceiroCreateSerializer,
        responses={201: LancamentoFinanceiroDetailSerializer},
        tags=["Financeiro - Lançamentos"],
    )
    def create(self, request):
        serializer = LancamentoFinanceiroCreateSerializer(data=request.data, context=self._serializer_context())
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        lancamento = criar_lancamento_financeiro(
            user=request.user,
            conta_financeira=data["conta_financeira"],
            categoria=data["categoria"],
            tipo=data["tipo"],
            valor=data["valor"],
            data_lancamento=data.get("data_lancamento"),
            descricao=data.get("descricao", ""),
            origem_tipo=LancamentoFinanceiro.ORIGEM_MANUAL,
            forma_pagamento=data.get("forma_pagamento", LancamentoFinanceiro.FORMA_OUTRO),
            caixa_diario=data.get("caixa_diario"),
            idempotency_key=data.get("idempotency_key", ""),
            metadata=data.get("metadata") or {},
            request=request,
        )
        return Response(LancamentoFinanceiroDetailSerializer(lancamento).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Detalhar lançamento financeiro", tags=["Financeiro - Lançamentos"])
    def retrieve(self, request, pk=None):
        lancamento = get_lancamento_by_id(company_id=self._company_id(), lancamento_id=pk)
        self.check_object_permissions(request, lancamento)
        return Response(LancamentoFinanceiroDetailSerializer(lancamento).data)

    @extend_schema(
        summary="Cancelar lançamento financeiro",
        description="Cancela o lançamento original e cria lançamento reverso de estorno.",
        request=CancelarLancamentoSerializer,
        responses={200: LancamentoFinanceiroDetailSerializer},
        tags=["Financeiro - Lançamentos"],
    )
    @action(detail=True, methods=["post"], url_path="cancelar")
    def cancelar(self, request, pk=None):
        lancamento = get_lancamento_by_id(company_id=self._company_id(), lancamento_id=pk)
        self.check_object_permissions(request, lancamento)
        serializer = CancelarLancamentoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        estorno = cancelar_lancamento_financeiro(
            user=request.user,
            lancamento=lancamento,
            **serializer.validated_data,
            request=request,
        )
        return Response(LancamentoFinanceiroDetailSerializer(estorno).data)


class ContaPagarViewSet(_FinanceiroViewSet):
    queryset = ContaPagar.objects.none()
    serializer_class = ContaPagarDetailSerializer
    filterset_class = ContaPagarFilter

    @extend_schema(summary="Listar contas a pagar", tags=["Financeiro - Contas a Pagar"])
    def list(self, request):
        qs = search_contas_pagar(company_id=self._company_id(), filters=request.query_params.dict())
        qs = qs.order_by(self._ordering("-data_vencimento"))
        return self._paginated(qs, ContaPagarListSerializer)

    @extend_schema(
        summary="Criar conta a pagar",
        request=ContaPagarCreateSerializer,
        responses={201: ContaPagarDetailSerializer},
        tags=["Financeiro - Contas a Pagar"],
    )
    def create(self, request):
        serializer = ContaPagarCreateSerializer(data=request.data, context=self._serializer_context())
        serializer.is_valid(raise_exception=True)
        conta = criar_conta_pagar(user=request.user, data=serializer.validated_data, request=request)
        return Response(ContaPagarDetailSerializer(conta).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Detalhar conta a pagar", tags=["Financeiro - Contas a Pagar"])
    def retrieve(self, request, pk=None):
        conta = get_conta_pagar_by_id(company_id=self._company_id(), conta_id=pk)
        self.check_object_permissions(request, conta)
        return Response(ContaPagarDetailSerializer(conta).data)

    @extend_schema(
        summary="Atualizar conta a pagar",
        request=ContaPagarUpdateSerializer,
        responses={200: ContaPagarDetailSerializer},
        tags=["Financeiro - Contas a Pagar"],
    )
    def partial_update(self, request, pk=None):
        from .services.conta_pagar import update_conta_pagar

        conta = get_conta_pagar_by_id(company_id=self._company_id(), conta_id=pk)
        self.check_object_permissions(request, conta)
        serializer = ContaPagarUpdateSerializer(conta, data=request.data, partial=True, context=self._serializer_context())
        serializer.is_valid(raise_exception=True)
        conta = update_conta_pagar(
            user=request.user,
            conta=conta,
            data=serializer.validated_data,
            request=request,
        )
        return Response(ContaPagarDetailSerializer(conta).data)

    @extend_schema(
        summary="Pagar conta a pagar",
        request=PagarContaPagarSerializer,
        responses={200: ContaPagarDetailSerializer},
        tags=["Financeiro - Contas a Pagar"],
    )
    @action(detail=True, methods=["post"], url_path="pagar")
    def pagar(self, request, pk=None):
        conta = get_conta_pagar_by_id(company_id=self._company_id(), conta_id=pk)
        self.check_object_permissions(request, conta)
        serializer = PagarContaPagarSerializer(data=request.data, context=self._serializer_context())
        serializer.is_valid(raise_exception=True)
        conta = pagar_conta_pagar(
            user=request.user,
            conta=conta,
            data=serializer.validated_data,
            request=request,
        )
        return Response(ContaPagarDetailSerializer(conta).data)

    @extend_schema(
        summary="Cancelar conta a pagar",
        request=CancelarContaPagarSerializer,
        responses={200: ContaPagarDetailSerializer},
        tags=["Financeiro - Contas a Pagar"],
    )
    @action(detail=True, methods=["post"], url_path="cancelar")
    def cancelar(self, request, pk=None):
        conta = get_conta_pagar_by_id(company_id=self._company_id(), conta_id=pk)
        self.check_object_permissions(request, conta)
        serializer = CancelarContaPagarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conta = cancelar_conta_pagar(
            user=request.user,
            conta=conta,
            **serializer.validated_data,
            request=request,
        )
        return Response(ContaPagarDetailSerializer(conta).data)


class CaixaDiarioViewSet(_FinanceiroViewSet):
    queryset = CaixaDiario.objects.none()
    serializer_class = CaixaDiarioDetailSerializer
    filterset_class = CaixaDiarioFilter

    @extend_schema(summary="Listar caixas diários", tags=["Financeiro - Caixa"])
    def list(self, request):
        qs = search_caixas(company_id=self._company_id(), filters=request.query_params.dict())
        qs = qs.order_by(self._ordering("-data"))
        return self._paginated(qs, CaixaDiarioListSerializer)

    @extend_schema(summary="Detalhar caixa diário", tags=["Financeiro - Caixa"])
    def retrieve(self, request, pk=None):
        caixa = get_caixa_by_id(company_id=self._company_id(), caixa_id=pk)
        self.check_object_permissions(request, caixa)
        return Response(CaixaDiarioDetailSerializer(caixa).data)

    @extend_schema(
        summary="Abrir caixa diário",
        request=AbrirCaixaSerializer,
        responses={201: CaixaDiarioDetailSerializer},
        tags=["Financeiro - Caixa"],
    )
    @action(detail=False, methods=["post"], url_path="abrir")
    def abrir(self, request):
        serializer = AbrirCaixaSerializer(data=request.data, context=self._serializer_context())
        serializer.is_valid(raise_exception=True)
        caixa = abrir_caixa(user=request.user, data=serializer.validated_data, request=request)
        return Response(CaixaDiarioDetailSerializer(caixa).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Fechar caixa diário",
        request=FecharCaixaSerializer,
        responses={200: CaixaDiarioDetailSerializer},
        tags=["Financeiro - Caixa"],
    )
    @action(detail=True, methods=["post"], url_path="fechar")
    def fechar(self, request, pk=None):
        caixa = get_caixa_by_id(company_id=self._company_id(), caixa_id=pk)
        self.check_object_permissions(request, caixa)
        serializer = FecharCaixaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        caixa = fechar_caixa(user=request.user, caixa=caixa, data=serializer.validated_data, request=request)
        return Response(CaixaDiarioDetailSerializer(caixa).data)

    @extend_schema(
        summary="Reabrir caixa diário",
        request=ReabrirCaixaSerializer,
        responses={200: CaixaDiarioDetailSerializer},
        tags=["Financeiro - Caixa"],
    )
    @action(detail=True, methods=["post"], url_path="reabrir")
    def reabrir(self, request, pk=None):
        caixa = get_caixa_by_id(company_id=self._company_id(), caixa_id=pk)
        self.check_object_permissions(request, caixa)
        serializer = ReabrirCaixaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        caixa = reabrir_caixa(user=request.user, caixa=caixa, data=serializer.validated_data, request=request)
        return Response(CaixaDiarioDetailSerializer(caixa).data)


class DashboardFinanceiroViewSet(_FinanceiroViewSet):
    queryset = LancamentoFinanceiro.objects.none()
    serializer_class = DashboardFinanceiroSerializer

    @extend_schema(
        summary="Dashboard financeiro",
        responses={200: DashboardFinanceiroSerializer},
        tags=["Financeiro - Dashboard"],
    )
    def list(self, request):
        data = get_dashboard_financeiro(company_id=self._company_id())
        return Response(DashboardFinanceiroSerializer(data).data)
