from __future__ import annotations

from decimal import Decimal
from html import escape

from django.utils import timezone
from django.utils.text import slugify
from weasyprint import HTML

from ..models import Venda


def _money(value: Decimal | None) -> str:
    amount = value or Decimal("0.00")
    formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def _decimal(value: Decimal | None, digits: int = 3) -> str:
    amount = value or Decimal("0")
    formatted = f"{amount:,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return formatted


def _date(value) -> str:
    if not value:
        return "-"
    if hasattr(value, "hour"):
        value = timezone.localtime(value)
        return value.strftime("%d/%m/%Y %H:%M")
    return value.strftime("%d/%m/%Y")


def _forma_label(forma: str) -> str:
    return {
        "DINHEIRO": "Dinheiro",
        "PIX": "PIX",
        "CARTAO": "Cartão",
        "TRANSFERENCIA": "Transferência",
    }.get(forma, forma)


def venda_pdf_filename(venda: Venda) -> str:
    data = timezone.localtime(venda.created_at).strftime("%Y%m%d")
    return f"venda-{venda.numero}-{data}.pdf"


def _item_rows(itens) -> str:
    rows = []
    for item in itens:
        forma = item.forma_venda.nome if item.forma_venda_id and item.forma_venda else "Unid. base"
        rows.append(
            "<tr>"
            f"<td><strong>{escape(item.produto.nome)}</strong><br><span>{escape(item.produto.sku or '-')}</span></td>"
            f"<td>{escape(str(forma))}</td>"
            f"<td class='num'>{_decimal(item.quantidade_informada)}</td>"
            f"<td class='num'>{_money(item.preco_unitario)}</td>"
            f"<td class='num strong'>{_money(item.subtotal)}</td>"
            "</tr>"
        )
    if rows:
        return "".join(rows)
    return "<tr><td colspan='5' class='empty'>Nenhum item.</td></tr>"


def render_venda_pdf(*, venda: Venda, itens) -> bytes:
    empresa_nome = venda.company.nome_fantasia or venda.company.razao_social or "MP Construções"
    cliente_nome = venda.cliente.nome if venda.cliente_id and venda.cliente else "Consumidor final"

    html = f"""
    <!doctype html>
    <html lang="pt-BR">
      <head>
        <meta charset="utf-8">
        <style>
          @page {{ size: A4; margin: 18mm; }}
          * {{ box-sizing: border-box; }}
          body {{ color: #18181b; font-family: Inter, Arial, sans-serif; font-size: 12px; line-height: 1.45; }}
          .header {{ align-items: flex-start; border-bottom: 2px solid #f97316; display: flex; justify-content: space-between; padding-bottom: 18px; }}
          .brand {{ display: flex; gap: 12px; }}
          .logo {{ align-items: center; background: #f97316; border-radius: 6px; color: white; display: flex; font-weight: 800; height: 38px; justify-content: center; width: 38px; font-size: 14px; }}
          h1 {{ font-size: 18px; margin: 0; }}
          h2 {{ font-size: 13px; margin: 22px 0 8px; text-transform: uppercase; letter-spacing: .04em; }}
          .muted {{ color: #71717a; }}
          .badge {{ background: #ecfdf5; border: 1px solid #bbf7d0; border-radius: 999px; color: #15803d; display: inline-block; font-size: 11px; font-weight: 700; padding: 4px 9px; text-transform: uppercase; }}
          .grid {{ display: grid; gap: 8px; grid-template-columns: repeat(3, 1fr); margin-top: 16px; }}
          .box {{ border: 1px solid #e4e4e7; border-radius: 8px; padding: 10px; }}
          .label {{ color: #71717a; display: block; font-size: 10px; font-weight: 700; text-transform: uppercase; }}
          .value {{ display: block; font-size: 13px; font-weight: 800; margin-top: 3px; }}
          table {{ border-collapse: collapse; margin-top: 6px; width: 100%; }}
          th {{ background: #f4f4f5; color: #52525b; font-size: 10px; padding: 8px; text-align: left; text-transform: uppercase; }}
          td {{ border-bottom: 1px solid #e4e4e7; padding: 9px 8px; vertical-align: top; }}
          td span {{ color: #71717a; font-size: 10px; }}
          .num {{ text-align: right; white-space: nowrap; }}
          .strong {{ font-weight: 800; }}
          .empty {{ color: #71717a; padding: 18px; text-align: center; }}
          .summary {{ margin-left: auto; margin-top: 16px; width: 280px; }}
          .summary div {{ display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #e4e4e7; }}
          .summary .total {{ border-bottom: none; border-top: 2px solid #18181b; font-size: 14px; font-weight: 800; padding-top: 10px; }}
          .footer {{ border-top: 1px solid #e4e4e7; color: #71717a; font-size: 10px; margin-top: 28px; padding-top: 10px; }}
        </style>
      </head>
      <body>
        <div class="header">
          <div class="brand">
            <div class="logo">MP</div>
            <div>
              <h1>{escape(empresa_nome)}</h1>
              <div class="muted">Comprovante de venda #{escape(venda.numero)}</div>
            </div>
          </div>
          <span class="badge">Concluída</span>
        </div>

        <div class="grid">
          <div class="box">
            <span class="label">Cliente</span>
            <span class="value">{escape(cliente_nome)}</span>
          </div>
          <div class="box">
            <span class="label">Data</span>
            <span class="value">{_date(venda.created_at)}</span>
          </div>
          <div class="box">
            <span class="label">Pagamento</span>
            <span class="value">{escape(_forma_label(venda.forma_pagamento))}</span>
          </div>
        </div>

        <h2>Itens</h2>
        <table>
          <thead>
            <tr>
              <th>Produto</th><th>Forma</th>
              <th class="num">Qtd.</th><th class="num">Preço unit.</th><th class="num">Total</th>
            </tr>
          </thead>
          <tbody>{_item_rows(itens)}</tbody>
        </table>

        <div class="summary">
          <div><span>Subtotal</span><strong>{_money(venda.valor_subtotal)}</strong></div>
          {'<div><span>Desconto</span><strong>− ' + _money(venda.desconto) + '</strong></div>' if venda.desconto else ''}
          <div class="total"><span>Total</span><strong>{_money(venda.valor_total)}</strong></div>
        </div>

        {'<div style="background:#fafafa;border:1px solid #e4e4e7;border-radius:8px;margin-top:14px;padding:10px"><strong>Observações</strong><br>' + escape(venda.observacao) + '</div>' if venda.observacao else ''}

        <div class="footer">
          Documento gerado em {_date(timezone.now())} · {escape(venda.numero)} · ObraFlow
        </div>
      </body>
    </html>
    """
    return HTML(string=html).write_pdf()
