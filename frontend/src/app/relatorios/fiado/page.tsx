"use client"

import { useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Download, HandCoins, Search, Users, AlertTriangle, Wallet } from "lucide-react"
import { Shell } from "@/components/layout/shell"
import { Topbar } from "@/components/layout/topbar"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { StatCard } from "@/components/ui/stat-card"
import { Table, Tbody, Td, Th, Thead, Tr } from "@/components/ui/table"
import { ErrorState } from "@/components/ui/error-state"
import { PaginationControls } from "@/features/relatorios/pagination-controls"
import { clientesService } from "@/services/clientes.service"
import { relatoriosService } from "@/services/relatorios.service"
import { formatCurrency, formatDate } from "@/lib/utils"
import { currentMonthStartInputValue, localDateInputValue } from "@/lib/date-range"
import type { PaginationParams, StatusContaFiado } from "@/types"

const PAGE_SIZE = 20

export default function RelatorioFiadoPage() {
  const [page, setPage] = useState(1)
  const [downloading, setDownloading] = useState(false)
  const [filters, setFilters] = useState({
    data_inicio: currentMonthStartInputValue(),
    data_fim: localDateInputValue(),
    cliente: "",
    status: "",
  })

  const params = useMemo<PaginationParams>(() => ({
    page,
    page_size: PAGE_SIZE,
    data_inicio: filters.data_inicio,
    data_fim: filters.data_fim,
    cliente: filters.cliente || undefined,
    status: filters.status || undefined,
  }), [filters, page])

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["relatorios", "fiado", params],
    queryFn: () => relatoriosService.fiado(params),
  })
  const clientes = useQuery({
    queryKey: ["clientes", "relatorio-fiado"],
    queryFn: () => clientesService.list({ page_size: 100, ordering: "nome" }),
  })

  function updateFilter(next: Partial<typeof filters>) {
    setPage(1)
    setFilters((current) => ({ ...current, ...next }))
  }

  async function baixarPdf() {
    setDownloading(true)
    try {
      await relatoriosService.baixarPdfFiado(params)
    } finally {
      setDownloading(false)
    }
  }

  return (
    <Shell>
      <Topbar title="Relatório de Fiado" subtitle="Saldos em aberto, vencidos e maiores devedores" />
      <main className="flex-1 space-y-5 p-4 md:p-6">
        <div className="flex flex-wrap items-end gap-3 rounded-lg border border-zinc-200 bg-white p-4">
          <label className="w-40 text-xs font-medium text-zinc-600">
            Período inicial
            <Input
              className="mt-1"
              type="date"
              value={filters.data_inicio}
              onChange={(event) => updateFilter({ data_inicio: event.target.value })}
            />
          </label>
          <label className="w-40 text-xs font-medium text-zinc-600">
            Período final
            <Input
              className="mt-1"
              type="date"
              value={filters.data_fim}
              onChange={(event) => updateFilter({ data_fim: event.target.value })}
            />
          </label>
          <label className="min-w-56 flex-1 text-xs font-medium text-zinc-600">
            Cliente
            <select
              className="mt-1 h-9 w-full rounded-md border border-zinc-300 bg-white px-3 text-sm text-zinc-900 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/30"
              value={filters.cliente}
              onChange={(event) => updateFilter({ cliente: event.target.value })}
            >
              <option value="">Todos</option>
              {(clientes.data?.results ?? []).map((cliente) => (
                <option key={cliente.id} value={cliente.id}>{cliente.nome}</option>
              ))}
            </select>
          </label>
          <label className="w-40 text-xs font-medium text-zinc-600">
            Status
            <select
              className="mt-1 h-9 w-full rounded-md border border-zinc-300 bg-white px-3 text-sm text-zinc-900 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/30"
              value={filters.status}
              onChange={(event) => updateFilter({ status: event.target.value as StatusContaFiado | "" })}
            >
              <option value="">Todos</option>
              <option value="ABERTA">Aberta</option>
              <option value="FECHADA">Fechada</option>
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
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, index) => <StatCard key={index} label="" value="" loading />)}
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard label="Total em Aberto" value={formatCurrency(data?.kpis.total_em_aberto)} icon={<HandCoins className="size-4" />} />
              <StatCard label="Total Vencido" value={formatCurrency(data?.kpis.total_vencido)} accent icon={<AlertTriangle className="size-4" />} />
              <StatCard label="Recebido no Mês" value={formatCurrency(data?.kpis.recebido_no_mes)} icon={<Wallet className="size-4" />} />
              <StatCard label="Clientes Inadimplentes" value={String(data?.kpis.clientes_inadimplentes ?? 0)} accent={(data?.kpis.clientes_inadimplentes ?? 0) > 0} icon={<Users className="size-4" />} />
            </div>

            <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
              <Card className="xl:col-span-1">
                <CardHeader>
                  <h2 className="text-sm font-semibold text-zinc-900">Maiores Devedores</h2>
                </CardHeader>
                <CardContent className="space-y-3">
                  {(data?.ranking_maiores_devedores ?? []).length === 0 ? (
                    <div className="py-8 text-center text-sm text-zinc-400">Nenhum devedor no período.</div>
                  ) : (
                    data?.ranking_maiores_devedores.map((item, index) => (
                      <div key={item.cliente_id} className="flex items-center justify-between gap-3 rounded-md border border-zinc-100 p-3">
                        <div className="min-w-0">
                          <p className="text-xs font-semibold text-zinc-500">#{index + 1}</p>
                          <p className="truncate text-sm font-semibold text-zinc-900">{item.cliente}</p>
                          <p className="text-xs text-zinc-500">{item.dias_em_atraso} dias em atraso</p>
                        </div>
                        <span className="text-sm font-bold tabular-nums text-zinc-900">{formatCurrency(item.saldo)}</span>
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>

              <Card className="xl:col-span-2">
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <Search className="size-4 text-zinc-400" />
                    <h2 className="text-sm font-semibold text-zinc-900">Contas do Fiado</h2>
                  </div>
                </CardHeader>
                <CardContent className="p-0">
                  <Table>
                    <Thead>
                      <Tr>
                        <Th>Cliente</Th>
                        <Th>Status</Th>
                        <Th className="text-right">Saldo</Th>
                        <Th>Vencimento</Th>
                        <Th className="text-right">Atraso</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {(data?.resultados.results ?? []).map((conta) => (
                        <Tr key={conta.id}>
                          <Td className="font-medium text-zinc-900">{conta.cliente}</Td>
                          <Td>{conta.status}</Td>
                          <Td className="text-right font-semibold tabular-nums">{formatCurrency(conta.valor_restante)}</Td>
                          <Td>{conta.data_vencimento ? formatDate(conta.data_vencimento) : "-"}</Td>
                          <Td className="text-right">{conta.dias_atraso}</Td>
                        </Tr>
                      ))}
                      {(data?.resultados.results ?? []).length === 0 && (
                        <Tr><Td colSpan={5} className="py-10 text-center text-zinc-400">Nenhuma conta encontrada.</Td></Tr>
                      )}
                    </Tbody>
                  </Table>
                  {data?.resultados && (
                    <PaginationControls
                      currentPage={data.resultados.current_page}
                      totalPages={data.resultados.total_pages}
                      totalCount={data.resultados.count}
                      onPageChange={setPage}
                    />
                  )}
                </CardContent>
              </Card>
            </div>
          </>
        )}
      </main>
    </Shell>
  )
}
