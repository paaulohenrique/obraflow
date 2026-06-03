"use client"

import { useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { AlertTriangle, Boxes, Package, RotateCw, Search } from "lucide-react"
import { Shell } from "@/components/layout/shell"
import { Topbar } from "@/components/layout/topbar"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { ErrorState } from "@/components/ui/error-state"
import { Input } from "@/components/ui/input"
import { StatCard } from "@/components/ui/stat-card"
import { Table, Tbody, Td, Th, Thead, Tr } from "@/components/ui/table"
import { PaginationControls } from "@/features/relatorios/pagination-controls"
import { relatoriosService } from "@/services/relatorios.service"
import { formatNumber } from "@/lib/format"
import { formatCurrency } from "@/lib/utils"
import { currentMonthStartInputValue, localDateInputValue } from "@/lib/date-range"
import type { PaginationParams } from "@/types"

const PAGE_SIZE = 20

export default function RelatorioEstoquePage() {
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState({
    data_inicio: currentMonthStartInputValue(),
    data_fim: localDateInputValue(),
    search: "",
  })

  const params = useMemo<PaginationParams>(() => ({
    page,
    page_size: PAGE_SIZE,
    data_inicio: filters.data_inicio,
    data_fim: filters.data_fim,
    search: filters.search || undefined,
  }), [filters, page])

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["relatorios", "estoque", params],
    queryFn: () => relatoriosService.estoque(params),
  })

  function updateFilter(next: Partial<typeof filters>) {
    setPage(1)
    setFilters((current) => ({ ...current, ...next }))
  }

  return (
    <Shell>
      <Topbar title="Relatório de Estoque" subtitle="Valor estimado, produtos críticos, giro e itens parados" />
      <main className="flex-1 space-y-5 p-4 md:p-6">
        <div className="flex flex-wrap items-end gap-3 rounded-lg border border-zinc-200 bg-white p-4">
          <label className="w-40 text-xs font-medium text-zinc-600">
            Período inicial
            <Input className="mt-1" type="date" value={filters.data_inicio} onChange={(event) => updateFilter({ data_inicio: event.target.value })} />
          </label>
          <label className="w-40 text-xs font-medium text-zinc-600">
            Período final
            <Input className="mt-1" type="date" value={filters.data_fim} onChange={(event) => updateFilter({ data_fim: event.target.value })} />
          </label>
          <label className="min-w-60 flex-1 text-xs font-medium text-zinc-600">
            Produto
            <div className="relative mt-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-zinc-400" />
              <Input
                className="pl-9"
                value={filters.search}
                placeholder="Buscar por nome, SKU ou código"
                onChange={(event) => updateFilter({ search: event.target.value })}
              />
            </div>
          </label>
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
              <StatCard label="Valor do Estoque" value={formatCurrency(data?.kpis.valor_estimado_estoque)} icon={<Boxes className="size-4" />} />
              <StatCard label="Produtos Críticos" value={String(data?.kpis.produtos_criticos ?? 0)} accent={(data?.kpis.produtos_criticos ?? 0) > 0} icon={<AlertTriangle className="size-4" />} />
              <StatCard label="Sem Movimentação" value={String(data?.kpis.produtos_sem_movimentacao ?? 0)} accent={(data?.kpis.produtos_sem_movimentacao ?? 0) > 0} icon={<Package className="size-4" />} />
              <StatCard label="Com Maior Giro" value={String(data?.kpis.produtos_com_maior_giro ?? 0)} icon={<RotateCw className="size-4" />} />
            </div>

            <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
              <Card>
                <CardHeader><h2 className="text-sm font-semibold text-zinc-900">Top Produtos Vendidos</h2></CardHeader>
                <CardContent className="p-0">
                  <Table>
                    <Thead><Tr><Th>Produto</Th><Th className="text-right">Quantidade</Th><Th className="text-right">Valor vendido</Th></Tr></Thead>
                    <Tbody>
                      {(data?.top_produtos_vendidos ?? []).map((item) => (
                        <Tr key={item.produto_id}>
                          <Td className="font-medium text-zinc-900">{item.produto}</Td>
                          <Td className="text-right">{formatNumber(item.quantidade, 3)}</Td>
                          <Td className="text-right font-semibold">{formatCurrency(item.valor_vendido)}</Td>
                        </Tr>
                      ))}
                      {(data?.top_produtos_vendidos ?? []).length === 0 && <Tr><Td colSpan={3} className="py-8 text-center text-zinc-400">Sem vendas no período.</Td></Tr>}
                    </Tbody>
                  </Table>
                </CardContent>
              </Card>

              <Card>
                <CardHeader><h2 className="text-sm font-semibold text-zinc-900">Top Produtos Parados</h2></CardHeader>
                <CardContent className="p-0">
                  <Table>
                    <Thead><Tr><Th>Produto</Th><Th className="text-right">Estoque</Th><Th className="text-right">Valor</Th></Tr></Thead>
                    <Tbody>
                      {(data?.top_produtos_parados ?? []).map((item) => (
                        <Tr key={item.produto_id}>
                          <Td className="font-medium text-zinc-900">{item.produto}</Td>
                          <Td className="text-right">{formatNumber(item.estoque_atual, 3)}</Td>
                          <Td className="text-right font-semibold">{formatCurrency(item.valor_estoque)}</Td>
                        </Tr>
                      ))}
                      {(data?.top_produtos_parados ?? []).length === 0 && <Tr><Td colSpan={3} className="py-8 text-center text-zinc-400">Sem produtos parados no período.</Td></Tr>}
                    </Tbody>
                  </Table>
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader><h2 className="text-sm font-semibold text-zinc-900">Produtos</h2></CardHeader>
              <CardContent className="p-0">
                <Table>
                  <Thead><Tr><Th>Produto</Th><Th>Categoria</Th><Th className="text-right">Atual</Th><Th className="text-right">Mínimo</Th><Th className="text-right">Valor</Th></Tr></Thead>
                  <Tbody>
                    {(data?.resultados.results ?? []).map((produto) => (
                      <Tr key={produto.id}>
                        <Td className="font-medium text-zinc-900">{produto.nome}</Td>
                        <Td>{produto.categoria}</Td>
                        <Td className="text-right">{formatNumber(produto.estoque_atual, 3)}</Td>
                        <Td className="text-right">{formatNumber(produto.estoque_minimo, 3)}</Td>
                        <Td className="text-right font-semibold">{formatCurrency(produto.valor_estoque)}</Td>
                      </Tr>
                    ))}
                    {(data?.resultados.results ?? []).length === 0 && <Tr><Td colSpan={5} className="py-10 text-center text-zinc-400">Nenhum produto encontrado.</Td></Tr>}
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
