"""Testes de models, constraints e imutabilidade."""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.notas_entrada.models import (
    HistoricoNotaFiscalEntrada,
    ItemNotaFiscalEntrada,
    NotaFiscalEntrada,
)

from .conftest import CNPJ_FORNECEDOR_XML


@pytest.mark.django_db
class TestNotaFiscalEntradaModel:
    def test_str(self, empresa_a, admin_user):
        nota = NotaFiscalEntrada.objects.create(
            company=empresa_a,
            numero="001",
            serie="1",
            modelo="55",
            data_emissao="2026-05-30",
            valor_total="1000.00",
            valor_produtos="1000.00",
            criado_por=admin_user,
        )
        assert "001" in str(nota)
        assert "AGUARDANDO_REVISAO" in str(nota)

    def test_status_default(self, empresa_a, admin_user):
        nota = NotaFiscalEntrada.objects.create(
            company=empresa_a,
            numero="002",
            serie="1",
            modelo="55",
            data_emissao="2026-05-30",
            valor_total="0.00",
            valor_produtos="0.00",
            criado_por=admin_user,
        )
        assert nota.status == NotaFiscalEntrada.STATUS_AGUARDANDO_REVISAO

    def test_unique_chave_acesso_por_empresa(self, empresa_a, empresa_b, admin_user):
        chave = "35210112345678000195550010000001231000012340"
        NotaFiscalEntrada.objects.create(
            company=empresa_a,
            numero="001",
            serie="1",
            modelo="55",
            data_emissao="2026-05-30",
            valor_total="100.00",
            valor_produtos="100.00",
            chave_acesso=chave,
            sha256="abc123",
            criado_por=admin_user,
        )
        # Mesma chave em empresa diferente: OK
        NotaFiscalEntrada.objects.create(
            company=empresa_b,
            numero="001",
            serie="1",
            modelo="55",
            data_emissao="2026-05-30",
            valor_total="100.00",
            valor_produtos="100.00",
            chave_acesso=chave,
            sha256="def456",
        )
        # Mesma chave na mesma empresa: IntegrityError
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                NotaFiscalEntrada.objects.create(
                    company=empresa_a,
                    numero="002",
                    serie="1",
                    modelo="55",
                    data_emissao="2026-05-30",
                    valor_total="100.00",
                    valor_produtos="100.00",
                    chave_acesso=chave,
                    sha256="ghi789",
                    criado_por=admin_user,
                )

    def test_unique_sha256_por_empresa(self, empresa_a, empresa_b, admin_user):
        sha = "deadbeef" * 8
        NotaFiscalEntrada.objects.create(
            company=empresa_a,
            numero="001",
            serie="1",
            modelo="55",
            data_emissao="2026-05-30",
            valor_total="100.00",
            valor_produtos="100.00",
            sha256=sha,
            criado_por=admin_user,
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                NotaFiscalEntrada.objects.create(
                    company=empresa_a,
                    numero="002",
                    serie="1",
                    modelo="55",
                    data_emissao="2026-05-30",
                    valor_total="100.00",
                    valor_produtos="100.00",
                    sha256=sha,
                    criado_por=admin_user,
                )

    def test_delete_raises(self, empresa_a, admin_user):
        nota = NotaFiscalEntrada.objects.create(
            company=empresa_a,
            numero="001",
            serie="1",
            modelo="55",
            data_emissao="2026-05-30",
            valor_total="0.00",
            valor_produtos="0.00",
            criado_por=admin_user,
        )
        with pytest.raises(RuntimeError):
            nota.delete()

    def test_clean_fornecedor_wrong_company(self, empresa_a, empresa_b, admin_user, fornecedor_a):
        nota = NotaFiscalEntrada(
            company=empresa_b,
            numero="001",
            serie="1",
            modelo="55",
            data_emissao="2026-05-30",
            valor_total="0.00",
            valor_produtos="0.00",
            fornecedor=fornecedor_a,
        )
        with pytest.raises(ValidationError) as exc_info:
            nota.full_clean()
        assert "fornecedor" in exc_info.value.message_dict

    def test_clean_rejeicao_sem_motivo(self, empresa_a, admin_user):
        nota = NotaFiscalEntrada(
            company=empresa_a,
            numero="001",
            serie="1",
            modelo="55",
            data_emissao="2026-05-30",
            valor_total="0.00",
            valor_produtos="0.00",
            status=NotaFiscalEntrada.STATUS_REJEITADA,
            motivo_rejeicao="",
        )
        with pytest.raises(ValidationError) as exc_info:
            nota.full_clean()
        assert "motivo_rejeicao" in exc_info.value.message_dict

    def test_soft_delete(self, empresa_a, admin_user):
        nota = NotaFiscalEntrada.objects.create(
            company=empresa_a,
            numero="001",
            serie="1",
            modelo="55",
            data_emissao="2026-05-30",
            valor_total="0.00",
            valor_produtos="0.00",
            criado_por=admin_user,
        )
        nota.soft_delete()
        nota.refresh_from_db()
        assert nota.is_active is False
        assert nota.deleted_at is not None


@pytest.mark.django_db
class TestItemNotaFiscalEntradaModel:
    def _create_nota(self, empresa, user):
        return NotaFiscalEntrada.objects.create(
            company=empresa,
            numero="001",
            serie="1",
            modelo="55",
            data_emissao="2026-05-30",
            valor_total="500.00",
            valor_produtos="500.00",
            criado_por=user,
        )

    def test_clean_produto_wrong_company(self, empresa_a, empresa_b, admin_user, produto_cimento):
        nota = self._create_nota(empresa_b, admin_user)
        item = ItemNotaFiscalEntrada(
            company=empresa_b,
            nota=nota,
            produto=produto_cimento,
            descricao_original="Cimento",
            unidade="SC",
            quantidade="10",
            valor_unitario="25.00",
            valor_total_item="250.00",
        )
        with pytest.raises(ValidationError) as exc_info:
            item.full_clean()
        assert "produto" in exc_info.value.message_dict

    def test_check_constraint_quantidade_zero(self, empresa_a, admin_user):
        nota = self._create_nota(empresa_a, admin_user)
        with pytest.raises(Exception):
            with transaction.atomic():
                ItemNotaFiscalEntrada.objects.create(
                    company=empresa_a,
                    nota=nota,
                    descricao_original="Produto",
                    unidade="UN",
                    quantidade="0",
                    valor_unitario="10.00",
                    valor_total_item="0.00",
                )


@pytest.mark.django_db
class TestHistoricoNotaFiscalEntradaModel:
    def _create_nota(self, empresa, user):
        return NotaFiscalEntrada.objects.create(
            company=empresa,
            numero="001",
            serie="1",
            modelo="55",
            data_emissao="2026-05-30",
            valor_total="0.00",
            valor_produtos="0.00",
            criado_por=user,
        )

    def test_historico_imutavel_update(self, empresa_a, admin_user):
        nota = self._create_nota(empresa_a, admin_user)
        hist = HistoricoNotaFiscalEntrada.objects.create(
            company=empresa_a,
            nota=nota,
            evento=HistoricoNotaFiscalEntrada.EVENTO_XML_IMPORTADO,
            descricao="Teste",
        )
        with pytest.raises(RuntimeError):
            hist.save()

    def test_historico_imutavel_delete(self, empresa_a, admin_user):
        nota = self._create_nota(empresa_a, admin_user)
        hist = HistoricoNotaFiscalEntrada.objects.create(
            company=empresa_a,
            nota=nota,
            evento=HistoricoNotaFiscalEntrada.EVENTO_XML_IMPORTADO,
            descricao="Teste",
        )
        with pytest.raises(RuntimeError):
            hist.delete()

    def test_historico_imutavel_soft_delete(self, empresa_a, admin_user):
        nota = self._create_nota(empresa_a, admin_user)
        hist = HistoricoNotaFiscalEntrada.objects.create(
            company=empresa_a,
            nota=nota,
            evento=HistoricoNotaFiscalEntrada.EVENTO_XML_IMPORTADO,
            descricao="Teste",
        )
        with pytest.raises(RuntimeError):
            hist.soft_delete()
