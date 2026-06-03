"use client"

import { useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { Download, Package, Receipt, ShoppingBag, TrendingUp } from "lucide-react"
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
import { formatNumber, toNumber } from "@/lib/format"
import { formatCurrency, formatDate } from "@/lib/utils"
import { currentMonthStartInputValue, localDateInputValue } from "@/lib/date-range"
import type { PaginationParams } from "@/types"

const PAGE_SIZE = 20

export default function RelatorioVendasPage() {
  const [page, setPage] = useState(1)
  const [downloading, setDownloading] = useState(false)
  const [filters, setFilters] = useState({
    data_inicio: currentMonthStartInputValue(),
    data_fim: localDateInputValue(),
  })

  const params = useMemo<PaginationParams>(() => ({
    page,
    page_size: PAGE_SIZE,
    data_inicio: filters.data_inicio,
    data_fim: filters.data_fim,
  }), [filters, page])

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["relatorios", "vendas", params],
    queryFn: () => relatoriosService.vendas(params),
  })
  const chartData = (data?.vendas_por_dia ?? []).map((item) => ({
    data: item.data,
    total: toNumber(item.total),
    quantidade: item.quantidade,
  }))

  function updateFilter(next: Partial<typeof filters>) {
    setPage(1)
    setFilters((current) => ({ ...current, ...next }))
  }

  async function baixarPdf() {
    setDownloading(true)
    try {
      await relatoriosService.baixarPdfVendas(params)
    } finally {
      setDownloading(false)
    }
  }

  return (
    <Shell>
      <Topbar title="Relatório de Vendas" subtitle="Vendas do PDV, rankings e evolução diária" />
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
              <StatCard label="Vendas Hoje" value={formatCurrency(data?.kpis.vendas_hoje)} icon={<ShoppingBag className="size-4" />} />
              <StatCard label="Vendas Mês" value={formatCurrency(data?.kpis.vendas_mes)} icon={<TrendingUp className="size-4" />} />
              <StatCard label="Ticket Médio" value={formatCurrency(data?.kpis.ticket_medio)} icon={<Receipt className="size-4" />} />
              <StatCard label="Quantidade" value={String(data?.kpis.quantidade_vendas ?? 0)} icon={<Package className="size-4" />} />
            </div>

            <Card>
              <CardHeader>
                <h2 className="text-sm font-semibold text-zinc-900">Vendas por Dia</h2>
              </CardHeader>
              <CardContent>
                {chartData.length === 0 ? (
                  <div className="flex h-64 items-center justify-center text-sm text-zinc-400">Nenhuma venda no período.</div>
                ) : (
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f4f4f5" />
                      <XAxis dataKey="data" tick={{ fontSize: 11, fill: "#71717a" }} axisLine={false} tickLine={false} />
                      <YAxis tick={{ fontSize: 11, fill: "#71717a" }} axisLine={false} tickLine={false} tickFormatter={(value) => `R$${Number(value) / 1000}k`} width={52} />
                      <Tooltip formatter={(value) => formatCurrency(Number(value))} labelFormatter={(label) => String(label)} />
                      <Bar dataKey="total" name="Vendas" fill="#f97316" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>

            <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
              <Card>
                <CardHeader><h2 className="text-sm font-semibold text-zinc-900">Produtos Mais Vendidos</h2></CardHeader>
                <CardContent className="p-0">
                  <Table>
                    <Thead><Tr><Th>Produto</Th><Th className="text-right">Quantidade</Th><Th className="text-right">Valor</Th></Tr></Thead>
                    <Tbody>
                      {(data?.produtos_mais_vendidos ?? []).map((item) => (
                        <Tr key={item.produto_id}>
                          <Td className="font-medium text-zinc-900">{item.produto}</Td>
                          <Td className="text-right">{formatNumber(item.quantidade, 3)}</Td>
                          <Td className="text-right font-semibold">{formatCurrency(item.valor_vendido)}</Td>
                        </Tr>
                      ))}
                      {(data?.produtos_mais_vendidos ?? []).length === 0 && <Tr><Td colSpan={3} className="py-8 text-center text-zinc-400">Sem produtos vendidos.</Td></Tr>}
                    </Tbody>
                  </Table>
                </CardContent>
              </Card>

              <Card>
                <CardHeader><h2 className="text-sm font-semibold text-zinc-900">Categorias Mais Vendidas</h2></CardHeader>
                <CardContent className="p-0">
                  <Table>
                    <Thead><Tr><Th>Categoria</Th><Th className="text-right">Quantidade</Th><Th className="text-right">Valor</Th></Tr></Thead>
                    <Tbody>
                      {(data?.categorias_mais_vendidas ?? []).map((item) => (
                        <Tr key={item.categoria_id ?? "sem-categoria"}>
                          <Td className="font-medium text-zinc-900">{item.categoria ?? "-"}</Td>
                          <Td className="text-right">{formatNumber(item.quantidade, 3)}</Td>
                          <Td className="text-right font-semibold">{formatCurrency(item.valor_vendido)}</Td>
                        </Tr>
                      ))}
                      {(data?.categorias_mais_vendidas ?? []).length === 0 && <Tr><Td colSpan={3} className="py-8 text-center text-zinc-400">Sem categorias vendidas.</Td></Tr>}
                    </Tbody>
                  </Table>
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader><h2 className="text-sm font-semibold text-zinc-900">Vendas</h2></CardHeader>
              <CardContent className="p-0">
                <Table>
                  <Thead><Tr><Th>Número</Th><Th>Cliente</Th><Th>Data</Th><Th>Forma</Th><Th className="text-right">Total</Th></Tr></Thead>
                  <Tbody>
                    {(data?.resultados.results ?? []).map((venda) => (
                      <Tr key={venda.id}>
                        <Td className="font-medium text-zinc-900">{venda.numero || "-"}</Td>
                        <Td>{venda.cliente}</Td>
                        <Td>{formatDate(venda.created_at)}</Td>
                        <Td>{venda.forma_pagamento}</Td>
                        <Td className="text-right font-semibold">{formatCurrency(venda.valor_total)}</Td>
                      </Tr>
                    ))}
                    {(data?.resultados.results ?? []).length === 0 && <Tr><Td colSpan={5} className="py-10 text-center text-zinc-400">Nenhuma venda encontrada.</Td></Tr>}
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
