"use client"

import { StatCard } from "@/components/ui/stat-card"
import { formatCurrency } from "@/lib/utils"
import { toNumber } from "@/lib/format"
import { AlertTriangle, Banknote, HandCoins, Package, ReceiptText, ShoppingBag, Users, Wallet } from "lucide-react"
import { ErrorState } from "@/components/ui/error-state"
import { useDashboardExecutivo } from "./use-dashboard-executivo"

export function DashboardMetrics() {
  const { data, isLoading, isError, refetch } = useDashboardExecutivo()

  if (isError) {
    return (
      <div className="rounded-xl border border-red-100 bg-white p-5 shadow-sm">
        <ErrorState onRetry={() => refetch()} />
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {Array.from({ length: 8 }).map((_, index) => (
          <StatCard key={index} label="" value="" loading />
        ))}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <StatCard
        label="Caixa Atual"
        value={formatCurrency(data?.caixa_atual)}
        accent={toNumber(data?.caixa_atual) > 0}
        icon={<Wallet className="size-4" />}
      />
      <StatCard
        label="A Receber"
        value={formatCurrency(data?.a_receber)}
        accent={toNumber(data?.a_receber) > 0}
        icon={<Banknote className="size-4" />}
      />
      <StatCard
        label="A Pagar"
        value={formatCurrency(data?.a_pagar)}
        accent={toNumber(data?.a_pagar) > 0}
        icon={<ReceiptText className="size-4" />}
      />
      <StatCard
        label="Fiado em Aberto"
        value={formatCurrency(data?.fiado_em_aberto)}
        accent={toNumber(data?.fiado_em_aberto) > 0}
        icon={<HandCoins className="size-4" />}
      />
      <StatCard
        label="Fiado Vencido"
        value={formatCurrency(data?.fiado_vencido)}
        accent={toNumber(data?.fiado_vencido) > 0}
        icon={<AlertTriangle className="size-4" />}
      />
      <StatCard
        label="Vendas do Mês"
        value={formatCurrency(data?.vendas_mes)}
        icon={<ShoppingBag className="size-4" />}
      />
      <StatCard
        label="Clientes Inadimplentes"
        value={String(data?.clientes_inadimplentes ?? 0)}
        accent={(data?.clientes_inadimplentes ?? 0) > 0}
        icon={<Users className="size-4" />}
      />
      <StatCard
        label="Estoque Crítico"
        value={`${data?.produtos_estoque_critico ?? 0} SKUs`}
        accent={(data?.produtos_estoque_critico ?? 0) > 0}
        icon={<Package className="size-4" />}
      />
    </div>
  )
}
