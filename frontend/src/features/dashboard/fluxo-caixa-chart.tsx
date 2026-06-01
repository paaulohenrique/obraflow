"use client"

import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { formatCurrency } from "@/lib/utils"
import { useDashboardResumo } from "./use-dashboard-resumo"

interface TooltipEntry {
  name?: string
  color?: string
  value?: number
}

function TooltipContent({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: TooltipEntry[]
  label?: string
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-3 text-xs shadow-md">
      <p className="mb-2 font-medium text-zinc-700">{label}</p>
      {payload.map((entry) => (
        <div key={entry.name} className="mb-1 flex items-center gap-2">
          <span className="size-2 rounded-full" style={{ background: entry.color }} />
          <span className="capitalize text-zinc-500">{entry.name}:</span>
          <span className="font-semibold tabular-nums">{formatCurrency(entry.value)}</span>
        </div>
      ))}
    </div>
  )
}

export function FluxoCaixaChart() {
  const { data, isLoading } = useDashboardResumo()
  const chartData = data?.fluxoCaixa ?? []

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-zinc-900">Fluxo de Caixa</h3>
            <p className="mt-0.5 text-xs text-zinc-500">Lançamentos financeiros confirmados</p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-2">
        {isLoading ? (
          <Skeleton className="h-[200px] w-full" />
        ) : chartData.length === 0 ? (
          <div className="flex h-[200px] items-center justify-center text-sm text-zinc-400">
            Nenhum lançamento financeiro no período.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="receitas" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#22c55e" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="despesas" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.12} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f4f4f5" />
              <XAxis dataKey="data" tick={{ fontSize: 11, fill: "#a1a1aa" }} axisLine={false} tickLine={false} />
              <YAxis
                tick={{ fontSize: 11, fill: "#a1a1aa" }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(value) => `R$${(Number(value) / 1000).toFixed(0)}k`}
                width={48}
              />
              <Tooltip content={<TooltipContent />} />
              <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11, color: "#71717a" }} />
              <Area
                type="monotone"
                dataKey="receitas"
                stroke="#16a34a"
                strokeWidth={1.5}
                fill="url(#receitas)"
                name="Receitas"
              />
              <Area
                type="monotone"
                dataKey="despesas"
                stroke="#dc2626"
                strokeWidth={1.5}
                fill="url(#despesas)"
                name="Despesas"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  )
}
