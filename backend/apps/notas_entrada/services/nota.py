"""Services principais do módulo Nota Fiscal de Entrada."""
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.core.exceptions import require_company
from apps.core.models import AuditLog
from apps.core.services import create_audit_log

from ..models import HistoricoNotaFiscalEntrada, ItemNotaFiscalEntrada, NotaFiscalEntrada
from .matching import match_fornecedor, match_produto_por_item
from .validators import validate_xml_file
from .xml_parser import parse_nfe_xml


# ── Helpers ──────────────────────────────────────────────────────────────────


def _request_id(request) -> str:
    return getattr(request, "request_id", "") or "" if request else ""


def _full_clean_or_400(obj) -> None:
    try:
        obj.full_clean()
    except DjangoValidationError as exc:
        raise ValidationError(getattr(exc, "message_dict", exc.messages))


def nota_snapshot(nota: NotaFiscalEntrada) -> dict[str, Any]:
    return {
        "id": str(nota.pk),
        "company_id": str(nota.company_id),
        "fornecedor_id": str(nota.fornecedor_id) if nota.fornecedor_id else None,
        "fornecedor_nome_xml": nota.fornecedor_nome_xml,
        "fornecedor_cnpj_xml": nota.fornecedor_cnpj_xml,
        "chave_acesso": nota.chave_acesso,
        "numero": nota.numero,
        "serie": nota.serie,
        "modelo": nota.modelo,
        "data_emissao": str(nota.data_emissao),
        "valor_total": str(nota.valor_total),
        "valor_produtos": str(nota.valor_produtos),
        "status": nota.status,
        "criado_por_id": str(nota.criado_por_id) if nota.criado_por_id else None,
        "confirmado_por_id": str(nota.confirmado_por_id) if nota.confirmado_por_id else None,
        "confirmado_em": nota.confirmado_em.isoformat() if nota.confirmado_em else None,
        "rejeitado_por_id": str(nota.rejeitado_por_id) if nota.rejeitado_por_id else None,
        "rejeitado_em": nota.rejeitado_em.isoformat() if nota.rejeitado_em else None,
        "motivo_rejeicao": nota.motivo_rejeicao,
        "conta_pagar_id": str(nota.conta_pagar_id) if nota.conta_pagar_id else None,
    }


def criar_historico(
    *,
    nota: NotaFiscalEntrada,
    evento: str,
    descricao: str,
    user=None,
    before=None,
    after=None,
    metadata=None,
    request=None,
) -> HistoricoNotaFiscalEntrada:
    return HistoricoNotaFiscalEntrada.objects.create(
        company=nota.company,
        nota=nota,
        evento=evento,
        descricao=descricao,
        before=before,
        after=after,
        metadata=metadata or {},
        request_id=_request_id(request),
        created_by=user,
    )


def _check_sha256(*, company_id, sha256: str) -> None:
    if NotaFiscalEntrada.objects.filter(
        company_id=company_id,
        sha256=sha256,
        deleted_at__isnull=True,
    ).exists():
        raise ValidationError({"arquivo": "Este XML já foi importado para esta empresa."})


def _check_chave(*, company_id, chave_acesso: str) -> None:
    if not chave_acesso:
        return
    if NotaFiscalEntrada.objects.filter(
        company_id=company_id,
        chave_acesso=chave_acesso,
        deleted_at__isnull=True,
    ).exists():
        raise ValidationError({"chave_acesso": "Esta chave de acesso já foi importada."})


def _check_idempotency(*, company_id, key: str) -> NotaFiscalEntrada | None:
    if not key:
        return None
    return NotaFiscalEntrada.objects.filter(
        company_id=company_id,
        idempotency_key=key,
        deleted_at__isnull=True,
    ).first()


# ── Service Principal ─────────────────────────────────────────────────────────


@transaction.atomic
def importar_xml_nota(
    *,
    user,
    arquivo,
    observacao: str = "",
    idempotency_key: str = "",
    request=None,
) -> NotaFiscalEntrada:
    """Importa XML de NF-e, cria nota + itens e faz matching automático."""
    require_company(user)
    company = user.company
    company_id = user.company_id

    key = (idempotency_key or "").strip()
    existing = _check_idempotency(company_id=company_id, key=key)
    if existing:
        return existing

    # 1. Validar arquivo
    meta = validate_xml_file(arquivo)
    conteudo = meta["conteudo"]
    sha256 = meta["sha256"]

    _check_sha256(company_id=company_id, sha256=sha256)

    # 2. Parse XML
    payload = parse_nfe_xml(conteudo)

    # 3. Verificar chave duplicada (após parse para extrair a chave)
    _check_chave(company_id=company_id, chave_acesso=payload.chave_acesso)

    # 4. Match fornecedor automático
    fornecedor = match_fornecedor(cnpj_xml=payload.fornecedor_cnpj, company_id=company_id)

    # 5. Criar NotaFiscalEntrada
    nota = NotaFiscalEntrada(
        company=company,
        fornecedor=fornecedor,
        fornecedor_nome_xml=payload.fornecedor_nome,
        fornecedor_cnpj_xml=payload.fornecedor_cnpj,
        sha256=sha256,
        chave_acesso=payload.chave_acesso,
        numero=payload.numero,
        serie=payload.serie,
        modelo=payload.modelo,
        data_emissao=payload.data_emissao or timezone.localdate(),
        valor_total=payload.valor_total,
        valor_produtos=payload.valor_produtos,
        valor_frete=payload.valor_frete,
        valor_desconto=payload.valor_desconto,
        valor_icms=payload.valor_icms,
        valor_ipi=payload.valor_ipi,
        status=NotaFiscalEntrada.STATUS_AGUARDANDO_REVISAO,
        payload_extraido=payload.raw,
        observacao=(observacao or "").strip(),
        idempotency_key=key,
        criado_por=user,
    )
    _full_clean_or_400(nota)
    try:
        nota.save()
    except IntegrityError as exc:
        raise ValidationError({"arquivo": "Nota duplicada para esta empresa."}) from exc

    # Salva o arquivo XML após o save (precisa do pk)
    arquivo.seek(0)
    nota.xml_file.save(f"{nota.pk}.xml", arquivo, save=True)

    # 6. Criar itens com match automático de produto
    itens_bulk = []
    for item_nfe in payload.itens:
        produto = match_produto_por_item(
            codigo_barras=item_nfe.codigo_barras,
            codigo_fornecedor=item_nfe.codigo_fornecedor,
            company_id=company_id,
        )
        custo = item_nfe.valor_unitario if item_nfe.valor_unitario > Decimal("0") else None
        itens_bulk.append(ItemNotaFiscalEntrada(
            company=company,
            nota=nota,
            produto=produto,
            descricao_original=item_nfe.descricao_original,
            codigo_fornecedor=item_nfe.codigo_fornecedor,
            codigo_barras=item_nfe.codigo_barras,
            ncm=item_nfe.ncm,
            cfop=item_nfe.cfop,
            unidade=item_nfe.unidade,
            quantidade=item_nfe.quantidade,
            valor_unitario=item_nfe.valor_unitario,
            valor_total_item=item_nfe.valor_total_item,
            custo_unitario=custo,
            valor_ipi_item=item_nfe.valor_ipi_item,
            valor_icms_item=item_nfe.valor_icms_item,
            ordem=item_nfe.ordem,
        ))
    ItemNotaFiscalEntrada.objects.bulk_create(itens_bulk)

    # 7. Auditoria e histórico
    after = nota_snapshot(nota)
    create_audit_log(
        user=user,
        action=AuditLog.ACTION_CREATE,
        entity=nota,
        after=after,
        request=request,
    )
    criar_historico(
        nota=nota,
        evento=HistoricoNotaFiscalEntrada.EVENTO_XML_IMPORTADO,
        descricao=f"XML NF-e {nota.numero}/{nota.serie} importado.",
        user=user,
        after=after,
        metadata={
            "fornecedor_cnpj": payload.fornecedor_cnpj,
            "fornecedor_vinculado": bool(fornecedor),
            "total_itens": len(payload.itens),
        },
        request=request,
    )

    return nota


# ── Vincular Fornecedor ───────────────────────────────────────────────────────


@transaction.atomic
def vincular_fornecedor(
    *,
    user,
    nota: NotaFiscalEntrada,
    fornecedor,
    request=None,
) -> NotaFiscalEntrada:
    require_company(user)
    # Busca do banco para garantir status atual
    from rest_framework.exceptions import NotFound
    try:
        nota = NotaFiscalEntrada.objects.select_for_update(of=("self",)).get(
            pk=nota.pk, company_id=user.company_id, deleted_at__isnull=True
        )
    except NotaFiscalEntrada.DoesNotExist:
        raise NotFound("Nota não encontrada.")
    if nota.status != NotaFiscalEntrada.STATUS_AGUARDANDO_REVISAO:
        raise ValidationError({"status": "Apenas notas aguardando revisão podem ter fornecedor vinculado."})
    if fornecedor.company_id != user.company_id:
        raise ValidationError({"fornecedor": "Fornecedor não pertence à empresa."})

    before = nota_snapshot(nota)
    nota.fornecedor = fornecedor
    nota._allow_update = True
    try:
        _full_clean_or_400(nota)
        nota.save(update_fields=["fornecedor", "updated_at"])
    finally:
        nota._allow_update = False

    after = nota_snapshot(nota)
    create_audit_log(user=user, action=AuditLog.ACTION_UPDATE, entity=nota, before=before, after=after, request=request)
    criar_historico(
        nota=nota,
        evento=HistoricoNotaFiscalEntrada.EVENTO_FORNECEDOR_VINCULADO,
        descricao=f"Fornecedor {fornecedor} vinculado à nota.",
        user=user,
        before=before,
        after=after,
        metadata={"fornecedor_id": str(fornecedor.pk)},
        request=request,
    )
    return nota


# ── Vincular Produto ao Item ──────────────────────────────────────────────────


_UNSET = object()


@transaction.atomic
def vincular_produto_item(
    *,
    user,
    item: ItemNotaFiscalEntrada,
    produto=None,
    custo_unitario=None,
    ignorado: bool | None = None,
    forma_venda=_UNSET,
    request=None,
) -> ItemNotaFiscalEntrada:
    require_company(user)

    if item.company_id != user.company_id:
        raise ValidationError({"item": "Item não pertence à empresa."})

    nota = NotaFiscalEntrada.objects.select_for_update(of=("self",)).get(
        pk=item.nota_id, company_id=user.company_id, deleted_at__isnull=True
    )
    if nota.status != NotaFiscalEntrada.STATUS_AGUARDANDO_REVISAO:
        raise ValidationError({"status": "Itens só podem ser editados com nota aguardando revisão."})

    if produto is not None and produto.company_id != user.company_id:
        raise ValidationError({"produto": "Produto não pertence à empresa."})

    # Produto que estará no item após a atualização (pode mudar nesta chamada)
    produto_final = produto if (produto is not None or "produto" in (request.data if request else {})) else item.produto

    # Valida forma_venda antes de qualquer alteração no item
    if forma_venda is not _UNSET:
        if forma_venda is not None:
            if forma_venda.company_id != user.company_id:
                raise ValidationError({"forma_venda": "Forma de venda não pertence à empresa."})
            if not forma_venda.ativo:
                raise ValidationError({"forma_venda": "Forma de venda está inativa."})
            if produto_final is None:
                raise ValidationError({
                    "forma_venda": "Defina o produto antes de selecionar a forma de venda."
                })
            if forma_venda.produto_id != produto_final.pk:
                raise ValidationError({
                    "forma_venda": "Forma de venda não pertence ao produto selecionado."
                })

    update_fields = ["updated_at"]

    if produto is not None or "produto" in (request.data if request else {}):
        item.produto = produto
        update_fields.append("produto")
        # Limpa forma_venda automaticamente se produto mudou e forma_venda não foi enviada
        if forma_venda is _UNSET and item.forma_venda_id:
            item.forma_venda = None
            update_fields.append("forma_venda")

    if forma_venda is not _UNSET:
        item.forma_venda = forma_venda
        update_fields.append("forma_venda")

    if custo_unitario is not None:
        item.custo_unitario = custo_unitario
        update_fields.append("custo_unitario")

    if ignorado is not None:
        item.ignorado = ignorado
        update_fields.append("ignorado")

    _full_clean_or_400(item)
    item.save(update_fields=update_fields)

    evento = HistoricoNotaFiscalEntrada.EVENTO_ITEM_IGNORADO if (ignorado is True) else HistoricoNotaFiscalEntrada.EVENTO_ITEM_PRODUTO_VINCULADO
    descricao = (
        f"Item '{item.descricao_original}' marcado como ignorado."
        if ignorado is True
        else f"Produto/forma vinculados ao item '{item.descricao_original}'."
    )
    criar_historico(
        nota=nota,
        evento=evento,
        descricao=descricao,
        user=user,
        metadata={
            "item_id": str(item.pk),
            "produto_id": str(item.produto_id) if item.produto_id else None,
            "forma_venda_id": str(item.forma_venda_id) if item.forma_venda_id else None,
        },
        request=request,
    )
    return item


# ── Rejeitar Nota ─────────────────────────────────────────────────────────────


@transaction.atomic
def rejeitar_nota(
    *,
    user,
    nota: NotaFiscalEntrada,
    motivo: str,
    request=None,
) -> NotaFiscalEntrada:
    require_company(user)
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValidationError({"motivo": "Motivo é obrigatório para rejeição."})

    nota = NotaFiscalEntrada.objects.select_for_update(of=("self",)).get(
        pk=nota.pk, company_id=user.company_id, deleted_at__isnull=True
    )
    if nota.status in {NotaFiscalEntrada.STATUS_CONFIRMADA, NotaFiscalEntrada.STATUS_REJEITADA}:
        raise ValidationError({"status": "Nota não pode ser rejeitada no status atual."})

    before = nota_snapshot(nota)
    nota.status = NotaFiscalEntrada.STATUS_REJEITADA
    nota.rejeitado_por = user
    nota.rejeitado_em = timezone.now()
    nota.motivo_rejeicao = motivo
    nota._allow_update = True
    try:
        _full_clean_or_400(nota)
        nota.save(update_fields=["status", "rejeitado_por", "rejeitado_em", "motivo_rejeicao", "updated_at"])
    finally:
        nota._allow_update = False

    after = nota_snapshot(nota)
    create_audit_log(user=user, action=AuditLog.ACTION_UPDATE, entity=nota, before=before, after=after, request=request)
    criar_historico(
        nota=nota,
        evento=HistoricoNotaFiscalEntrada.EVENTO_REJEITADA,
        descricao=f"Nota rejeitada: {motivo}",
        user=user,
        before=before,
        after=after,
        request=request,
    )
    return nota
