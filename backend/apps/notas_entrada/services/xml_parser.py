"""Parser de NF-e (Nota Fiscal Eletrônica modelo 55/65).

Suporta XMLs com e sem declaração de namespace.
Usa defusedxml para prevenir XXE e ataques XML.
"""
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

from defusedxml import ElementTree
from defusedxml.ElementTree import ParseError

from rest_framework.exceptions import ValidationError


# Namespace NF-e padrão (versão 4.00)
_NFE_NS = "http://www.portalfiscal.inf.br/nfe"
_NS = {"nfe": _NFE_NS}


@dataclass
class ItemNFe:
    ordem: int
    codigo_fornecedor: str
    codigo_barras: str
    descricao_original: str
    ncm: str
    cfop: str
    unidade: str
    quantidade: Decimal
    valor_unitario: Decimal
    valor_total_item: Decimal
    valor_ipi_item: Decimal
    valor_icms_item: Decimal


@dataclass
class NFEPayload:
    chave_acesso: str
    numero: str
    serie: str
    modelo: str
    data_emissao: str
    fornecedor_cnpj: str
    fornecedor_nome: str
    destinatario_cnpj: str
    destinatario_nome: str
    valor_total: Decimal
    valor_produtos: Decimal
    valor_frete: Decimal
    valor_desconto: Decimal
    valor_icms: Decimal
    valor_ipi: Decimal
    itens: list[ItemNFe] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


def _dec(text: str | None, default: Decimal = Decimal("0.00")) -> Decimal:
    try:
        return Decimal(str(text or "0").strip())
    except (InvalidOperation, ValueError):
        return default


def _txt(el, tag: str, ns: dict | None = None) -> str:
    """Extrai texto de um subelemento, retorna '' se não encontrado."""
    if el is None:
        return ""
    child = el.find(tag, ns) if ns else el.find(tag)
    if child is None:
        return ""
    return (child.text or "").strip()


def _find(el, tag: str, ns: dict | None = None):
    if el is None:
        return None
    return el.find(tag, ns) if ns else el.find(tag)


def _make_tag(local: str, ns: str | None) -> str:
    if ns:
        return f"{{{ns}}}{local}"
    return local


def _detect_ns(root) -> str | None:
    """Detecta se o XML usa namespace NF-e e retorna o namespace ou None."""
    tag = root.tag
    if tag.startswith(f"{{{_NFE_NS}}}"):
        return _NFE_NS
    return None


def _find_nfe_root(root, ns: str | None):
    """Localiza a raiz <NFe> ou <nfeProc><NFe> independentemente do namespace."""
    tag_nfe = _make_tag("NFe", ns)
    tag_nfeProc = _make_tag("nfeProc", ns)

    if root.tag == tag_nfe:
        return root
    if root.tag == tag_nfeProc:
        child = root.find(tag_nfe)
        return child
    # Fallback: busca direta
    for el in [root] + list(root):
        if el.tag.endswith("}NFe") or el.tag == "NFe":
            return el
    return None


def _parse_emitente(emit, ns: str | None) -> dict:
    d = ns and {"nfe": ns} or {}
    cnpj = _txt(emit, "nfe:CNPJ", d) if ns else _txt(emit, "CNPJ")
    xnome = _txt(emit, "nfe:xNome", d) if ns else _txt(emit, "xNome")
    xfant = _txt(emit, "nfe:xFant", d) if ns else _txt(emit, "xFant")
    return {"cnpj": cnpj, "nome": xnome or xfant}


def _parse_destinatario(dest, ns: str | None) -> dict:
    d = ns and {"nfe": ns} or {}
    cnpj = _txt(dest, "nfe:CNPJ", d) if ns else _txt(dest, "CNPJ")
    cpf = _txt(dest, "nfe:CPF", d) if ns else _txt(dest, "CPF")
    xnome = _txt(dest, "nfe:xNome", d) if ns else _txt(dest, "xNome")
    return {"cnpj": cnpj or cpf, "nome": xnome}


def _parse_ide(ide, ns: str | None) -> dict:
    d = ns and {"nfe": ns} or {}
    if ns:
        return {
            "chave": "",
            "numero": _txt(ide, "nfe:nNF", d),
            "serie": _txt(ide, "nfe:serie", d),
            "modelo": _txt(ide, "nfe:mod", d),
            "data_emissao": _txt(ide, "nfe:dhEmi", d)[:10] if _txt(ide, "nfe:dhEmi", d) else _txt(ide, "nfe:dEmi", d),
        }
    return {
        "chave": "",
        "numero": _txt(ide, "nNF"),
        "serie": _txt(ide, "serie"),
        "modelo": _txt(ide, "mod"),
        "data_emissao": (_txt(ide, "dhEmi") or _txt(ide, "dEmi"))[:10],
    }


def _parse_infNFe_chave(infNFe) -> str:
    return (infNFe.get("Id") or "").replace("NFe", "")


def _parse_total(total, ns: str | None) -> dict:
    d = ns and {"nfe": ns} or {}
    icms_tag = "nfe:ICMSTot" if ns else "ICMSTot"
    icms = _find(total, icms_tag, d) if ns else _find(total, icms_tag)
    if icms is None:
        icms = total
    if ns:
        return {
            "vNF": _dec(_txt(icms, "nfe:vNF", d)),
            "vProd": _dec(_txt(icms, "nfe:vProd", d)),
            "vFrete": _dec(_txt(icms, "nfe:vFrete", d)),
            "vDesc": _dec(_txt(icms, "nfe:vDesc", d)),
            "vICMS": _dec(_txt(icms, "nfe:vICMS", d)),
            "vIPI": _dec(_txt(icms, "nfe:vIPI", d)),
        }
    return {
        "vNF": _dec(_txt(icms, "vNF")),
        "vProd": _dec(_txt(icms, "vProd")),
        "vFrete": _dec(_txt(icms, "vFrete")),
        "vDesc": _dec(_txt(icms, "vDesc")),
        "vICMS": _dec(_txt(icms, "vICMS")),
        "vIPI": _dec(_txt(icms, "vIPI")),
    }


def _parse_icms_valor(imposto, ns: str | None) -> Decimal:
    d = ns and {"nfe": ns} or {}
    icms_root = _find(imposto, "nfe:ICMS", d) if ns else _find(imposto, "ICMS")
    if icms_root is None:
        return Decimal("0.00")
    for child in icms_root:
        val = _txt(child, "nfe:vICMS", d) if ns else _txt(child, "vICMS")
        if val:
            return _dec(val)
    return Decimal("0.00")


def _parse_ipi_valor(imposto, ns: str | None) -> Decimal:
    d = ns and {"nfe": ns} or {}
    ipi_root = _find(imposto, "nfe:IPI", d) if ns else _find(imposto, "IPI")
    if ipi_root is None:
        return Decimal("0.00")
    ipi_trib = _find(ipi_root, "nfe:IPITrib", d) if ns else _find(ipi_root, "IPITrib")
    if ipi_trib is not None:
        val = _txt(ipi_trib, "nfe:vIPI", d) if ns else _txt(ipi_trib, "vIPI")
        return _dec(val)
    return Decimal("0.00")


def _parse_det(det_list, ns: str | None) -> list[ItemNFe]:
    d = ns and {"nfe": ns} or {}
    itens = []
    for i, det in enumerate(det_list, start=1):
        prod = _find(det, "nfe:prod", d) if ns else _find(det, "prod")
        if prod is None:
            continue
        imposto = _find(det, "nfe:imposto", d) if ns else _find(det, "imposto")

        if ns:
            codigo = _txt(prod, "nfe:cProd", d)
            ean = _txt(prod, "nfe:cEAN", d)
            descricao = _txt(prod, "nfe:xProd", d)
            ncm = _txt(prod, "nfe:NCM", d)
            cfop = _txt(prod, "nfe:CFOP", d)
            unidade = _txt(prod, "nfe:uCom", d)
            qtd = _dec(_txt(prod, "nfe:qCom", d))
            vunit = _dec(_txt(prod, "nfe:vUnCom", d))
            vtotal = _dec(_txt(prod, "nfe:vProd", d))
        else:
            codigo = _txt(prod, "cProd")
            ean = _txt(prod, "cEAN")
            descricao = _txt(prod, "xProd")
            ncm = _txt(prod, "NCM")
            cfop = _txt(prod, "CFOP")
            unidade = _txt(prod, "uCom")
            qtd = _dec(_txt(prod, "qCom"))
            vunit = _dec(_txt(prod, "vUnCom"))
            vtotal = _dec(_txt(prod, "vProd"))

        sem_gtin = {"SEM GTIN", "SEM%20GTIN", "0"}
        ean_clean = ean if ean.upper() not in sem_gtin else ""

        itens.append(ItemNFe(
            ordem=i,
            codigo_fornecedor=codigo,
            codigo_barras=ean_clean,
            descricao_original=descricao,
            ncm=ncm,
            cfop=cfop,
            unidade=unidade,
            quantidade=qtd,
            valor_unitario=vunit,
            valor_total_item=vtotal,
            valor_icms_item=_parse_icms_valor(imposto, ns) if imposto is not None else Decimal("0.00"),
            valor_ipi_item=_parse_ipi_valor(imposto, ns) if imposto is not None else Decimal("0.00"),
        ))
    return itens


def parse_nfe_xml(conteudo: bytes) -> NFEPayload:
    """Faz o parse de um XML NF-e e retorna NFEPayload estruturado.

    Lança ValidationError com mensagem descritiva em caso de XML inválido.
    """
    try:
        root = ElementTree.fromstring(conteudo)
    except ParseError as exc:
        raise ValidationError({"arquivo": f"XML malformado: {exc}"})
    except Exception as exc:
        raise ValidationError({"arquivo": f"Erro ao processar XML: {exc}"})

    ns = _detect_ns(root)
    nfe = _find_nfe_root(root, ns)
    if nfe is None:
        raise ValidationError({"arquivo": "XML não contém elemento <NFe> válido."})

    d = {"nfe": ns} if ns else {}
    infNFe_tag = _make_tag("infNFe", ns)
    infNFe = _find(nfe, infNFe_tag)
    if infNFe is None:
        raise ValidationError({"arquivo": "XML não contém <infNFe>."})

    chave = _parse_infNFe_chave(infNFe)

    ide_tag = _make_tag("ide", ns)
    emit_tag = _make_tag("emit", ns)
    dest_tag = _make_tag("dest", ns)
    total_tag = _make_tag("total", ns)
    det_tag = _make_tag("det", ns)

    ide = _find(infNFe, ide_tag)
    emit = _find(infNFe, emit_tag)
    dest = _find(infNFe, dest_tag)
    total = _find(infNFe, total_tag)
    det_list = infNFe.findall(det_tag) if ns else infNFe.findall(det_tag)

    if ide is None:
        raise ValidationError({"arquivo": "XML não contém <ide>."})
    if emit is None:
        raise ValidationError({"arquivo": "XML não contém <emit>."})
    if total is None:
        raise ValidationError({"arquivo": "XML não contém <total>."})

    ide_data = _parse_ide(ide, ns)
    emit_data = _parse_emitente(emit, ns)
    dest_data = _parse_destinatario(dest, ns) if dest is not None else {"cnpj": "", "nome": ""}
    total_data = _parse_total(total, ns)
    itens = _parse_det(det_list, ns)

    if not itens:
        raise ValidationError({"arquivo": "NF-e não contém itens (<det>)."})

    return NFEPayload(
        chave_acesso=chave,
        numero=ide_data["numero"],
        serie=ide_data["serie"],
        modelo=ide_data["modelo"],
        data_emissao=ide_data["data_emissao"],
        fornecedor_cnpj=emit_data["cnpj"],
        fornecedor_nome=emit_data["nome"],
        destinatario_cnpj=dest_data["cnpj"],
        destinatario_nome=dest_data["nome"],
        valor_total=total_data["vNF"],
        valor_produtos=total_data["vProd"],
        valor_frete=total_data["vFrete"],
        valor_desconto=total_data["vDesc"],
        valor_icms=total_data["vICMS"],
        valor_ipi=total_data["vIPI"],
        itens=itens,
        raw={
            "ide": ide_data,
            "emit": emit_data,
            "dest": dest_data,
            "total": {k: str(v) for k, v in total_data.items()},
        },
    )
