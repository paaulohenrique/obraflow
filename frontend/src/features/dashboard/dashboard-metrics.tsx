"use client"

import { StatCard } from "@/components/ui/stat-card"
import { formatCurrency } from "@/lib/utils"
import { toNumber } from "@/lib/format"
import { AlertTriangle, Banknote, HandCoins, Package, ReceiptText, ShoppingBag, Users } from "lucide-react"
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
    <div className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-zinc-400">Painel do Dono</p>
          <h2 className="mt-1 text-lg font-semibold text-zinc-950">Indicadores que pedem decisão</h2>
        </div>
        <p className="text-xs text-zinc-500">
          Atualizado com dados operacionais reais
        </p>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard
        label="Faturamento do mês"
        value={formatCurrency(data?.vendas_mes)}
        context="Vendas concluídas no mês corrente."
        icon={<ShoppingBag className="size-4" />}
      />
      <StatCard
        label="Recebimentos"
        value={formatCurrency(data?.a_receber)}
        context="Fiado em aberto e valores ainda a receber."
        accent={toNumber(data?.a_receber) > 0}
        icon={<Banknote className="size-4" />}
      />
      <StatCard
        label="Contas a pagar"
        value={formatCurrency(data?.a_pagar)}
        context="Compromissos financeiros abertos."
        accent={toNumber(data?.a_pagar) > 0}
        icon={<ReceiptText className="size-4" />}
      />
      <StatCard
        label="Fiado em aberto"
        value={formatCurrency(data?.fiado_em_aberto)}
        context="Crédito concedido ainda não quitado."
        accent={toNumber(data?.fiado_em_aberto) > 0}
        icon={<HandCoins className="size-4" />}
      />
      <StatCard
        label="Fiado vencido"
        value={formatCurrency(data?.fiado_vencido)}
        context="Valor atrasado que exige cobrança."
        accent={toNumber(data?.fiado_vencido) > 0}
        icon={<AlertTriangle className="size-4" />}
      />
      <StatCard
        label="Clientes inadimplentes"
        value={String(data?.clientes_inadimplentes ?? 0)}
        context="Clientes com atraso no crédito."
        accent={(data?.clientes_inadimplentes ?? 0) > 0}
        icon={<Users className="size-4" />}
      />
      <StatCard
        label="Estoque crítico"
        value={`${data?.produtos_estoque_critico ?? 0} SKUs`}
        context="Itens abaixo do mínimo definido."
        accent={(data?.produtos_estoque_critico ?? 0) > 0}
        icon={<Package className="size-4" />}
      />
      </div>
    </div>
  )
}
