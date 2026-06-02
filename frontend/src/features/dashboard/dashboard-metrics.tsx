"use client"

import { StatCard } from "@/components/ui/stat-card"
import { formatCurrency } from "@/lib/utils"
import { toNumber } from "@/lib/format"
import { AlertTriangle, Clock, DollarSign, HandCoins, Package, Users, Wallet } from "lucide-react"
import { useDashboardResumo } from "./use-dashboard-resumo"

export function DashboardMetrics() {
  const { data, isLoading } = useDashboardResumo()

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
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
      <StatCard
        label="Recebimentos do Mês"
        value={formatCurrency(financeiro?.recebido_mes)}
        accent
        icon={<DollarSign className="size-4" />}
      />
      <StatCard
        label="Recebido Hoje"
        value={formatCurrency(financeiro?.recebido_hoje)}
        icon={<Wallet className="size-4" />}
      />
      <StatCard
        label="Saldo em Caixa"
        value={formatCurrency(financeiro?.saldo_caixa)}
        icon={<Wallet className="size-4" />}
      />
      <StatCard
        label="Valor em Fiado"
        value={formatCurrency(fiado?.total_em_aberto)}
        icon={<HandCoins className="size-4" />}
      />
      <StatCard
        label="Fiado Vencido"
        value={formatCurrency(fiado?.total_atrasado)}
        accent={toNumber(fiado?.total_atrasado) > 0}
        icon={<Clock className="size-4" />}
      />
      <StatCard
        label="Contas Vencidas"
        value={formatCurrency(financeiro?.total_contas_pagar_vencidas)}
        accent={toNumber(financeiro?.total_contas_pagar_vencidas) > 0}
        icon={<AlertTriangle className="size-4" />}
      />
      <StatCard
        label="Clientes Inadimplentes"
        value={String(data?.clientesInadimplentes.count ?? 0)}
        accent={(data?.clientesInadimplentes.count ?? 0) > 0}
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
      <StatCard
        label="Clientes Ativos"
        value={String(data?.clientes.count ?? 0)}
        icon={<Users className="size-4" />}
      />
    </div>
  )
}
