"use client"

import { useQuery } from "@tanstack/react-query"
import { Plus, Search, RefreshCw } from "lucide-react"
import { useState, useDeferredValue } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Shell } from "@/components/layout/shell"
import { Topbar } from "@/components/layout/topbar"
import { boletosService } from "@/services/boletos.service"
import { BoletosDashboardCards } from "@/features/boletos/boletos-dashboard-cards"
import { BoletosTable } from "@/features/boletos/boletos-table"
import { BoletoUploadModal } from "@/features/boletos/boleto-upload-modal"
import { BoletoReviewDrawer } from "@/features/boletos/boleto-review-drawer"

export default function BoletosPage() {
  const [uploadOpen, setUploadOpen] = useState(false)
  const [selectedBoletoId, setSelectedBoletoId] = useState<string | null>(null)
  
  // Filtros
  const [searchText, setSearchText] = useState("")
  const deferredSearch = useDeferredValue(searchText)
  const [statusFilter, setStatusFilter] = useState("")
  const [page, setPage] = useState(1)

  // Query do Dashboard de boletos
  const dashboardQuery = useQuery({
    queryKey: ["boletos", "dashboard"],
    queryFn: boletosService.getDashboardBoletos,
    staleTime: 30_000,
  })

  // Query da listagem de boletos
  const boletosQuery = useQuery({
    queryKey: ["boletos", "list", deferredSearch, statusFilter, page],
    queryFn: () => boletosService.list({
      page,
      page_size: 25,
      ordering: "-created_at",
      search: deferredSearch || undefined,
      status: statusFilter || undefined
    }),
    staleTime: 30_000,
  })

  const boletosResponse = boletosQuery.data
  const boletos = boletosResponse?.results ?? []

  const handleRefresh = () => {
    dashboardQuery.refetch()
    boletosQuery.refetch()
  }

  const handleSuccessUpload = (newBoletoId: string) => {
    handleRefresh()
    // Opcionalmente podemos abrir o detalhe do boleto recém-criado imediatamente para o fluxo ser super dinâmico
    setSelectedBoletoId(newBoletoId)
  }

  const totalPages = boletosResponse?.total_pages ?? 1

  return (
    <Shell>
      <Topbar
        title="Boletos"
        subtitle="Envie boletos, revise a leitura automática e gere contas a pagar."
        actions={
          <Button
            type="button"
            onClick={() => setUploadOpen(true)}
            className="bg-orange-500 hover:bg-orange-600 text-white font-semibold flex items-center gap-1.5 shadow-sm cursor-pointer"
            icon={<Plus className="size-4" />}
          >
            Adicionar boleto
          </Button>
        }
      />

      <main className="flex-1 space-y-6 p-4 md:p-6">
        {/* KPI Cards Widget */}
        <BoletosDashboardCards
          data={dashboardQuery.data}
          isLoading={dashboardQuery.isLoading}
        />

        {/* Barra de Filtros e Ferramentas */}
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between bg-white p-4 border border-zinc-200 rounded-xl shadow-sm">
          <div className="flex flex-1 flex-col gap-2.5 sm:flex-row sm:items-center">
            {/* Input de Busca */}
            <div className="relative w-full sm:max-w-xs">
              <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-zinc-400" />
              <Input
                type="text"
                placeholder="Buscar por beneficiário, banco, arquivo..."
                value={searchText}
                onChange={(e) => {
                  setSearchText(e.target.value)
                  setPage(1) // Volta para primeira página
                }}
                className="pl-9 text-xs"
              />
            </div>

            {/* Select Filtro de Status */}
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value)
                setPage(1)
              }}
              className="h-8 rounded-md border border-zinc-200 bg-white px-3 text-xs text-zinc-700 font-medium focus:border-orange-500 focus:outline-none"
            >
              <option value="">Todos os status</option>
              <option value="ENVIADO">Enviado</option>
              <option value="PROCESSANDO">Processando</option>
              <option value="AGUARDANDO_REVISAO">Aguardando Revisão</option>
              <option value="CONFIRMADO">Confirmado</option>
              <option value="REJEITADO">Rejeitado</option>
              <option value="ERRO">Erro</option>
            </select>
          </div>

          <div className="flex items-center gap-2 self-end md:self-auto">
            <button
              onClick={handleRefresh}
              className="flex items-center justify-center p-2 text-zinc-500 hover:text-zinc-700 border border-zinc-200 rounded-lg bg-zinc-50 hover:bg-zinc-100 transition-colors cursor-pointer"
              title="Atualizar dados"
            >
              <RefreshCw className="size-4" />
            </button>
          </div>
        </div>

        {/* Tabela de Resultados */}
        {boletosQuery.isLoading ? (
          <div className="bg-white border border-zinc-200 rounded-xl p-6 space-y-4">
            <div className="flex justify-between items-center pb-2">
              <div className="h-4 bg-zinc-100 rounded w-1/4 animate-pulse" />
              <div className="h-4 bg-zinc-100 rounded w-12 animate-pulse" />
            </div>
            {Array.from({ length: 6 }).map((_, index) => (
              <div key={index} className="h-10 bg-zinc-50 rounded-lg w-full animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="space-y-4">
            <BoletosTable
              boletos={boletos}
              onSelect={setSelectedBoletoId}
              onAddClick={() => setUploadOpen(true)}
            />

            {/* Paginação */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between border-t border-zinc-100 pt-4 px-1 text-xs">
                <span className="text-zinc-500">
                  Mostrando página <strong className="text-zinc-700 font-semibold">{page}</strong> de <strong className="text-zinc-700 font-semibold">{totalPages}</strong>
                </span>
                <div className="flex items-center gap-1.5">
                  <Button
                    variant="outline"
                    size="xs"
                    disabled={page === 1}
                    onClick={() => setPage(p => Math.max(p - 1, 1))}
                  >
                    Anterior
                  </Button>
                  <Button
                    variant="outline"
                    size="xs"
                    disabled={page === totalPages}
                    onClick={() => setPage(p => Math.min(p + 1, totalPages))}
                  >
                    Próxima
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Modais e Drawers de Ação */}
      <BoletoUploadModal
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        onSuccess={handleSuccessUpload}
      />

      <BoletoReviewDrawer
        key={selectedBoletoId || "empty"}
        boletoId={selectedBoletoId}
        onClose={() => {
          setSelectedBoletoId(null)
          handleRefresh()
        }}
      />
    </Shell>
  )
}
