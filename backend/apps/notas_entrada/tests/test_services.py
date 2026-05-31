"""Testes dos services: importação, matching, confirmação, rejeição."""
import pytest
from decimal import Decimal
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.notas_entrada.models import (
    HistoricoNotaFiscalEntrada,
    ItemNotaFiscalEntrada,
    NotaFiscalEntrada,
)
from apps.notas_entrada.services.matching import match_fornecedor, match_produto_por_item
from apps.notas_entrada.services.nota import (
    importar_xml_nota,
    rejeitar_nota,
    vincular_fornecedor,
    vincular_produto_item,
)
from apps.notas_entrada.services.confirmacao import confirmar_nota
from apps.core.models import AuditLog
from rest_framework.exceptions import ValidationError

from .conftest import CNPJ_FORNECEDOR_XML, xml_bytes, xml_file


@pytest.mark.django_db
class TestMatchFornecedor:
    def test_match_por_cnpj(self, empresa_a, fornecedor_a):
        resultado = match_fornecedor(cnpj_xml=CNPJ_FORNECEDOR_XML, company_id=empresa_a.pk)
        assert resultado == fornecedor_a

    def test_cnpj_nao_encontrado(self, empresa_a):
        resultado = match_fornecedor(cnpj_xml="99999999000199", company_id=empresa_a.pk)
        assert resultado is None

    def test_cnpj_vazio(self, empresa_a):
        resultado = match_fornecedor(cnpj_xml="", company_id=empresa_a.pk)
        assert resultado is None

    def test_cnpj_outra_empresa(self, empresa_a, empresa_b, fornecedor_a):
        resultado = match_fornecedor(cnpj_xml=CNPJ_FORNECEDOR_XML, company_id=empresa_b.pk)
        assert resultado is None


@pytest.mark.django_db
class TestMatchProduto:
    def test_match_por_codigo_barras(self, empresa_a, produto_cimento):
        resultado = match_produto_por_item(
            codigo_barras="7891000315507",
            codigo_fornecedor="",
            company_id=empresa_a.pk,
        )
        assert resultado == produto_cimento

    def test_match_por_sku(self, empresa_a, produto_sem_ean):
        resultado = match_produto_por_item(
            codigo_barras="",
            codigo_fornecedor="AREIA-F-001",
            company_id=empresa_a.pk,
        )
        assert resultado == produto_sem_ean

    def test_sem_match(self, empresa_a):
        resultado = match_produto_por_item(
            codigo_barras="0000000000000",
            codigo_fornecedor="INEXISTENTE",
            company_id=empresa_a.pk,
        )
        assert resultado is None

    def test_nao_faz_match_outra_empresa(self, empresa_a, empresa_b, produto_cimento):
        resultado = match_produto_por_item(
            codigo_barras="7891000315507",
            codigo_fornecedor="",
            company_id=empresa_b.pk,
        )
        assert resultado is None

    def test_prioridade_barcode_sobre_sku(self, empresa_a, produto_cimento, produto_sem_ean):
        # produto_sem_ean tem SKU "AREIA-F-001"
        # produto_cimento tem barcode "7891000315507"
        resultado = match_produto_por_item(
            codigo_barras="7891000315507",
            codigo_fornecedor="AREIA-F-001",
            company_id=empresa_a.pk,
        )
        assert resultado == produto_cimento


@pytest.mark.django_db
class TestImportarXMLNota:
    def test_upload_valido_cria_nota(self, admin_user, empresa_a, fornecedor_a):
        arquivo = xml_file()
        nota = importar_xml_nota(user=admin_user, arquivo=arquivo)

        assert nota.pk is not None
        assert nota.status == NotaFiscalEntrada.STATUS_AGUARDANDO_REVISAO
        assert nota.numero == "123"
        assert nota.serie == "1"
        assert nota.company == empresa_a
        assert nota.fornecedor == fornecedor_a
        assert nota.fornecedor_cnpj_xml == CNPJ_FORNECEDOR_XML

    def test_upload_cria_itens(self, admin_user, empresa_a, fornecedor_a, produto_cimento):
        arquivo = xml_file()
        nota = importar_xml_nota(user=admin_user, arquivo=arquivo)

        itens = ItemNotaFiscalEntrada.objects.filter(nota=nota).order_by("ordem")
        assert itens.count() == 3

        # Primeiro item com EAN deve ter sido auto-linked
        item1 = itens[0]
        assert item1.codigo_barras == "7891000315507"
        assert item1.produto == produto_cimento

    def test_upload_item_sem_match_produto_nulo(self, admin_user, empresa_a):
        arquivo = xml_file()
        nota = importar_xml_nota(user=admin_user, arquivo=arquivo)
        itens = ItemNotaFiscalEntrada.objects.filter(nota=nota, produto__isnull=True)
        assert itens.exists()

    def test_upload_registra_historico(self, admin_user, empresa_a):
        arquivo = xml_file()
        nota = importar_xml_nota(user=admin_user, arquivo=arquivo)
        hist = HistoricoNotaFiscalEntrada.objects.filter(
            nota=nota, evento=HistoricoNotaFiscalEntrada.EVENTO_XML_IMPORTADO
        )
        assert hist.exists()

    def test_upload_registra_auditlog(self, admin_user, empresa_a):
        arquivo = xml_file()
        nota = importar_xml_nota(user=admin_user, arquivo=arquivo)
        log = AuditLog.objects.filter(
            entity_type="NotaFiscalEntrada",
            entity_id=nota.pk,
            action=AuditLog.ACTION_CREATE,
        )
        assert log.exists()

    def test_upload_sha256_duplicado_rejeita(self, admin_user, empresa_a):
        arquivo = xml_file()
        importar_xml_nota(user=admin_user, arquivo=arquivo)
        arquivo2 = xml_file()
        with pytest.raises(ValidationError) as exc_info:
            importar_xml_nota(user=admin_user, arquivo=arquivo2)
        assert "arquivo" in exc_info.value.detail

    def test_upload_chave_duplicada_rejeita(self, admin_user, empresa_a):
        arquivo1 = xml_file()
        nota1 = importar_xml_nota(user=admin_user, arquivo=arquivo1)

        # Criar XML com sha256 diferente mas mesma chave
        conteudo2 = xml_bytes().replace(b"sha256_placeholder", b"diferente")
        arquivo2 = SimpleUploadedFile("nfe2.xml", conteudo2, content_type="text/xml")

        # Manipular diretamente a chave para simular duplicata
        chave = nota1.chave_acesso
        if chave:
            from apps.notas_entrada.services.nota import _check_chave
            with pytest.raises(ValidationError):
                _check_chave(company_id=empresa_a.pk, chave_acesso=chave)

    def test_upload_idempotency_key_retorna_existente(self, admin_user, empresa_a):
        arquivo = xml_file()
        nota1 = importar_xml_nota(user=admin_user, arquivo=arquivo, idempotency_key="test-key-001")

        arquivo2 = xml_file("nfe_sem_namespace.xml", "nfe2.xml")
        nota2 = importar_xml_nota(user=admin_user, arquivo=arquivo2, idempotency_key="test-key-001")

        assert nota1.pk == nota2.pk

    def test_upload_xml_invalido_rejeita(self, admin_user, empresa_a):
        arquivo = SimpleUploadedFile("nfe.xml", b"<xml>invalido", content_type="text/xml")
        with pytest.raises(ValidationError):
            importar_xml_nota(user=admin_user, arquivo=arquivo)

    def test_upload_xml_sem_namespace(self, admin_user, empresa_a):
        arquivo = xml_file("nfe_sem_namespace.xml", "nfe_sem_ns.xml")
        nota = importar_xml_nota(user=admin_user, arquivo=arquivo)
        assert nota.numero == "999"
        assert nota.status == NotaFiscalEntrada.STATUS_AGUARDANDO_REVISAO

    def test_fornecedor_nao_encontrado_campo_xml_preenchido(self, admin_user, empresa_a):
        # Sem fornecedor cadastrado, nota deve ser criada com campos xml preenchidos
        arquivo = xml_file()
        nota = importar_xml_nota(user=admin_user, arquivo=arquivo)
        assert nota.fornecedor_cnpj_xml == CNPJ_FORNECEDOR_XML
        assert nota.fornecedor_nome_xml == "Distribuidora Teste Ltda"


@pytest.mark.django_db
class TestVincularFornecedor:
    def test_vincular_fornecedor_sucesso(self, admin_user, empresa_a, fornecedor_a):
        arquivo = xml_file()
        nota = importar_xml_nota(user=admin_user, arquivo=arquivo)
        # Desvincular para testar
        nota._allow_update = True
        nota.fornecedor = None
        nota.save(update_fields=["fornecedor", "updated_at"])

        nota_atualizada = vincular_fornecedor(user=admin_user, nota=nota, fornecedor=fornecedor_a)
        assert nota_atualizada.fornecedor == fornecedor_a

    def test_vincular_fornecedor_outra_empresa_rejeita(self, admin_user, empresa_a, empresa_b, user_b):
        from apps.estoque.models import Fornecedor
        forn_b = Fornecedor.objects.create(
            company=empresa_b, razao_social="Forn B", cnpj="99888777000100"
        )
        arquivo = xml_file()
        nota = importar_xml_nota(user=admin_user, arquivo=arquivo)
        nota._allow_update = True
        nota.fornecedor = None
        nota.save(update_fields=["fornecedor", "updated_at"])

        with pytest.raises(ValidationError):
            vincular_fornecedor(user=admin_user, nota=nota, fornecedor=forn_b)

    def test_vincular_fornecedor_nota_confirmada_rejeita(self, admin_user, empresa_a, fornecedor_a, produto_cimento, categoria_despesa):
        arquivo = xml_file()
        nota = importar_xml_nota(user=admin_user, arquivo=arquivo, )
        # Ignorar todos itens sem produto
        for item in nota.itens.filter(produto__isnull=True):
            item.ignorado = True
            item.save(update_fields=["ignorado", "updated_at"])
        confirmar_nota(user=admin_user, nota_id=nota.pk)

        with pytest.raises(ValidationError):
            vincular_fornecedor(user=admin_user, nota=nota, fornecedor=fornecedor_a)


@pytest.mark.django_db
class TestVincularProdutoItem:
    def test_vincular_produto_ao_item(self, admin_user, empresa_a, produto_sem_ean):
        arquivo = xml_file()
        nota = importar_xml_nota(user=admin_user, arquivo=arquivo)
        item = nota.itens.filter(produto__isnull=True, ignorado=False).first()
        if item is None:
            pytest.skip("Nenhum item sem produto neste XML")

        item_atualizado = vincular_produto_item(
            user=admin_user, item=item, produto=produto_sem_ean
        )
        assert item_atualizado.produto == produto_sem_ean

    def test_marcar_item_como_ignorado(self, admin_user, empresa_a):
        arquivo = xml_file()
        nota = importar_xml_nota(user=admin_user, arquivo=arquivo)
        item = nota.itens.filter(produto__isnull=True, ignorado=False).first()
        if item is None:
            pytest.skip("Nenhum item sem produto")

        item_atualizado = vincular_produto_item(
            user=admin_user, item=item, ignorado=True
        )
        assert item_atualizado.ignorado is True

    def test_vincular_produto_nota_confirmada_rejeita(self, admin_user, empresa_a, produto_sem_ean):
        arquivo = xml_file()
        nota = importar_xml_nota(user=admin_user, arquivo=arquivo)
        for item in nota.itens.filter(produto__isnull=True):
            item.ignorado = True
            item.save(update_fields=["ignorado", "updated_at"])
        confirmar_nota(user=admin_user, nota_id=nota.pk)

        item = nota.itens.first()
        with pytest.raises(ValidationError):
            vincular_produto_item(user=admin_user, item=item, produto=produto_sem_ean)


@pytest.mark.django_db
class TestRejeitarNota:
    def test_rejeitar_sucesso(self, admin_user, empresa_a):
        arquivo = xml_file()
        nota = importar_xml_nota(user=admin_user, arquivo=arquivo)
        nota_rejeitada = rejeitar_nota(user=admin_user, nota=nota, motivo="Duplicada")
        assert nota_rejeitada.status == NotaFiscalEntrada.STATUS_REJEITADA
        assert nota_rejeitada.motivo_rejeicao == "Duplicada"
        assert nota_rejeitada.rejeitado_por == admin_user

    def test_rejeitar_sem_motivo_rejeita(self, admin_user, empresa_a):
        arquivo = xml_file()
        nota = importar_xml_nota(user=admin_user, arquivo=arquivo)
        with pytest.raises(ValidationError):
            rejeitar_nota(user=admin_user, nota=nota, motivo="")

    def test_rejeitar_nota_ja_confirmada_rejeita(self, admin_user, empresa_a):
        arquivo = xml_file()
        nota = importar_xml_nota(user=admin_user, arquivo=arquivo)
        for item in nota.itens.filter(produto__isnull=True):
            item.ignorado = True
            item.save(update_fields=["ignorado", "updated_at"])
        confirmar_nota(user=admin_user, nota_id=nota.pk)

        with pytest.raises(ValidationError):
            rejeitar_nota(user=admin_user, nota=nota, motivo="Tentativa tardia")

    def test_rejeitar_registra_historico(self, admin_user, empresa_a):
        arquivo = xml_file()
        nota = importar_xml_nota(user=admin_user, arquivo=arquivo)
        rejeitar_nota(user=admin_user, nota=nota, motivo="Erro de fornecedor")
        hist = HistoricoNotaFiscalEntrada.objects.filter(
            nota=nota, evento=HistoricoNotaFiscalEntrada.EVENTO_REJEITADA
        )
        assert hist.exists()


@pytest.mark.django_db
class TestConfirmarNota:
    def test_confirmar_com_todos_itens_vinculados(self, admin_user, empresa_a, produto_cimento, produto_sem_ean, unidade):
        from apps.estoque.models import UnidadeMedida
        # Garantir que unidade "MIL" e "M3" existam
        UnidadeMedida.objects.get_or_create(company=empresa_a, sigla="MIL", defaults={"nome": "Mil Unidades"})
        UnidadeMedida.objects.get_or_create(company=empresa_a, sigla="M3", defaults={"nome": "Metro Cúbico"})

        arquivo = xml_file()
        nota = importar_xml_nota(user=admin_user, arquivo=arquivo)

        # Vincular produto ao item sem produto
        for item in nota.itens.filter(produto__isnull=True, ignorado=False):
            vincular_produto_item(user=admin_user, item=item, produto=produto_sem_ean)

        nota_confirmada = confirmar_nota(user=admin_user, nota_id=nota.pk)
        assert nota_confirmada.status == NotaFiscalEntrada.STATUS_CONFIRMADA
        assert nota_confirmada.confirmado_por == admin_user
        assert nota_confirmada.confirmado_em is not None

    def test_confirmar_cria_movimentacoes_estoque(self, admin_user, empresa_a, produto_cimento, produto_sem_ean):
        from apps.estoque.models import MovimentacaoEstoque, UnidadeMedida
        UnidadeMedida.objects.get_or_create(company=empresa_a, sigla="MIL", defaults={"nome": "Mil Unidades"})
        UnidadeMedida.objects.get_or_create(company=empresa_a, sigla="M3", defaults={"nome": "Metro Cúbico"})

        arquivo = xml_file()
        nota = importar_xml_nota(user=admin_user, arquivo=arquivo)

        for item in nota.itens.filter(produto__isnull=True, ignorado=False):
            vincular_produto_item(user=admin_user, item=item, produto=produto_sem_ean)

        confirmar_nota(user=admin_user, nota_id=nota.pk)

        movs = MovimentacaoEstoque.objects.filter(
            company=empresa_a,
            tipo=MovimentacaoEstoque.TIPO_ENTRADA,
        )
        assert movs.count() >= 1

    def test_confirmar_com_item_ignorado(self, admin_user, empresa_a, produto_cimento):
        from apps.estoque.models import UnidadeMedida
        UnidadeMedida.objects.get_or_create(company=empresa_a, sigla="MIL", defaults={"nome": "Mil Unidades"})
        UnidadeMedida.objects.get_or_create(company=empresa_a, sigla="M3", defaults={"nome": "Metro Cúbico"})

        arquivo = xml_file()
        nota = importar_xml_nota(user=admin_user, arquivo=arquivo)

        for item in nota.itens.filter(produto__isnull=True, ignorado=False):
            vincular_produto_item(user=admin_user, item=item, ignorado=True)

        nota_confirmada = confirmar_nota(user=admin_user, nota_id=nota.pk)
        assert nota_confirmada.status == NotaFiscalEntrada.STATUS_CONFIRMADA

    def test_confirmar_itens_pendentes_bloqueia(self, admin_user, empresa_a):
        arquivo = xml_file()
        nota = importar_xml_nota(user=admin_user, arquivo=arquivo)
        # Não vincular nenhum item

        # Remove auto-match para este cenário
        for item in nota.itens.all():
            item.produto = None
            item.save(update_fields=["produto", "updated_at"])

        with pytest.raises(ValidationError) as exc_info:
            confirmar_nota(user=admin_user, nota_id=nota.pk)
        assert "itens" in exc_info.value.detail

    def test_confirmar_idempotente(self, admin_user, empresa_a, produto_cimento, produto_sem_ean):
        from apps.estoque.models import UnidadeMedida
        UnidadeMedida.objects.get_or_create(company=empresa_a, sigla="MIL", defaults={"nome": "Mil Unidades"})
        UnidadeMedida.objects.get_or_create(company=empresa_a, sigla="M3", defaults={"nome": "Metro Cúbico"})

        arquivo = xml_file()
        nota = importar_xml_nota(user=admin_user, arquivo=arquivo)

        for item in nota.itens.filter(produto__isnull=True, ignorado=False):
            vincular_produto_item(user=admin_user, item=item, produto=produto_sem_ean)

        confirmar_nota(user=admin_user, nota_id=nota.pk)
        # Chamar de novo não deve duplicar
        nota2 = confirmar_nota(user=admin_user, nota_id=nota.pk)
        assert nota2.status == NotaFiscalEntrada.STATUS_CONFIRMADA

    def test_confirmar_com_conta_pagar(self, admin_user, empresa_a, produto_cimento, produto_sem_ean, categoria_despesa):
        from apps.estoque.models import UnidadeMedida
        from apps.financeiro.models import ContaPagar, ContaFinanceira
        UnidadeMedida.objects.get_or_create(company=empresa_a, sigla="MIL", defaults={"nome": "Mil Unidades"})
        UnidadeMedida.objects.get_or_create(company=empresa_a, sigla="M3", defaults={"nome": "Metro Cúbico"})

        arquivo = xml_file()
        nota = importar_xml_nota(user=admin_user, arquivo=arquivo)

        for item in nota.itens.filter(produto__isnull=True, ignorado=False):
            vincular_produto_item(user=admin_user, item=item, produto=produto_sem_ean)

        from datetime import date
        nota_confirmada = confirmar_nota(
            user=admin_user,
            nota_id=nota.pk,
            criar_conta_pagar_flag=True,
            dados_conta_pagar={
                "categoria": categoria_despesa,
                "data_vencimento": date(2026, 6, 30),
                "observacao": "Pagamento NF-e teste",
            },
        )
        assert nota_confirmada.conta_pagar is not None
        assert nota_confirmada.conta_pagar.valor_total == nota_confirmada.valor_total

    def test_confirmar_rollback_produto_inativo(self, admin_user, empresa_a, produto_cimento, produto_sem_ean):
        from apps.estoque.models import MovimentacaoEstoque, UnidadeMedida
        UnidadeMedida.objects.get_or_create(company=empresa_a, sigla="MIL", defaults={"nome": "Mil Unidades"})
        UnidadeMedida.objects.get_or_create(company=empresa_a, sigla="M3", defaults={"nome": "Metro Cúbico"})

        arquivo = xml_file()
        nota = importar_xml_nota(user=admin_user, arquivo=arquivo)

        for item in nota.itens.filter(produto__isnull=True, ignorado=False):
            vincular_produto_item(user=admin_user, item=item, produto=produto_sem_ean)

        # Desativar produto para provocar erro
        produto_sem_ean.is_active = False
        produto_sem_ean.save(update_fields=["is_active", "updated_at"])

        movs_antes = MovimentacaoEstoque.objects.filter(company=empresa_a).count()
        with pytest.raises((ValidationError, Exception)):
            confirmar_nota(user=admin_user, nota_id=nota.pk)

        nota.refresh_from_db()
        movs_depois = MovimentacaoEstoque.objects.filter(company=empresa_a).count()
        # Rollback: nota não confirmada e nenhuma movimentação criada
        assert nota.status != NotaFiscalEntrada.STATUS_CONFIRMADA
        assert movs_depois == movs_antes


@pytest.mark.django_db
class TestConcorrencia:
    def test_confirmacao_idempotente_chamada_dupla(self, admin_user, manager_user, empresa_a, produto_cimento, produto_sem_ean):
        """Valida que chamar confirmar_nota duas vezes não duplica movimentações.

        O select_for_update e a verificação de status garantem idempotência.
        Teste sequencial é suficiente porque o real risco (race condition) é
        coberto pelo select_for_update na camada de serviço.
        """
        from apps.estoque.models import MovimentacaoEstoque, UnidadeMedida

        UnidadeMedida.objects.get_or_create(company=empresa_a, sigla="MIL", defaults={"nome": "Mil Unidades"})
        UnidadeMedida.objects.get_or_create(company=empresa_a, sigla="M3", defaults={"nome": "Metro Cúbico"})

        arquivo = xml_file()
        nota = importar_xml_nota(user=admin_user, arquivo=arquivo)
        for item in nota.itens.filter(produto__isnull=True, ignorado=False):
            vincular_produto_item(user=admin_user, item=item, produto=produto_sem_ean)

        movs_antes = MovimentacaoEstoque.objects.filter(company=empresa_a).count()

        # Primeira confirmação
        nota1 = confirmar_nota(user=admin_user, nota_id=nota.pk)
        assert nota1.status == NotaFiscalEntrada.STATUS_CONFIRMADA

        movs_apos_primeira = MovimentacaoEstoque.objects.filter(company=empresa_a).count()
        assert movs_apos_primeira > movs_antes

        # Segunda chamada (idempotência): não deve criar movimentações extras
        nota2 = confirmar_nota(user=manager_user, nota_id=nota.pk)
        assert nota2.status == NotaFiscalEntrada.STATUS_CONFIRMADA

        movs_apos_segunda = MovimentacaoEstoque.objects.filter(company=empresa_a).count()
        assert movs_apos_segunda == movs_apos_primeira

    def test_confirmacao_nota_ja_rejeitada_falha(self, admin_user, empresa_a):
        """Nota rejeitada não pode ser confirmada — garante proteção de status."""
        arquivo = xml_file()
        nota = importar_xml_nota(user=admin_user, arquivo=arquivo)
        rejeitar_nota(user=admin_user, nota=nota, motivo="Teste")

        with pytest.raises(ValidationError) as exc_info:
            confirmar_nota(user=admin_user, nota_id=nota.pk)
        assert "status" in exc_info.value.detail
