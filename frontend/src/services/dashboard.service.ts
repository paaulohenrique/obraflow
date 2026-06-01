import type { DashboardResumo, FluxoCaixaItem } from "@/types"
import { toNumber } from "@/lib/format"
import { clientesService } from "./clientes.service"
import { estoqueService } from "./estoque.service"
import { fiadoService } from "./fiado.service"
import { financeiroService } from "./financeiro.service"

function buildFluxoCaixa(items: DashboardResumo["financeiro"]["fluxo_diario"]): FluxoCaixaItem[] {
  const byDate = new Map<string, FluxoCaixaItem>()

  items.forEach((item) => {
    const current = byDate.get(item.data) ?? {
      data: item.data,
      receitas: 0,
      despesas: 0,
      saldo: 0,
    }

    if (item.tipo === "ENTRADA") {
      current.receitas += toNumber(item.total)
    } else {
      current.despesas += toNumber(item.total)
    }

    current.saldo = current.receitas - current.despesas
    byDate.set(item.data, current)
  })

  return [...byDate.values()].sort((a, b) => a.data.localeCompare(b.data))
}

export const dashboardService = {
  async resumo(): Promise<DashboardResumo> {
    const [financeiro, fiado, clientes, clientesDevedores, produtosCriticos, contasAtrasadas] =
      await Promise.all([
        financeiroService.dashboard(),
        fiadoService.dashboard(),
        clientesService.list({ page_size: 1 }),
        clientesService.list({ saldo_devedor__gt: 0, ordering: "-saldo_devedor", page_size: 5 }),
        estoqueService.lowStock({ page_size: 5 }),
        financeiroService.contasPagar({ situacao: "atrasada", page_size: 5 }),
      ])

    return {
      financeiro,
      fiado,
      clientes,
      clientesDevedores,
      produtosCriticos,
      contasAtrasadas,
      fluxoCaixa: buildFluxoCaixa(financeiro.fluxo_diario),
    }
  },
}
