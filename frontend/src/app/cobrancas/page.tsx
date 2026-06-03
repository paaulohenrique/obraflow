"use client"

import { useMemo, useState } from "react"
import * as Dialog from "@radix-ui/react-dialog"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  AlertTriangle,
  CheckCheck,
  Clock3,
  Eye,
  Filter,
  MessageCircle,
  Search,
  Send,
  Users,
  X,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { EmptyState } from "@/components/ui/empty-state"
import { ErrorState } from "@/components/ui/error-state"
import { Input } from "@/components/ui/input"
import { SkeletonTable } from "@/components/ui/skeleton"
import { StatCard } from "@/components/ui/stat-card"
import { Table, Tbody, Td, Th, Thead, Tr } from "@/components/ui/table"
import { Shell } from "@/components/layout/shell"
import { Topbar } from "@/components/layout/topbar"
import { useApiToast } from "@/hooks/use-api-toast"
import { useDebouncedValue } from "@/hooks/use-debounced-value"
import { createIdempotencyKey } from "@/lib/idempotency"
import { toNumber } from "@/lib/format"
import { cn, formatCurrency, formatDate, formatDatetime, formatDocument, formatPhone, initials } from "@/lib/utils"
import { cobrancasService } from "@/services/cobrancas.service"
import type { CobrancaConta, CobrancaPreview, StatusNotificacao } from "@/types"

type StatusFilter = "TODOS" | StatusNotificacao
type CriterioLote = 1 | 7 | 15 | 30

const statusOptions: Array<{ value: StatusFilter; label: string }> = [
  { value: "TODOS", label: "Todos" },
  { value: "PENDENTE", label: "Pendentes" },
  { value: "ENVIADA", label: "Enviadas" },
  { value: "ENTREGUE", label: "Entregues" },
  { value: "LIDA", label: "Lidas" },
  { value: "FALHOU", label: "Falharam" },
]

const criteriosLote: CriterioLote[] = [1, 7, 15, 30]

function statusBadge(status: StatusNotificacao) {
  if (status === "LIDA") return <Badge variant="success">Lida</Badge>
  if (status === "ENTREGUE") return <Badge variant="info">Entregue</Badge>
  if (status === "ENVIADA") return <Badge variant="default">Enviada</Badge>
  if (status === "FALHOU") return <Badge variant="error">Falhou</Badge>
  if (status === "ENFILEIRADA") return <Badge variant="warning">Enfileirada</Badge>
  return <Badge variant="warning">Pendente</Badge>
}

function atrasoLabel(conta: CobrancaConta) {
  if (!conta.data_vencimento) return "Sem vencimento"
  if (conta.dias_atraso <= 0) return "No prazo"
  return `${conta.dias_atraso}d atraso`
}

export default function CobrancasPage() {
  const queryClient = useQueryClient()
  const toast = useApiToast()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState("")
  const [status, setStatus] = useState<StatusFilter>("TODOS")
  const [diasMin, setDiasMin] = useState("")
  const [valorMin, setValorMin] = useState("")
  const [valorMax, setValorMax] = useState("")
  const [dataInicio, setDataInicio] = useState("")
  const [dataFim, setDataFim] = useState("")
  const [preview, setPreview] = useState<CobrancaPreview | null>(null)
  const [previewConta, setPreviewConta] = useState<CobrancaConta | null>(null)
  const [criterioLote, setCriterioLote] = useState<CriterioLote>(1)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const debouncedSearch = useDebouncedValue(search.trim(), 300)

  const filters = {
    page,
    page_size: 20,
    search: debouncedSearch,
    ...(status !== "TODOS" ? { status } : {}),
    ...(diasMin ? { dias_atraso_min: diasMin } : {}),
    ...(valorMin ? { valor_min: valorMin } : {}),
    ...(valorMax ? { valor_max: valorMax } : {}),
    ...(dataInicio ? { data_inicio: dataInicio } : {}),
    ...(dataFim ? { data_fim: dataFim } : {}),
  }

  const dashboardQuery = useQuery({
    queryKey: ["cobrancas", "dashboard", filters],
    queryFn: () => cobrancasService.dashboard(filters),
    staleTime: 30_000,
  })

  const contasQuery = useQuery({
    queryKey: ["cobrancas", "contas", filters],
    queryFn: () => cobrancasService.list(filters),
    staleTime: 20_000,
  })

  const loteQuery = useQuery({
    queryKey: ["cobrancas", "lote", criterioLote],
    queryFn: () => cobrancasService.list({ criterio: criterioLote, page_size: 100, ordering: "cliente__nome" }),
    staleTime: 20_000,
  })

  const previewMutation = useMutation({
    mutationFn: (conta: CobrancaConta) => cobrancasService.preview({ conta_id: conta.id }),
    onSuccess: (data, conta) => {
      setPreviewConta(conta)
      setPreview(data)
    },
    onError: (error) => toast.error(error),
  })

  const enviarMutation = useMutation({
    mutationFn: (payload: { conta_id: string; tipo?: CobrancaPreview["tipo"] }) =>
      cobrancasService.enviar({
        conta_id: payload.conta_id,
        tipo: payload.tipo,
        idempotency_key: createIdempotencyKey("cobranca-individual"),
      }),
    onSuccess: () => {
      toast.success("Cobrança enviada para a fila do WhatsApp.")
      setPreview(null)
      setPreviewConta(null)
      queryClient.invalidateQueries({ queryKey: ["cobrancas"] })
      queryClient.invalidateQueries({ queryKey: ["fiado"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
    onError: (error) => toast.error(error),
  })

  const loteMutation = useMutation({
    mutationFn: () =>
      cobrancasService.enviarLote({
        criterio: criterioLote,
        conta_ids: Array.from(selectedIds),
        idempotency_key: createIdempotencyKey(`cobranca-lote-${criterioLote}`),
      }),
    onSuccess: (data) => {
      toast.success(`${data.quantidade} cobranças enviadas para a fila.`)
      setSelectedIds(new Set())
      queryClient.invalidateQueries({ queryKey: ["cobrancas"] })
      queryClient.invalidateQueries({ queryKey: ["fiado"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
    onError: (error) => toast.error(error),
  })

  const contas = contasQuery.data?.results ?? []
  const loteContas = useMemo(() => loteQuery.data?.results ?? [], [loteQuery.data?.results])
  const totalPages = contasQuery.data?.total_pages ?? 1
  const currentPage = contasQuery.data?.current_page ?? page
  const dash = dashboardQuery.data

  const selectedLote = useMemo(
    () => loteContas.filter((conta) => selectedIds.has(conta.id)),
    [loteContas, selectedIds]
  )
  const valorSelecionado = selectedLote.reduce((sum, conta) => sum + toNumber(conta.valor_restante), 0)
  const allSelected = loteContas.length > 0 && selectedIds.size === loteContas.length

  const toggleSelected = (id: string) => {
    setSelectedIds((current) => {
      const next = new Set(current)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleAll = () => {
    setSelectedIds(allSelected ? new Set() : new Set(loteContas.map((conta) => conta.id)))
  }

  return (
    <Shell>
      <Topbar title="Cobranças" subtitle="Central operacional integrada ao WhatsApp" />

      <main className="flex-1 space-y-5 p-4 md:p-6">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-6">
          <StatCard label="Enviadas" value={`${dash?.mensagens_enviadas ?? 0}`} icon={<Send className="size-4" />} accent />
          <StatCard label="Entregues" value={`${dash?.entregues ?? 0}`} icon={<CheckCheck className="size-4" />} />
          <StatCard label="Lidas" value={`${dash?.lidas ?? 0}`} icon={<Eye className="size-4" />} />
          <StatCard label="Falharam" value={`${dash?.falharam ?? 0}`} icon={<AlertTriangle className="size-4" />} />
          <StatCard label="Valor Cobrado" value={formatCurrency(dash?.valor_cobrado)} icon={<MessageCircle className="size-4" />} />
          <StatCard label="Recuperação" value={`${dash?.percentual_recuperacao ?? 0}%`} icon={<Users className="size-4" />} />
        </div>

        <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
          <Card>
            <CardHeader className="space-y-3">
              <div className="flex flex-wrap items-center gap-3">
                <div className="relative min-w-64 flex-1 max-w-sm">
                  <Search className="absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-zinc-400" />
                  <Input
                    placeholder="Cliente, CPF/CNPJ ou telefone"
                    value={search}
                    onChange={(event) => {
                      setPage(1)
                      setSearch(event.target.value)
                    }}
                    className="pl-8"
                  />
                </div>
                <div className="flex items-center gap-1 overflow-x-auto">
                  {statusOptions.map((item) => (
                    <button
                      key={item.value}
                      type="button"
                      onClick={() => {
                        setPage(1)
                        setStatus(item.value)
                      }}
                      className={cn(
                        "h-8 rounded-md border px-3 text-xs font-medium transition-colors",
                        status === item.value
                          ? "border-zinc-900 bg-zinc-900 text-white"
                          : "border-zinc-200 bg-white text-zinc-600 hover:border-zinc-400 hover:text-zinc-900"
                      )}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
                <div className="ml-auto flex items-center gap-1 text-xs text-zinc-500">
                  <Filter className="size-3.5" />
                  <span className="font-medium text-zinc-800">{contasQuery.data?.count ?? 0}</span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
                <Input type="date" value={dataInicio} onChange={(event) => setDataInicio(event.target.value)} />
                <Input type="date" value={dataFim} onChange={(event) => setDataFim(event.target.value)} />
                <Input placeholder="Dias atraso min." value={diasMin} onChange={(event) => setDiasMin(event.target.value)} />
                <Input placeholder="Valor min." value={valorMin} onChange={(event) => setValorMin(event.target.value)} />
                <Input placeholder="Valor max." value={valorMax} onChange={(event) => setValorMax(event.target.value)} />
              </div>
            </CardHeader>

            <CardContent className="p-0">
              {contasQuery.isLoading ? (
                <SkeletonTable rows={8} cols={7} />
              ) : contasQuery.isError ? (
                <ErrorState onRetry={() => contasQuery.refetch()} />
              ) : contas.length === 0 ? (
                <EmptyState
                  icon={<MessageCircle className="size-5" />}
                  title="Nenhuma cobrança na fila"
                  description="Contas abertas com saldo em aberto aparecem aqui conforme os filtros selecionados."
                />
              ) : (
                <Table>
                  <Thead>
                    <tr>
                      <Th>Cliente</Th>
                      <Th>Status</Th>
                      <Th>Vencimento</Th>
                      <Th className="text-right">Aberto</Th>
                      <Th>Última cobrança</Th>
                      <Th />
                    </tr>
                  </Thead>
                  <Tbody>
                    {contas.map((conta) => (
                      <Tr key={conta.id}>
                        <Td>
                          <div className="flex items-center gap-2.5">
                            <div className="flex size-8 flex-shrink-0 items-center justify-center rounded-full bg-zinc-100">
                              <span className="text-[10px] font-semibold text-zinc-600">{initials(conta.cliente_nome)}</span>
                            </div>
                            <div>
                              <p className="font-medium leading-tight text-zinc-900">{conta.cliente_nome}</p>
                              <p className="text-[11px] text-zinc-400">
                                {formatDocument(conta.cliente_documento)}
                                {conta.cliente_whatsapp ? ` · ${formatPhone(conta.cliente_whatsapp)}` : ""}
                              </p>
                            </div>
                          </div>
                        </Td>
                        <Td>{statusBadge(conta.status_cobranca)}</Td>
                        <Td>
                          <div className="text-xs">
                            <p className="font-medium text-zinc-700">{conta.data_vencimento ? formatDate(conta.data_vencimento) : "-"}</p>
                            <p className={cn("mt-0.5", conta.dias_atraso > 0 ? "text-red-600" : "text-zinc-400")}>
                              {atrasoLabel(conta)}
                            </p>
                          </div>
                        </Td>
                        <Td className="text-right font-semibold tabular-nums text-red-600">
                          {formatCurrency(conta.valor_restante)}
                        </Td>
                        <Td className="text-xs text-zinc-500">
                          {conta.ultima_cobranca_em ? formatDatetime(conta.ultima_cobranca_em) : "Nunca"}
                        </Td>
                        <Td>
                          <Button
                            size="xs"
                            variant="outline"
                            icon={<MessageCircle className="size-3.5" />}
                            disabled={!conta.tem_contato || previewMutation.isPending}
                            loading={previewMutation.isPending && previewConta?.id === conta.id}
                            onClick={() => previewMutation.mutate(conta)}
                          >
                            Cobrar
                          </Button>
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              )}
            </CardContent>

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

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-zinc-900">Cobrança em Lote</h3>
                  <p className="mt-0.5 text-xs text-zinc-500">{selectedIds.size} selecionados</p>
                </div>
                <select
                  value={criterioLote}
                  onChange={(event) => {
                    setCriterioLote(Number(event.target.value) as CriterioLote)
                    setSelectedIds(new Set())
                  }}
                  className="h-8 rounded-md border border-zinc-300 bg-white px-2 text-xs font-medium text-zinc-800 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/30"
                >
                  {criteriosLote.map((criterio) => (
                    <option key={criterio} value={criterio}>{criterio} dias</option>
                  ))}
                </select>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-2">
                <div className="rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2">
                  <p className="text-[10px] font-medium text-zinc-400">Quantidade</p>
                  <p className="mt-0.5 text-lg font-bold text-zinc-900">{selectedIds.size}</p>
                </div>
                <div className="rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2">
                  <p className="text-[10px] font-medium text-zinc-400">Valor total</p>
                  <p className="mt-0.5 text-lg font-bold text-red-600">{formatCurrency(valorSelecionado)}</p>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <button
                  type="button"
                  className="text-xs font-semibold text-zinc-700 hover:text-zinc-950"
                  onClick={toggleAll}
                  disabled={loteContas.length === 0}
                >
                  {allSelected ? "Limpar seleção" : "Selecionar todos"}
                </button>
                <span className="text-xs text-zinc-400">{loteQuery.data?.count ?? 0} elegíveis</span>
              </div>

              <div className="max-h-[360px] space-y-2 overflow-y-auto pr-1">
                {loteQuery.isLoading ? (
                  Array.from({ length: 5 }).map((_, index) => (
                    <div key={index} className="h-14 animate-pulse rounded-md bg-zinc-100" />
                  ))
                ) : loteContas.length === 0 ? (
                  <div className="rounded-md border border-dashed border-zinc-200 px-3 py-6 text-center text-xs text-zinc-500">
                    Nenhuma conta para este critério.
                  </div>
                ) : (
                  loteContas.map((conta) => (
                    <label
                      key={conta.id}
                      className={cn(
                        "flex cursor-pointer items-center gap-3 rounded-md border px-3 py-2 transition-colors",
                        selectedIds.has(conta.id)
                          ? "border-orange-300 bg-orange-50"
                          : "border-zinc-200 bg-white hover:border-zinc-300"
                      )}
                    >
                      <input
                        type="checkbox"
                        checked={selectedIds.has(conta.id)}
                        onChange={() => toggleSelected(conta.id)}
                        className="size-4 rounded border-zinc-300 text-orange-500 focus:ring-orange-500"
                      />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-xs font-semibold text-zinc-900">{conta.cliente_nome}</p>
                        <p className="text-[11px] text-zinc-400">{formatCurrency(conta.valor_restante)}</p>
                      </div>
                      <Clock3 className="size-3.5 text-zinc-400" />
                    </label>
                  ))
                )}
              </div>

              <Button
                className="w-full"
                icon={<Send className="size-3.5" />}
                disabled={selectedIds.size === 0 || loteMutation.isPending}
                loading={loteMutation.isPending}
                onClick={() => loteMutation.mutate()}
              >
                Enviar Lote
              </Button>
            </CardContent>
          </Card>
        </div>
      </main>

      <Dialog.Root open={Boolean(preview)} onOpenChange={(open) => { if (!open) setPreview(null) }}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px]" />
          <Dialog.Content
            className="fixed left-1/2 top-1/2 z-50 w-[calc(100vw-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-lg border border-zinc-200 bg-white p-5 shadow-xl focus:outline-none"
            aria-describedby={undefined}
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <Dialog.Title className="text-sm font-semibold text-zinc-900">Preview da cobrança</Dialog.Title>
                {preview && (
                  <p className="mt-1 text-xs text-zinc-500">
                    {preview.cliente_nome} · {formatCurrency(preview.valor)} · {preview.dias_atraso}d atraso
                  </p>
                )}
              </div>
              <Dialog.Close asChild>
                <button className="rounded-md p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700" aria-label="Fechar">
                  <X className="size-4" />
                </button>
              </Dialog.Close>
            </div>

            {preview && (
              <div className="mt-4 space-y-4">
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded-md border border-zinc-200 px-3 py-2">
                    <p className="text-zinc-400">Vencimento</p>
                    <p className="mt-0.5 font-semibold text-zinc-900">{preview.data_vencimento_formatada}</p>
                  </div>
                  <div className="rounded-md border border-zinc-200 px-3 py-2">
                    <p className="text-zinc-400">Template</p>
                    <p className="mt-0.5 font-semibold text-zinc-900">{preview.tipo}</p>
                  </div>
                </div>
                <div className="whitespace-pre-wrap rounded-md border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm leading-relaxed text-zinc-800">
                  {preview.mensagem}
                </div>
                <div className="flex justify-end gap-2">
                  <Dialog.Close asChild>
                    <Button variant="outline" size="sm">Cancelar</Button>
                  </Dialog.Close>
                  <Button
                    size="sm"
                    icon={<Send className="size-3.5" />}
                    loading={enviarMutation.isPending}
                    onClick={() => enviarMutation.mutate({ conta_id: preview.conta_id, tipo: preview.tipo })}
                  >
                    Enviar
                  </Button>
                </div>
              </div>
            )}
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </Shell>
  )
}
