"use client"

import { StatCard } from "@/components/ui/stat-card"
import { formatCurrency } from "@/lib/utils"
import { toNumber } from "@/lib/format"
import { AlertTriangle, DollarSign, Package, Users } from "lucide-react"
import { useDashboardResumo } from "./use-dashboard-resumo"

export function DashboardMetrics() {
  const { data, isLoading } = useDashboardResumo()

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {Array.from({ length: 7 }).map((_, index) => (
          <StatCard key={index} label="" value="" loading />
        ))}
      </div>
    )
  }

  const financeiro = data?.financeiro
  const fiado = data?.fiado

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <StatCard
        label="Recebido Hoje"
        value={formatCurrency(financeiro?.recebido_hoje)}
        accent
        icon={<DollarSign className="size-4" />}
      />
      <StatCard
        label="Recebido no Mês"
        value={formatCurrency(financeiro?.recebido_mes)}
        icon={<DollarSign className="size-4" />}
      />
      <StatCard
        label="Recebido no Ano"
        value={formatCurrency(financeiro?.recebido_ano)}
        icon={<DollarSign className="size-4" />}
      />
      <StatCard
        label="Fiado em Aberto"
        value={formatCurrency(fiado?.total_em_aberto)}
        icon={<Users className="size-4" />}
      />
      <StatCard
        label="Contas em Atraso"
        value={formatCurrency(financeiro?.total_contas_pagar_vencidas)}
        icon={<AlertTriangle className="size-4" />}
      />
      <StatCard
        label="Clientes"
        value={String(data?.clientes.count ?? 0)}
        icon={<Users className="size-4" />}
      />
      <StatCard
        label="Clientes Devedores"
        value={String(fiado?.clientes_devedores ?? 0)}
        icon={<Users className="size-4" />}
      />
      <StatCard
        label="Estoque Crítico"
        value={`${data?.produtosCriticos.count ?? 0} produtos`}
        accent={toNumber(data?.produtosCriticos.count ?? 0) > 0}
        icon={<Package className="size-4" />}
      />
    </div>
  )
}
