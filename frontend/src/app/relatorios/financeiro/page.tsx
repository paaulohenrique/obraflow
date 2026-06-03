"use client"

import { useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { AlertTriangle, Download, Landmark, TrendingDown, TrendingUp, Wallet } from "lucide-react"
import { Shell } from "@/components/layout/shell"
import { Topbar } from "@/components/layout/topbar"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { ErrorState } from "@/components/ui/error-state"
import { Input } from "@/components/ui/input"
import { StatCard } from "@/components/ui/stat-card"
import { Table, Tbody, Td, Th, Thead, Tr } from "@/components/ui/table"
import { PaginationControls } from "@/features/relatorios/pagination-controls"
import { relatoriosService } from "@/services/relatorios.service"
import { toNumber } from "@/lib/format"
import { formatCurrency, formatDate } from "@/lib/utils"
import { currentMonthStartInputValue, localDateInputValue } from "@/lib/date-range"
import type { ContaPagar, PaginationParams } from "@/types"

const PAGE_SIZE = 20

export default function RelatorioFinanceiroPage() {
  const [page, setPage] = useState(1)
  const [downloading, setDownloading] = useState(false)
  const [filters, setFilters] = useState({
    data_inicio: currentMonthStartInputValue(),
    data_fim: localDateInputValue(),
    status: "",
  })

  const params = useMemo<PaginationParams>(() => ({
    page,
    page_size: PAGE_SIZE,
    data_inicio: filters.data_inicio,
    data_fim: filters.data_fim,
    status: filters.status || undefined,
  }), [filters, page])

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["relatorios", "financeiro", params],
    queryFn: () => relatoriosService.financeiro(params),
  })
  const chartData = (data?.fluxo ?? []).map((item) => ({
    data: item.data,
    entradas: toNumber(item.entradas),
    saidas: toNumber(item.saidas),
    saldo: toNumber(item.saldo),
  }))

  function updateFilter(next: Partial<typeof filters>) {
    setPage(1)
    setFilters((current) => ({ ...current, ...next }))
  }

  async function baixarPdf() {
    setDownloading(true)
    try {
      await relatoriosService.baixarPdfFinanceiro(params)
    } finally {
      setDownloading(false)
    }
  }

  return (
    <Shell>
      <Topbar title="Relatório Financeiro" subtitle="Entradas, saídas, saldo e contas" />
      <main className="flex-1 space-y-5 p-6">
        <div className="flex flex-wrap items-end gap-3 rounded-lg border border-zinc-200 bg-white p-4">
          <label className="w-40 text-xs font-medium text-zinc-600">
            Período inicial
            <Input className="mt-1" type="date" value={filters.data_inicio} onChange={(event) => updateFilter({ data_inicio: event.target.value })} />
          </label>
          <label className="w-40 text-xs font-medium text-zinc-600">
            Período final
            <Input className="mt-1" type="date" value={filters.data_fim} onChange={(event) => updateFilter({ data_fim: event.target.value })} />
          </label>
          <label className="w-40 text-xs font-medium text-zinc-600">
            Status
            <select
              className="mt-1 h-9 w-full rounded-md border border-zinc-300 bg-white px-3 text-sm text-zinc-900 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/30"
              value={filters.status}
              onChange={(event) => updateFilter({ status: event.target.value as ContaPagar["status"] | "" })}
            >
              <option value="">Todos</option>
              <option value="ABERTA">Aberta</option>
              <option value="PAGA">Paga</option>
              <option value="CANCELADA">Cancelada</option>
            </select>
          </label>
          <Button type="button" variant="outline" icon={<Download className="size-4" />} loading={downloading} onClick={baixarPdf}>
            PDF
          </Button>
        </div>

        {isError ? (
          <Card><CardContent className="py-8"><ErrorState onRetry={() => refetch()} /></CardContent></Card>
        ) : isLoading ? (
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, index) => <StatCard key={index} label="" value="" loading />)}
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <StatCard label="Entradas" value={formatCurrency(data?.kpis.entradas)} icon={<TrendingUp className="size-4" />} />
              <StatCard label="Saídas" value={formatCurrency(data?.kpis.saidas)} accent={toNumber(data?.kpis.saidas) > 0} icon={<TrendingDown className="size-4" />} />
              <StatCard label="Saldo" value={formatCurrency(data?.kpis.saldo)} accent={toNumber(data?.kpis.saldo) > 0} icon={<Wallet className="size-4" />} />
              <StatCard label="Lucro Bruto Estimado" value={formatCurrency(data?.kpis.lucro_bruto_estimado)} icon={<Landmark className="size-4" />} />
            </div>

            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              <Card><CardContent className="p-4"><p className="text-xs font-medium uppercase text-zinc-500">A vencer</p><p className="mt-1 text-xl font-semibold text-zinc-900">{formatCurrency(data?.contas.a_vencer.total)}</p><p className="text-xs text-zinc-500">{data?.contas.a_vencer.quantidade ?? 0} contas</p></CardContent></Card>
              <Card><CardContent className="p-4"><p className="text-xs font-medium uppercase text-zinc-500">Vencidas</p><p className="mt-1 text-xl font-semibold text-red-600">{formatCurrency(data?.contas.vencidas.total)}</p><p className="text-xs text-zinc-500">{data?.contas.vencidas.quantidade ?? 0} contas</p></CardContent></Card>
              <Card><CardContent className="p-4"><p className="text-xs font-medium uppercase text-zinc-500">Pagas</p><p className="mt-1 text-xl font-semibold text-zinc-900">{formatCurrency(data?.contas.pagas.total)}</p><p className="text-xs text-zinc-500">{data?.contas.pagas.quantidade ?? 0} contas</p></CardContent></Card>
            </div>

            <Card>
              <CardHeader><h2 className="text-sm font-semibold text-zinc-900">Fluxo por Dia</h2></CardHeader>
              <CardContent>
                {chartData.length === 0 ? (
                  <div className="flex h-64 items-center justify-center text-sm text-zinc-400">Nenhum lançamento no período.</div>
                ) : (
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f4f4f5" />
                      <XAxis dataKey="data" tick={{ fontSize: 11, fill: "#71717a" }} axisLine={false} tickLine={false} />
                      <YAxis tick={{ fontSize: 11, fill: "#71717a" }} axisLine={false} tickLine={false} tickFormatter={(value) => `R$${Number(value) / 1000}k`} width={52} />
                      <Tooltip formatter={(value) => formatCurrency(Number(value))} />
                      <Legend wrapperStyle={{ fontSize: 11 }} />
                      <Bar dataKey="entradas" name="Entradas" fill="#16a34a" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="saidas" name="Saídas" fill="#dc2626" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <AlertTriangle className="size-4 text-zinc-400" />
                  <h2 className="text-sm font-semibold text-zinc-900">Contas</h2>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                <Table>
                  <Thead><Tr><Th>Descrição</Th><Th>Fornecedor</Th><Th>Status</Th><Th>Vencimento</Th><Th className="text-right">Restante</Th></Tr></Thead>
                  <Tbody>
                    {(data?.resultados.results ?? []).map((conta) => (
                      <Tr key={conta.id}>
                        <Td className="font-medium text-zinc-900">{conta.descricao}</Td>
                        <Td>{conta.fornecedor || "-"}</Td>
                        <Td>{conta.status}</Td>
                        <Td>{formatDate(conta.data_vencimento)}</Td>
                        <Td className="text-right font-semibold">{formatCurrency(conta.valor_restante)}</Td>
                      </Tr>
                    ))}
                    {(data?.resultados.results ?? []).length === 0 && <Tr><Td colSpan={5} className="py-10 text-center text-zinc-400">Nenhuma conta encontrada.</Td></Tr>}
                  </Tbody>
                </Table>
                {data?.resultados && (
                  <PaginationControls currentPage={data.resultados.current_page} totalPages={data.resultados.total_pages} totalCount={data.resultados.count} onPageChange={setPage} />
                )}
              </CardContent>
            </Card>
          </>
        )}
      </main>
    </Shell>
  )
}
