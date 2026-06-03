"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import {
  AlertTriangle,
  Ban,
  ChevronLeft,
  ChevronRight,
  Landmark,
  Plus,
  TrendingDown,
  TrendingUp,
  Wallet,
} from "lucide-react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import * as Dialog from "@radix-ui/react-dialog"
import * as Tabs from "@radix-ui/react-tabs"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { EmptyState } from "@/components/ui/empty-state"
import { SkeletonTable } from "@/components/ui/skeleton"
import { StatCard } from "@/components/ui/stat-card"
import { Table, Tbody, Td, Th, Thead, Tr } from "@/components/ui/table"
import { Shell } from "@/components/layout/shell"
import { Topbar } from "@/components/layout/topbar"
import { useApiToast } from "@/hooks/use-api-toast"
import { useCurrentUser } from "@/hooks/use-current-user"
import { formatCurrency, formatDate, formatDatetime } from "@/lib/utils"
import { financeiroService } from "@/services/financeiro.service"
import { LancamentosTable } from "@/features/financeiro/lancamentos-table"
import { NovaContaPagarDialog } from "@/features/financeiro/nova-conta-pagar-dialog"
import { NovaLancamentoDialog } from "@/features/financeiro/nova-lancamento-dialog"
import { PagarContaDialog } from "@/features/financeiro/pagar-conta-dialog"
import type { CancelarContaPagarPayload, ContaPagar, TipoLancamento } from "@/types"

type FilterCP = "todas" | "abertas" | "vencidas" | "pagas" | "canceladas"

function statusBadge(conta: ContaPagar) {
  if (conta.status === "PAGA") return <Badge variant="success">Paga</Badge>
  if (conta.status === "CANCELADA") return <Badge variant="outline">Cancelada</Badge>
  if (conta.is_atrasada) return <Badge variant="error">Vencida {conta.dias_atraso}d</Badge>
  if (conta.is_parcial) return <Badge variant="warning">Parcial</Badge>
  return <Badge variant="default">Aberta</Badge>
}

// ─── Modal de cancelar conta a pagar ─────────────────────────────────────────

interface CancelarContaDialogProps {
  conta: ContaPagar | null
  onClose: () => void
}

function CancelarContaDialog({ conta, onClose }: CancelarContaDialogProps) {
  const queryClient = useQueryClient()
  const toast = useApiToast()
  const [motivo, setMotivo] = useState("")

  const mutation = useMutation({
    mutationFn: (payload: CancelarContaPagarPayload) =>
      financeiroService.cancelarContaPagar(conta!.id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["financeiro"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
      toast.success("Conta cancelada.")
      setMotivo("")
      onClose()
    },
    onError: (error) => toast.error(error),
  })

  return (
    <Dialog.Root open={Boolean(conta)} onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px] data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 z-50 w-full max-w-sm -translate-x-1/2 -translate-y-1/2 rounded-xl border border-zinc-200 bg-white p-5 shadow-xl focus:outline-none"
          aria-describedby={undefined}
        >
          <Dialog.Title className="text-sm font-semibold text-zinc-900">Cancelar conta a pagar</Dialog.Title>
          <p className="mt-1 text-xs text-zinc-500">Informe o motivo do cancelamento.</p>

          {conta && (
            <div className="mt-3 rounded-lg border border-zinc-100 bg-zinc-50 px-3 py-2 text-xs text-zinc-700">
              <span className="font-medium">{conta.descricao}</span>
              {" · "}
              <span className="font-semibold text-red-600">{formatCurrency(conta.valor_restante)}</span>
            </div>
          )}

          <textarea
            className="mt-3 h-20 w-full resize-none rounded-md border border-zinc-300 px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/30"
            placeholder="Ex: duplicidade, lançamento incorreto..."
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
          />

          <div className="mt-4 flex justify-end gap-2">
            <Dialog.Close asChild>
              <Button variant="outline" size="sm" onClick={() => setMotivo("")}>Voltar</Button>
            </Dialog.Close>
            <Button
              variant="danger"
              size="sm"
              loading={mutation.isPending}
              disabled={!motivo.trim()}
              onClick={() => mutation.mutate({ motivo: motivo.trim() })}
            >
              Cancelar Conta
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

// ─── Página principal ─────────────────────────────────────────────────────────

export default function FinanceiroPage() {
  const { user } = useCurrentUser()
  const canOperate = user?.role === "admin" || user?.role === "manager"

  // ─── Filtros e paginação ──────────────────────────────────────────────────
  const [filterCP, setFilterCP] = useState<FilterCP>("abertas")
  const [pageCP, setPageCP] = useState(1)
  const [pageL, setPageL] = useState(1)

  // ─── Estado dos dialogs ───────────────────────────────────────────────────
  const [pagarConta, setPagarConta] = useState<ContaPagar | null>(null)
  const [cancelarConta, setCancelarConta] = useState<ContaPagar | null>(null)
  const [novaContaOpen, setNovaContaOpen] = useState(false)
  const [novaLancamentoTipo, setNovaLancamentoTipo] = useState<TipoLancamento | null>(null)

  // ─── Queries ──────────────────────────────────────────────────────────────
  const dashboardQuery = useQuery({
    queryKey: ["financeiro", "dashboard"],
    queryFn: financeiroService.dashboard,
    staleTime: 30_000,
  })

  const paramCP = {
    page: pageCP,
    page_size: 20,
    ordering: "data_vencimento",
    ...(filterCP === "abertas" ? { status: "ABERTA" } : {}),
    ...(filterCP === "vencidas" ? { vencidas: "true" } : {}),
    ...(filterCP === "pagas" ? { status: "PAGA" } : {}),
    ...(filterCP === "canceladas" ? { status: "CANCELADA" } : {}),
  }

  const contasQuery = useQuery({
    queryKey: ["financeiro", "contas-pagar", paramCP],
    queryFn: () => financeiroService.contasPagar(paramCP),
    staleTime: 30_000,
  })

  const lancamentosQuery = useQuery({
    queryKey: ["financeiro", "lancamentos", { page: pageL }],
    queryFn: () => financeiroService.lancamentos({ page: pageL, page_size: 20, ordering: "-data_lancamento" }),
    staleTime: 30_000,
  })

  const contas = contasQuery.data?.results ?? []
  const totalPagesCP = contasQuery.data?.total_pages ?? 1
  const lancamentos = lancamentosQuery.data?.results ?? []
  const totalPagesL = lancamentosQuery.data?.total_pages ?? 1

  const dash = dashboardQuery.data

  return (
    <Shell>
      <Topbar
        title="Financeiro"
        subtitle="Contas a pagar, recebimentos e fluxo financeiro"
      />

      <main className="flex-1 space-y-5 p-4 md:p-6">
        {/* ─── KPIs ──────────────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <StatCard
            label="Recebido Hoje"
            value={formatCurrency(dash?.recebido_hoje)}
            icon={<Wallet className="size-4" />}
            accent={Number(dash?.recebido_hoje) > 0}
          />
          <StatCard
            label="Recebido no Mês"
            value={formatCurrency(dash?.recebido_mes)}
            icon={<TrendingUp className="size-4" />}
          />
          <StatCard
            label="A Pagar (aberto)"
            value={formatCurrency(dash?.total_contas_pagar_abertas)}
            icon={<TrendingDown className="size-4" />}
          />
          <StatCard
            label="Vencidas"
            value={formatCurrency(dash?.total_contas_pagar_vencidas)}
            icon={<AlertTriangle className="size-4" />}
            accent={Number(dash?.total_contas_pagar_vencidas) > 0}
          />
          <StatCard
            label="Saldo em Caixa"
            value={formatCurrency(dash?.saldo_caixa)}
            icon={<Landmark className="size-4" />}
          />
        </div>

        {/* ─── Tabs ──────────────────────────────────────────────────────── */}
        <Tabs.Root defaultValue="contas-pagar">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <Tabs.List className="flex gap-1 rounded-lg border border-zinc-200 bg-zinc-50 p-1">
              <Tabs.Trigger
                value="contas-pagar"
                className="rounded-md px-3 py-1.5 text-xs font-medium text-zinc-500 transition-colors data-[state=active]:bg-white data-[state=active]:text-zinc-900 data-[state=active]:shadow-sm"
              >
                Contas a Pagar
              </Tabs.Trigger>
              <Tabs.Trigger
                value="lancamentos"
                className="rounded-md px-3 py-1.5 text-xs font-medium text-zinc-500 transition-colors data-[state=active]:bg-white data-[state=active]:text-zinc-900 data-[state=active]:shadow-sm"
              >
                Lançamentos
              </Tabs.Trigger>
            </Tabs.List>

            {canOperate && (
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  icon={<TrendingUp className="size-3.5 text-green-600" />}
                  onClick={() => setNovaLancamentoTipo("ENTRADA")}
                >
                  Nova Receita
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  icon={<TrendingDown className="size-3.5 text-red-500" />}
                  onClick={() => setNovaLancamentoTipo("SAIDA")}
                >
                  Nova Despesa
                </Button>
                <Button
                  size="sm"
                  icon={<Plus className="size-3.5" />}
                  onClick={() => setNovaContaOpen(true)}
                >
                  Nova Conta a Pagar
                </Button>
              </div>
            )}
          </div>

          {/* ─── Tab: Contas a Pagar ──────────────────────────────────── */}
          <Tabs.Content value="contas-pagar" className="mt-4">
            <Card>
              {/* Filtros */}
              <div className="flex flex-wrap items-center gap-2 border-b border-zinc-100 px-5 py-3.5">
                {(
                  [
                    ["abertas", "Abertas"],
                    ["vencidas", "Vencidas"],
                    ["todas", "Todas"],
                    ["pagas", "Pagas"],
                    ["canceladas", "Canceladas"],
                  ] as [FilterCP, string][]
                ).map(([value, label]) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => {
                      setPageCP(1)
                      setFilterCP(value)
                    }}
                    className={`h-7 rounded-md border px-3 text-xs font-medium transition-colors ${
                      filterCP === value
                        ? "border-orange-300 bg-orange-50 text-orange-700"
                        : "border-zinc-200 text-zinc-500 hover:border-zinc-300 hover:text-zinc-800"
                    }`}
                  >
                    {label}
                  </button>
                ))}
                <span className="ml-auto text-xs text-zinc-500">
                  <span className="font-medium text-zinc-800">{contasQuery.data?.count ?? 0}</span> contas
                </span>
              </div>

              <CardContent className="p-0">
                {contasQuery.isLoading ? (
                  <SkeletonTable rows={6} cols={7} />
                ) : contas.length === 0 ? (
                  <EmptyState
                    icon={<Landmark className="size-5" />}
                    title="Nenhuma conta a pagar encontrada"
                    description="Cadastre contas de fornecedores, despesas e boletos para acompanhar vencimentos e baixas."
                    actionLabel={canOperate ? "Nova conta a pagar" : undefined}
                    onAction={canOperate ? () => setNovaContaOpen(true) : undefined}
                  />
                ) : (
                  <Table>
                    <Thead>
                      <tr>
                        <Th>Descrição</Th>
                        <Th>Fornecedor</Th>
                        <Th>Categoria</Th>
                        <Th>Vencimento</Th>
                        <Th className="text-right">Total</Th>
                        <Th className="text-right">Restante</Th>
                        <Th>Status</Th>
                        {canOperate && <Th />}
                      </tr>
                    </Thead>
                    <Tbody>
                      {contas.map((conta) => {
                        const podeOperar = conta.status === "ABERTA"
                        return (
                          <Tr key={conta.id}>
                            <Td>
                              <div>
                                <p className="text-sm font-medium text-zinc-900 max-w-[200px] truncate">
                                  {conta.descricao}
                                </p>
                                {conta.data_pagamento && (
                                  <p className="text-[11px] text-zinc-400">
                                    Pago em {formatDatetime(conta.data_pagamento)}
                                  </p>
                                )}
                              </div>
                            </Td>
                            <Td className="text-xs text-zinc-500">{conta.fornecedor_nome || "—"}</Td>
                            <Td className="text-xs text-zinc-500">{conta.categoria_nome}</Td>
                            <Td>
                              <span className={`text-xs ${conta.is_atrasada ? "font-semibold text-red-600" : "text-zinc-500"}`}>
                                {formatDate(conta.data_vencimento)}
                              </span>
                            </Td>
                            <Td className="text-right tabular-nums text-sm text-zinc-700">
                              {formatCurrency(conta.valor_total)}
                            </Td>
                            <Td className="text-right">
                              <span className={`tabular-nums text-sm font-semibold ${
                                conta.status === "PAGA" ? "text-green-600" : "text-red-600"
                              }`}>
                                {formatCurrency(conta.valor_restante)}
                              </span>
                            </Td>
                            <Td>{statusBadge(conta)}</Td>
                            {canOperate && (
                              <Td>
                                {podeOperar && (
                                  <div className="flex items-center gap-1">
                                    <Button
                                      size="xs"
                                      onClick={() => setPagarConta(conta)}
                                    >
                                      Baixar
                                    </Button>
                                    <button
                                      type="button"
                                      title="Cancelar conta"
                                      onClick={() => setCancelarConta(conta)}
                                      className="flex size-7 items-center justify-center rounded-md text-zinc-400 transition-colors hover:bg-red-50 hover:text-red-600"
                                    >
                                      <Ban className="size-3.5" />
                                    </button>
                                  </div>
                                )}
                              </Td>
                            )}
                          </Tr>
                        )
                      })}
                    </Tbody>
                  </Table>
                )}
              </CardContent>

              {/* Paginação */}
              <div className="flex items-center justify-between border-t border-zinc-100 bg-zinc-50/50 px-5 py-3">
                <span className="text-xs text-zinc-500">
                  Página {pageCP} de {Math.max(totalPagesCP, 1)}
                </span>
                <div className="flex items-center gap-1.5">
                  <Button
                    variant="outline"
                    size="xs"
                    icon={<ChevronLeft className="size-3.5" />}
                    disabled={pageCP <= 1 || contasQuery.isFetching}
                    onClick={() => setPageCP((p) => Math.max(1, p - 1))}
                  >
                    Anterior
                  </Button>
                  <Button
                    variant="outline"
                    size="xs"
                    disabled={pageCP >= totalPagesCP || contasQuery.isFetching}
                    onClick={() => setPageCP((p) => p + 1)}
                  >
                    Próximo
                    <ChevronRight className="size-3.5" />
                  </Button>
                </div>
              </div>
            </Card>
          </Tabs.Content>

          {/* ─── Tab: Lançamentos ────────────────────────────────────── */}
          <Tabs.Content value="lancamentos" className="mt-4">
            <Card>
              <CardHeader className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Wallet className="size-4 text-zinc-400" />
                  <h3 className="text-sm font-semibold text-zinc-900">Lançamentos Financeiros</h3>
                </div>
                <Badge variant="outline">{lancamentosQuery.data?.count ?? 0}</Badge>
              </CardHeader>

              <CardContent className="p-0">
                <LancamentosTable
                  lancamentos={lancamentos}
                  loading={lancamentosQuery.isLoading}
                />
              </CardContent>

              {/* Paginação */}
              <div className="flex items-center justify-between border-t border-zinc-100 bg-zinc-50/50 px-5 py-3">
                <span className="text-xs text-zinc-500">
                  Página {pageL} de {Math.max(totalPagesL, 1)}
                </span>
                <div className="flex items-center gap-1.5">
                  <Button
                    variant="outline"
                    size="xs"
                    icon={<ChevronLeft className="size-3.5" />}
                    disabled={pageL <= 1 || lancamentosQuery.isFetching}
                    onClick={() => setPageL((p) => Math.max(1, p - 1))}
                  >
                    Anterior
                  </Button>
                  <Button
                    variant="outline"
                    size="xs"
                    disabled={pageL >= totalPagesL || lancamentosQuery.isFetching}
                    onClick={() => setPageL((p) => p + 1)}
                  >
                    Próximo
                    <ChevronRight className="size-3.5" />
                  </Button>
                </div>
              </div>
            </Card>
          </Tabs.Content>
        </Tabs.Root>
      </main>

      {/* ─── Dialogs ──────────────────────────────────────────────────────── */}
      {pagarConta && (
        <PagarContaDialog
          conta={pagarConta}
          open={Boolean(pagarConta)}
          onOpenChange={(open) => !open && setPagarConta(null)}
        />
      )}

      <CancelarContaDialog
        conta={cancelarConta}
        onClose={() => setCancelarConta(null)}
      />

      <NovaContaPagarDialog
        open={novaContaOpen}
        onOpenChange={setNovaContaOpen}
      />

      <NovaLancamentoDialog
        open={Boolean(novaLancamentoTipo)}
        onOpenChange={(open) => !open && setNovaLancamentoTipo(null)}
        tipoInicial={novaLancamentoTipo ?? "ENTRADA"}
      />
    </Shell>
  )
}
