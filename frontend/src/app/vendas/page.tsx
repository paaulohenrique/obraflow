"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Ban, ShoppingBag, X } from "lucide-react"
import * as Dialog from "@radix-ui/react-dialog"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { EmptyState } from "@/components/ui/empty-state"
import { SkeletonTable } from "@/components/ui/skeleton"
import { StatCard } from "@/components/ui/stat-card"
import { Table, Tbody, Td, Th, Thead, Tr } from "@/components/ui/table"
import { Shell } from "@/components/layout/shell"
import { Topbar } from "@/components/layout/topbar"
import { useApiToast } from "@/hooks/use-api-toast"
import { useCurrentUser } from "@/hooks/use-current-user"
import { formatCurrency, formatDatetime } from "@/lib/utils"
import { vendasService } from "@/services/vendas.service"
import type { Venda } from "@/types"

const FORMA_LABEL: Record<string, string> = {
  DINHEIRO: "Dinheiro",
  PIX: "PIX",
  CARTAO: "Cartão",
  TRANSFERENCIA: "Transf.",
}

type FilterStatus = "todas" | "CONCLUIDA" | "CANCELADA"

interface CancelarDialogState {
  venda: Venda
  motivo: string
}

export default function VendasPage() {
  const { user } = useCurrentUser()
  const queryClient = useQueryClient()
  const toast = useApiToast()
  const canCancel = user?.role === "admin" || user?.role === "manager"

  const [filter, setFilter] = useState<FilterStatus>("todas")
  const [page, setPage] = useState(1)
  const [cancelar, setCancelar] = useState<CancelarDialogState | null>(null)

  const params = {
    page,
    page_size: 20,
    ordering: "-created_at",
    ...(filter !== "todas" ? { status: filter } : {}),
  }

  const vendasQuery = useQuery({
    queryKey: ["vendas", "list", params],
    queryFn: () => vendasService.list(params),
    staleTime: 30_000,
  })

  const dashQuery = useQuery({
    queryKey: ["vendas", "dashboard"],
    queryFn: vendasService.dashboard,
    staleTime: 30_000,
  })

  const cancelarMutation = useMutation({
    mutationFn: ({ id, motivo }: { id: string; motivo: string }) =>
      vendasService.cancelar(id, motivo),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["vendas"] })
      queryClient.invalidateQueries({ queryKey: ["financeiro"] })
      queryClient.invalidateQueries({ queryKey: ["estoque"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
      toast.success("Venda cancelada.")
      setCancelar(null)
    },
    onError: (error) => toast.error(error),
  })

  const vendas = vendasQuery.data?.results ?? []
  const totalPages = vendasQuery.data?.total_pages ?? 1

  return (
    <Shell>
      <Topbar title="Vendas" subtitle="Histórico de vendas no balcão" />

      <main className="flex-1 space-y-5 p-4 md:p-6">
        {/* KPIs */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Vendas hoje" value={`${dashQuery.data?.count_hoje ?? 0}`} />
          <StatCard
            label="Faturado hoje"
            value={formatCurrency(dashQuery.data?.total_hoje)}
            accent={Number(dashQuery.data?.total_hoje) > 0}
          />
          <StatCard label="Vendas no mês" value={`${dashQuery.data?.count_mes ?? 0}`} />
          <StatCard label="Ticket médio" value={formatCurrency(dashQuery.data?.ticket_medio)} />
        </div>

        <Card>
          {/* Filtros */}
          <div className="flex flex-wrap items-center gap-2 border-b border-zinc-100 px-5 py-3.5">
            {([
              ["todas", "Todas"],
              ["CONCLUIDA", "Concluídas"],
              ["CANCELADA", "Canceladas"],
            ] as [FilterStatus, string][]).map(([val, label]) => (
              <button
                key={val}
                type="button"
                onClick={() => { setPage(1); setFilter(val) }}
                className={`h-7 rounded-md border px-3 text-xs font-medium transition-colors ${
                  filter === val
                    ? "border-orange-300 bg-orange-50 text-orange-700"
                    : "border-zinc-200 text-zinc-500 hover:border-zinc-300 hover:text-zinc-800"
                }`}
              >
                {label}
              </button>
            ))}
            <span className="ml-auto text-xs text-zinc-500">
              <span className="font-medium text-zinc-800">{vendasQuery.data?.count ?? 0}</span> vendas
            </span>
          </div>

          <CardContent className="p-0">
            {vendasQuery.isLoading ? (
              <SkeletonTable rows={6} cols={7} />
            ) : vendas.length === 0 ? (
              <EmptyState
                icon={<ShoppingBag className="size-5" />}
                title="Nenhuma venda encontrada"
                description="As vendas concluídas no PDV aparecerão aqui com pagamento, status e total."
              />
            ) : (
              <Table>
                <Thead>
                  <tr>
                    <Th>Número</Th>
                    <Th>Cliente</Th>
                    <Th>Itens</Th>
                    <Th>Pagamento</Th>
                    <Th className="text-right">Total</Th>
                    <Th>Data</Th>
                    <Th>Status</Th>
                    {canCancel && <Th />}
                  </tr>
                </Thead>
                <Tbody>
                  {vendas.map((venda) => (
                    <Tr key={venda.id}>
                      <Td>
                        <span className="font-mono text-xs font-semibold text-zinc-700">
                          {venda.numero}
                        </span>
                      </Td>
                      <Td className="text-sm text-zinc-700">
                        {venda.cliente_nome || <span className="text-zinc-400">Consumidor final</span>}
                      </Td>
                      <Td className="text-xs text-zinc-500">{venda.total_itens}</Td>
                      <Td className="text-xs text-zinc-500">
                        {FORMA_LABEL[venda.forma_pagamento] ?? venda.forma_pagamento}
                      </Td>
                      <Td className="text-right">
                        <span className="tabular-nums text-sm font-semibold text-zinc-800">
                          {formatCurrency(venda.valor_total)}
                        </span>
                      </Td>
                      <Td className="text-xs text-zinc-500 whitespace-nowrap">
                        {formatDatetime(venda.created_at)}
                      </Td>
                      <Td>
                        {venda.status === "CONCLUIDA" ? (
                          <Badge variant="success">Concluída</Badge>
                        ) : (
                          <Badge variant="error">Cancelada</Badge>
                        )}
                      </Td>
                      {canCancel && (
                        <Td>
                          {venda.status === "CONCLUIDA" && (
                            <button
                              type="button"
                              title="Cancelar venda"
                              onClick={() => setCancelar({ venda, motivo: "" })}
                              className="flex size-7 items-center justify-center rounded-md text-zinc-400 transition-colors hover:bg-red-50 hover:text-red-600"
                            >
                              <Ban className="size-3.5" />
                            </button>
                          )}
                        </Td>
                      )}
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            )}
          </CardContent>

          {/* Paginação */}
          <div className="flex items-center justify-between border-t border-zinc-100 bg-zinc-50/50 px-5 py-3">
            <span className="text-xs text-zinc-500">Página {page} de {Math.max(totalPages, 1)}</span>
            <div className="flex gap-1.5">
              <Button
                variant="outline" size="xs"
                disabled={page <= 1 || vendasQuery.isFetching}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >Anterior</Button>
              <Button
                variant="outline" size="xs"
                disabled={page >= totalPages || vendasQuery.isFetching}
                onClick={() => setPage((p) => p + 1)}
              >Próximo</Button>
            </div>
          </div>
        </Card>
      </main>

      {/* Modal cancelar venda */}
      <Dialog.Root open={Boolean(cancelar)} onOpenChange={(open) => !open && setCancelar(null)}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px] data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0" />
          <Dialog.Content
            className="fixed left-1/2 top-1/2 z-50 w-full max-w-sm -translate-x-1/2 -translate-y-1/2 rounded-xl border border-zinc-200 bg-white p-5 shadow-xl focus:outline-none"
            aria-describedby={undefined}
          >
            <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
              <Dialog.Title className="text-sm font-semibold text-zinc-900">Cancelar venda</Dialog.Title>
              <Dialog.Close asChild>
                <button className="text-zinc-400 hover:text-zinc-600"><X className="size-4" /></button>
              </Dialog.Close>
            </div>

            {cancelar && (
              <div className="mt-3 rounded-lg border border-zinc-100 bg-zinc-50 px-3 py-2 text-xs text-zinc-700">
                <span className="font-mono font-semibold">{cancelar.venda.numero}</span>
                {" · "}
                <span className="font-semibold">{formatCurrency(cancelar.venda.valor_total)}</span>
              </div>
            )}

            <p className="mt-3 text-xs text-zinc-500">
              O estoque será devolvido e o lançamento financeiro estornado.
            </p>

            <textarea
              className="mt-3 h-20 w-full resize-none rounded-md border border-zinc-300 px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/30"
              placeholder="Motivo do cancelamento..."
              value={cancelar?.motivo ?? ""}
              onChange={(e) => setCancelar((prev) => prev ? { ...prev, motivo: e.target.value } : null)}
            />

            <div className="mt-4 flex justify-end gap-2">
              <Dialog.Close asChild>
                <Button variant="outline" size="sm">Voltar</Button>
              </Dialog.Close>
              <Button
                variant="danger" size="sm"
                loading={cancelarMutation.isPending}
                disabled={!cancelar?.motivo.trim()}
                onClick={() => {
                  if (!cancelar?.motivo.trim()) return
                  cancelarMutation.mutate({ id: cancelar.venda.id, motivo: cancelar.motivo.trim() })
                }}
              >
                Cancelar Venda
              </Button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </Shell>
  )
}
