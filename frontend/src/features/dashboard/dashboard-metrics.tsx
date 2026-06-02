"use client"

import { StatCard } from "@/components/ui/stat-card"
import { formatCurrency } from "@/lib/utils"
import { toNumber } from "@/lib/format"
import { AlertTriangle, Clock, DollarSign, HandCoins, Package, Users, Wallet } from "lucide-react"
import { ErrorState } from "@/components/ui/error-state"
import { useDashboardResumo } from "./use-dashboard-resumo"

export function DashboardMetrics() {
  const { data, isLoading, isError, refetch } = useDashboardResumo()

  if (isError) {
    return (
      <div className="rounded-xl border border-red-100 bg-white p-5 shadow-sm">
        <ErrorState onRetry={() => refetch()} />
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        {Array.from({ length: 10 }).map((_, index) => (
          <StatCard key={index} label="" value="" loading />
        ))}
      </div>
    )
  }

  const financeiro = data?.financeiro
  const fiado = data?.fiado

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
      <StatCard
        label="Recebido Hoje"
        value={formatCurrency(financeiro?.recebido_hoje)}
        icon={<Wallet className="size-4" />}
      />
      <StatCard
        label="Fiado em Aberto"
        value={formatCurrency(fiado?.total_em_aberto)}
        accent={toNumber(fiado?.total_em_aberto) > 0}
        icon={<HandCoins className="size-4" />}
      />
      <StatCard
        label="Inadimplentes"
        value={String(data?.clientesInadimplentes.count ?? 0)}
        accent={(data?.clientesInadimplentes.count ?? 0) > 0}
        icon={<Users className="size-4" />}
      />
      <StatCard
        label="Contas Vencidas"
        value={formatCurrency(financeiro?.total_contas_pagar_vencidas)}
        accent={toNumber(financeiro?.total_contas_pagar_vencidas) > 0}
        icon={<AlertTriangle className="size-4" />}
      />
      <StatCard
        label="Estoque Crítico"
        value={`${data?.produtosCriticos.count ?? 0} SKUs`}
        accent={toNumber(data?.produtosCriticos.count ?? 0) > 0}
        icon={<Package className="size-4" />}
      />
      <StatCard
        label="Recebido no Mês"
        value={formatCurrency(financeiro?.recebido_mes)}
        icon={<DollarSign className="size-4" />}
      />
    </div>
  )
}
