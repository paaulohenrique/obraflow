"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Search } from "lucide-react"
import { Shell } from "@/components/layout/shell"
import { Topbar } from "@/components/layout/topbar"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { ErrorState } from "@/components/ui/error-state"
import { Input } from "@/components/ui/input"
import { StatCard } from "@/components/ui/stat-card"
import { FiadoTable } from "@/features/fiado/fiado-table"
import { useDebouncedValue } from "@/hooks/use-debounced-value"
import { formatCurrency } from "@/lib/utils"
import { fiadoService } from "@/services/fiado.service"

type Filter = "todos" | "abertas" | "atrasadas" | "fechadas"

export default function FiadoPage() {
  const [search, setSearch] = useState("")
  const [page, setPage] = useState(1)
  const [filter, setFilter] = useState<Filter>("todos")
  const debouncedSearch = useDebouncedValue(search.trim(), 300)

  const dashboardQuery = useQuery({
    queryKey: ["fiado", "dashboard"],
    queryFn: fiadoService.dashboard,
  })

  const contasQuery = useQuery({
    queryKey: ["fiado", "contas", { search: debouncedSearch, page, filter }],
    queryFn: () =>
      fiadoService.list({
        page,
        page_size: 20,
        search: debouncedSearch,
        ...(filter === "abertas" ? { status: "ABERTA" } : {}),
        ...(filter === "atrasadas" ? { situacao: "atrasada" } : {}),
        ...(filter === "fechadas" ? { status: "FECHADA" } : {}),
      }),
  })

  const totalPages = contasQuery.data?.total_pages ?? 1
  const currentPage = contasQuery.data?.current_page ?? page
  const contas = contasQuery.data?.results ?? []

  return (
    <Shell>
      <Topbar title="Fiado" subtitle="Contas, pagamentos e histórico de crédito" />

      <main className="flex-1 space-y-5 p-6">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatCard label="Total em Aberto" value={formatCurrency(dashboardQuery.data?.total_em_aberto)} accent />
          <StatCard label="Atrasado" value={formatCurrency(dashboardQuery.data?.total_atrasado)} />
          <StatCard label="Recebido no Mês" value={formatCurrency(dashboardQuery.data?.total_recebido_mes)} />
          <StatCard label="Contas Abertas" value={`${dashboardQuery.data?.contas_abertas ?? 0}`} />
        </div>

        <Card>
          <div className="flex flex-wrap items-center gap-3 border-b border-zinc-100 px-5 py-3.5">
            <div className="relative min-w-64 flex-1 max-w-sm">
              <Search className="absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-zinc-400" />
              <Input
                placeholder="Buscar cliente, CPF/CNPJ..."
                value={search}
                onChange={(event) => {
                  setPage(1)
                  setSearch(event.target.value)
                }}
                className="pl-8"
              />
            </div>

            <div className="flex gap-1">
              {[
                ["todos", "Todos"],
                ["abertas", "Abertas"],
                ["atrasadas", "Atrasadas"],
                ["fechadas", "Fechadas"],
              ].map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => {
                    setPage(1)
                    setFilter(value as Filter)
                  }}
                  className={`h-8 rounded-md border px-3 text-xs font-medium transition-colors ${
                    filter === value
                      ? "border-orange-300 bg-orange-50 text-orange-700"
                      : "border-zinc-200 text-zinc-500 hover:border-zinc-400 hover:text-zinc-800"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            <div className="ml-auto text-xs text-zinc-500">
              <span className="font-medium text-zinc-800">{contasQuery.data?.count ?? 0}</span> contas
            </div>
          </div>

          {contasQuery.isError ? (
            <ErrorState onRetry={() => contasQuery.refetch()} />
          ) : (
            <FiadoTable contas={contas} loading={contasQuery.isLoading} />
          )}

          <div className="flex items-center justify-between border-t border-zinc-100 bg-zinc-50/50 px-5 py-3">
            <span className="text-xs text-zinc-500">
              Página {currentPage} de {Math.max(totalPages, 1)}
            </span>
            <div className="flex items-center gap-1.5">
              <Button
                variant="outline"
                size="xs"
                disabled={currentPage <= 1 || contasQuery.isFetching}
                onClick={() => setPage((value) => Math.max(1, value - 1))}
              >
                Anterior
              </Button>
              <Button
                variant="outline"
                size="xs"
                disabled={currentPage >= totalPages || contasQuery.isFetching}
                onClick={() => setPage((value) => value + 1)}
              >
                Próximo
              </Button>
            </div>
          </div>
        </Card>
      </main>
    </Shell>
  )
}
