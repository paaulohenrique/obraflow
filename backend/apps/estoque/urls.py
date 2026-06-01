from rest_framework.routers import SimpleRouter

from .views import (
    CategoriaViewSet,
    FormaVendaProdutoViewSet,
    FornecedorViewSet,
    MovimentacaoViewSet,
    ProdutoViewSet,
    UnidadeViewSet,
)

router = SimpleRouter()
router.register("unidades", UnidadeViewSet, basename="estoque-unidade")
router.register("categorias", CategoriaViewSet, basename="estoque-categoria")
router.register("fornecedores", FornecedorViewSet, basename="estoque-fornecedor")
router.register("produtos", ProdutoViewSet, basename="estoque-produto")
router.register("movimentacoes", MovimentacaoViewSet, basename="estoque-movimentacao")
router.register("formas-venda", FormaVendaProdutoViewSet, basename="estoque-forma-venda")

urlpatterns = router.urls
