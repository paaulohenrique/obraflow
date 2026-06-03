from __future__ import annotations

from decimal import Decimal
from html import escape

from django.utils import timezone
from weasyprint import HTML


def _money(value: Decimal | int | float | None) -> str:
    amount = Decimal(str(value or "0.00"))
    formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def _number(value: Decimal | int | float | None, digits: int = 3) -> str:
    amount = Decimal(str(value or "0"))
    return f"{amount:,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _date(value) -> str:
    if not value:
        return "-"
    if isinstance(value, str):
        return value
    if hasattr(value, "hour"):
        return timezone.localtime(value).strftime("%d/%m/%Y %H:%M")
    return value.strftime("%d/%m/%Y")


def _period_label(data: dict) -> str:
    periodo = data.get("periodo") or {}
    inicio = periodo.get("data_inicio")
    fim = periodo.get("data_fim")
    if inicio and fim:
        return f"{inicio} a {fim}"
    if inicio:
        return f"A partir de {inicio}"
    if fim:
        return f"Até {fim}"
    return "Todos os registros"


def _company_name(company) -> str:
    return company.nome_fantasia or company.razao_social or "MP Construções"


def _company_initials(company) -> str:
    name = _company_name(company)
    initials = "".join(part[0] for part in name.split()[:2]).upper()
    return initials or "MP"


def relatorio_pdf_filename(kind: str) -> str:
    data = timezone.localtime(timezone.now()).strftime("%Y%m%d")
    return f"relatorio-{kind}-{data}.pdf"


def _base_html(*, company, title: str, subtitle: str, body: str) -> bytes:
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
          h2 {{ font-size: 13px; margin: 22px 0 8px; text-transform: uppercase; }}
          .muted {{ color: #71717a; }}
          .grid {{ display: grid; gap: 8px; grid-template-columns: repeat(4, 1fr); margin-top: 16px; }}
          .box {{ border: 1px solid #e4e4e7; border-radius: 8px; padding: 10px; }}
          .label {{ color: #71717a; display: block; font-size: 10px; font-weight: 700; text-transform: uppercase; }}
          .value {{ display: block; font-size: 14px; font-weight: 800; margin-top: 3px; }}
          table {{ border-collapse: collapse; margin-top: 6px; width: 100%; }}
          th {{ background: #f4f4f5; color: #52525b; font-size: 10px; padding: 8px; text-align: left; text-transform: uppercase; }}
          td {{ border-bottom: 1px solid #e4e4e7; padding: 8px; vertical-align: top; }}
          .num {{ text-align: right; white-space: nowrap; }}
          .empty {{ color: #71717a; padding: 16px; text-align: center; }}
          .footer {{ border-top: 1px solid #e4e4e7; color: #71717a; font-size: 10px; margin-top: 28px; padding-top: 10px; }}
        </style>
      </head>
      <body>
        <div class="header">
          <div class="brand">
            <div class="logo">{escape(_company_initials(company))}</div>
            <div>
              <h1>{escape(_company_name(company))}</h1>
              <div class="muted">{escape(title)}</div>
            </div>
          </div>
          <div class="muted">{escape(subtitle)}</div>
        </div>
        {body}
        <div class="footer">Documento gerado em {_date(timezone.now())} · ObraFlow</div>
      </body>
    </html>
    """
    return HTML(string=html).write_pdf()


def _kpi_grid(items: list[tuple[str, str]]) -> str:
    boxes = "".join(
        f"<div class='box'><span class='label'>{escape(label)}</span><span class='value'>{escape(value)}</span></div>"
        for label, value in items
    )
    return f"<div class='grid'>{boxes}</div>"


def _rows(rows: list[str], colspan: int) -> str:
    return "".join(rows) if rows else f"<tr><td colspan='{colspan}' class='empty'>Sem registros.</td></tr>"


def render_relatorio_fiado_pdf(*, company, data: dict) -> bytes:
    kpis = data["kpis"]
    ranking_rows = [
        "<tr>"
        f"<td>{escape(str(item['cliente']))}</td>"
        f"<td class='num'>{_money(item['saldo'])}</td>"
        f"<td class='num'>{item['dias_em_atraso']}</td>"
        "</tr>"
        for item in data["ranking_maiores_devedores"]
    ]
    body = f"""
      {_kpi_grid([
        ("Total em aberto", _money(kpis["total_em_aberto"])),
        ("Total vencido", _money(kpis["total_vencido"])),
        ("Recebido no mês", _money(kpis["recebido_no_mes"])),
        ("Clientes inadimplentes", str(kpis["clientes_inadimplentes"])),
      ])}
      <h2>Maiores devedores</h2>
      <table>
        <thead><tr><th>Cliente</th><th class="num">Saldo</th><th class="num">Dias em atraso</th></tr></thead>
        <tbody>{_rows(ranking_rows, 3)}</tbody>
      </table>
    """
    return _base_html(
        company=company,
        title="Relatório de Fiado",
        subtitle=f"Período: {_period_label(data)}",
        body=body,
    )


def render_relatorio_vendas_pdf(*, company, data: dict) -> bytes:
    kpis = data["kpis"]
    produto_rows = [
        "<tr>"
        f"<td>{escape(str(item['produto']))}</td>"
        f"<td class='num'>{_number(item['quantidade'])}</td>"
        f"<td class='num'>{_money(item['valor_vendido'])}</td>"
        "</tr>"
        for item in data["produtos_mais_vendidos"]
    ]
    categoria_rows = [
        "<tr>"
        f"<td>{escape(str(item['categoria'] or '-'))}</td>"
        f"<td class='num'>{_number(item['quantidade'])}</td>"
        f"<td class='num'>{_money(item['valor_vendido'])}</td>"
        "</tr>"
        for item in data["categorias_mais_vendidas"]
    ]
    body = f"""
      {_kpi_grid([
        ("Vendas hoje", _money(kpis["vendas_hoje"])),
        ("Vendas mês", _money(kpis["vendas_mes"])),
        ("Ticket médio", _money(kpis["ticket_medio"])),
        ("Quantidade de vendas", str(kpis["quantidade_vendas"])),
      ])}
      <h2>Produtos mais vendidos</h2>
      <table>
        <thead><tr><th>Produto</th><th class="num">Quantidade</th><th class="num">Valor vendido</th></tr></thead>
        <tbody>{_rows(produto_rows, 3)}</tbody>
      </table>
      <h2>Categorias mais vendidas</h2>
      <table>
        <thead><tr><th>Categoria</th><th class="num">Quantidade</th><th class="num">Valor vendido</th></tr></thead>
        <tbody>{_rows(categoria_rows, 3)}</tbody>
      </table>
    """
    return _base_html(
        company=company,
        title="Relatório de Vendas",
        subtitle=f"Período: {_period_label(data)}",
        body=body,
    )


def render_relatorio_financeiro_pdf(*, company, data: dict) -> bytes:
    kpis = data["kpis"]
    fluxo_rows = [
        "<tr>"
        f"<td>{escape(str(item['data']))}</td>"
        f"<td class='num'>{_money(item['entradas'])}</td>"
        f"<td class='num'>{_money(item['saidas'])}</td>"
        f"<td class='num'>{_money(item['saldo'])}</td>"
        "</tr>"
        for item in data["fluxo"]
    ]
    contas = data["contas"]
    body = f"""
      {_kpi_grid([
        ("Entradas", _money(kpis["entradas"])),
        ("Saídas", _money(kpis["saidas"])),
        ("Saldo", _money(kpis["saldo"])),
        ("Lucro bruto estimado", _money(kpis["lucro_bruto_estimado"])),
      ])}
      <h2>Contas</h2>
      {_kpi_grid([
        ("A vencer", f"{contas['a_vencer']['quantidade']} · {_money(contas['a_vencer']['total'])}"),
        ("Vencidas", f"{contas['vencidas']['quantidade']} · {_money(contas['vencidas']['total'])}"),
        ("Pagas", f"{contas['pagas']['quantidade']} · {_money(contas['pagas']['total'])}"),
      ])}
      <h2>Fluxo</h2>
      <table>
        <thead><tr><th>Dia</th><th class="num">Entradas</th><th class="num">Saídas</th><th class="num">Saldo</th></tr></thead>
        <tbody>{_rows(fluxo_rows, 4)}</tbody>
      </table>
    """
    return _base_html(
        company=company,
        title="Relatório Financeiro",
        subtitle=f"Período: {_period_label(data)}",
        body=body,
    )
