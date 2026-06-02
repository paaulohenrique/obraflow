from __future__ import annotations

from decimal import Decimal
from html import escape

from django.utils import timezone
from django.utils.text import slugify
from weasyprint import HTML

from ..models import ContaFiado, ItemFiado, PagamentoFiado


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


def _status_label(status: str) -> str:
    return {
        ContaFiado.STATUS_ABERTA: "Aberta",
        ContaFiado.STATUS_FECHADA: "Fechada",
        ContaFiado.STATUS_CANCELADA: "Cancelada",
    }.get(status, status)


def _payment_label(value: str) -> str:
    return value.replace("_", " ").title()


def fiado_pdf_filename(conta: ContaFiado) -> str:
    cliente = slugify(conta.cliente.nome) or "cliente"
    data = timezone.localtime(conta.data_abertura).strftime("%Y%m%d")
    return f"fiado-{cliente}-{data}-{str(conta.pk)[:8]}.pdf"


def _item_rows(itens) -> str:
    rows = []
    for item in itens:
        forma = item.forma_venda.nome if item.forma_venda_id and item.forma_venda else "Unidade base"
        quantidade = item.quantidade_informada if item.quantidade_informada is not None else item.quantidade
        status = "" if item.status == ItemFiado.STATUS_ATIVO else f" ({escape(item.status.title())})"
        rows.append(
            "<tr>"
            f"<td><strong>{escape(item.produto.nome)}</strong><br><span>{escape(item.produto.sku or '-')}</span></td>"
            f"<td>{escape(str(forma))}{status}</td>"
            f"<td class='num'>{_decimal(quantidade)}</td>"
            f"<td class='num'>{_money(item.preco_unitario)}</td>"
            f"<td class='num strong'>{_money(item.subtotal)}</td>"
            "</tr>"
        )
    if rows:
        return "".join(rows)
    return "<tr><td colspan='5' class='empty'>Nenhum item registrado.</td></tr>"


def _payment_rows(pagamentos) -> str:
    rows = []
    for pagamento in pagamentos:
        status = "" if pagamento.status == PagamentoFiado.STATUS_CONFIRMADO else f" ({escape(pagamento.status.title())})"
        rows.append(
            "<tr>"
            f"<td>{_date(pagamento.data_pagamento)}</td>"
            f"<td>{escape(_payment_label(pagamento.forma_pagamento))}{status}</td>"
            f"<td>{escape(pagamento.observacao or '-')}</td>"
            f"<td class='num strong'>{_money(pagamento.valor)}</td>"
            "</tr>"
        )
    if rows:
        return "".join(rows)
    return "<tr><td colspan='4' class='empty'>Nenhum pagamento registrado.</td></tr>"


def render_conta_fiado_pdf(*, conta: ContaFiado, itens, pagamentos) -> bytes:
    empresa_nome = conta.company.nome_fantasia or conta.company.razao_social or "MP Construções"
    cliente = conta.cliente
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
          .logo {{ align-items: center; background: #f97316; border-radius: 6px; color: white; display: flex; font-weight: 800; height: 38px; justify-content: center; width: 38px; }}
          h1 {{ font-size: 18px; margin: 0; }}
          h2 {{ font-size: 13px; margin: 22px 0 8px; text-transform: uppercase; letter-spacing: .04em; }}
          .muted {{ color: #71717a; }}
          .badge {{ border: 1px solid #d4d4d8; border-radius: 999px; display: inline-block; font-size: 11px; font-weight: 700; padding: 4px 9px; text-transform: uppercase; }}
          .badge.closed {{ background: #ecfdf5; border-color: #bbf7d0; color: #15803d; }}
          .badge.open {{ background: #fff7ed; border-color: #fed7aa; color: #c2410c; }}
          .grid {{ display: grid; gap: 8px; grid-template-columns: repeat(3, 1fr); margin-top: 16px; }}
          .box {{ border: 1px solid #e4e4e7; border-radius: 8px; padding: 10px; }}
          .label {{ color: #71717a; display: block; font-size: 10px; font-weight: 700; text-transform: uppercase; }}
          .value {{ display: block; font-size: 14px; font-weight: 800; margin-top: 3px; }}
          table {{ border-collapse: collapse; margin-top: 6px; width: 100%; }}
          th {{ background: #f4f4f5; color: #52525b; font-size: 10px; padding: 8px; text-align: left; text-transform: uppercase; }}
          td {{ border-bottom: 1px solid #e4e4e7; padding: 9px 8px; vertical-align: top; }}
          td span {{ color: #71717a; font-size: 10px; }}
          .num {{ text-align: right; white-space: nowrap; }}
          .strong {{ font-weight: 800; }}
          .empty {{ color: #71717a; padding: 18px; text-align: center; }}
          .summary {{ margin-left: auto; margin-top: 16px; width: 280px; }}
          .summary div {{ display: flex; justify-content: space-between; padding: 6px 0; }}
          .summary .total {{ border-top: 2px solid #18181b; font-size: 14px; font-weight: 800; margin-top: 6px; padding-top: 10px; }}
          .note {{ background: #fafafa; border: 1px solid #e4e4e7; border-radius: 8px; margin-top: 14px; padding: 10px; }}
          .footer {{ border-top: 1px solid #e4e4e7; color: #71717a; font-size: 10px; margin-top: 28px; padding-top: 10px; }}
        </style>
      </head>
      <body>
        <div class="header">
          <div class="brand">
            <div class="logo">MP</div>
            <div>
              <h1>{escape(empresa_nome)}</h1>
              <div class="muted">Conta fiado #{str(conta.pk)[:8]}</div>
            </div>
          </div>
          <div>
            <span class="badge {'closed' if conta.status == ContaFiado.STATUS_FECHADA else 'open'}">{escape(_status_label(conta.status))}</span>
          </div>
        </div>

        <div class="grid">
          <div class="box"><span class="label">Cliente</span><span class="value">{escape(cliente.nome)}</span><span class="muted">{escape(cliente.cpf_cnpj)}</span></div>
          <div class="box"><span class="label">Abertura</span><span class="value">{_date(conta.data_abertura)}</span></div>
          <div class="box"><span class="label">Fechamento</span><span class="value">{_date(conta.data_fechamento)}</span></div>
        </div>

        <h2>Itens</h2>
        <table>
          <thead>
            <tr><th>Produto</th><th>Forma</th><th class="num">Qtd.</th><th class="num">Preço unit.</th><th class="num">Total</th></tr>
          </thead>
          <tbody>{_item_rows(itens)}</tbody>
        </table>

        <h2>Pagamentos</h2>
        <table>
          <thead>
            <tr><th>Data</th><th>Forma</th><th>Observação</th><th class="num">Valor</th></tr>
          </thead>
          <tbody>{_payment_rows(pagamentos)}</tbody>
        </table>

        <div class="summary">
          <div><span>Total</span><strong>{_money(conta.valor_total)}</strong></div>
          <div><span>Pago</span><strong>{_money(conta.valor_pago)}</strong></div>
          <div class="total"><span>Restante</span><strong>{_money(conta.valor_restante)}</strong></div>
        </div>

        <div class="note">
          <strong>Observações</strong><br>
          {escape(conta.observacao or "Sem observações.")}
        </div>

        <div class="footer">
          Documento gerado em {_date(timezone.now())}. Conta fechada permanece registrada para consulta, impressão e histórico.
        </div>
      </body>
    </html>
    """
    return HTML(string=html).write_pdf()
