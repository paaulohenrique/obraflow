"use client"

import Link from "next/link"
import { useParams } from "next/navigation"
import * as Dialog from "@radix-ui/react-dialog"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft, Banknote, CheckCircle2, CreditCard, FileDown, History, MessageCircle, Package, Plus, Printer, Send, User, X, XCircle } from "lucide-react"
import { useEffect, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { FiadoItemDialog } from "@/features/fiado/fiado-item-dialog"
import { FiadoPagamentoDialog } from "@/features/fiado/fiado-pagamento-dialog"
import { Shell } from "@/components/layout/shell"
import { Topbar } from "@/components/layout/topbar"
import { cn, formatCurrency, formatDate, formatDatetime, formatDocument, initials } from "@/lib/utils"
import { formatNumber, toNumber } from "@/lib/format"
import { fiadoService } from "@/services/fiado.service"
import { cobrancasService } from "@/services/cobrancas.service"
import { estoqueService } from "@/services/estoque.service"
import { useApiToast } from "@/hooks/use-api-toast"
import { createIdempotencyKey } from "@/lib/idempotency"
import type { CobrancaPreview } from "@/types"

type Tab = "itens" | "pagamentos" | "historico"

function contaStatus(status?: string, atrasada?: boolean, parcial?: boolean) {
  if (status === "FECHADA") return { label: "Fechada", variant: "success" as const }
  if (status === "CANCELADA") return { label: "Cancelada", variant: "outline" as const }
  if (atrasada) return { label: "Atrasada", variant: "error" as const }
  if (parcial) return { label: "Parcial", variant: "default" as const }
  return { label: "Aberta", variant: "warning" as const }
}

export default function FiadoDetalhePage() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  const toast = useApiToast()
  const [tab, setTab] = useState<Tab>("itens")
  const [itemDialogOpen, setItemDialogOpen] = useState(false)
  const [pagamentoDialogOpen, setPagamentoDialogOpen] = useState(false)
  const [cobrancaPreview, setCobrancaPreview] = useState<CobrancaPreview | null>(null)

  const handlePrefetchProducts = () => {
    queryClient.prefetchQuery({
      queryKey: ["estoque", "produtos", "fiado-autocomplete", { search: "", page: 1 }],
      queryFn: () =>
        estoqueService.list({
          page: 1,
          page_size: 8,
          search: "",
          ordering: "nome",
          is_active: true,
        }),
      staleTime: 30_000,
    })
  }

  useEffect(() => {
    const openProductSearch = () => setItemDialogOpen(true)
    window.addEventListener("obraflow:open-product-search", openProductSearch)
    return () => window.removeEventListener("obraflow:open-product-search", openProductSearch)
  }, [])

  const contaQuery = useQuery({
    queryKey: ["fiado", "contas", id],
    queryFn: () => fiadoService.get(id),
    staleTime: 10_000,
  })

  const itensQuery = useQuery({
    queryKey: ["fiado", "contas", id, "itens"],
    queryFn: () => fiadoService.itens(id, { page_size: 100 }),
    enabled: Boolean(contaQuery.data),
    staleTime: 10_000,
  })

  const pagamentosQuery = useQuery({
    queryKey: ["fiado", "contas", id, "pagamentos"],
    queryFn: () => fiadoService.pagamentos(id, { page_size: 100 }),
    enabled: Boolean(contaQuery.data),
    staleTime: 10_000,
  })

  const historicoQuery = useQuery({
    queryKey: ["fiado", "contas", id, "historico"],
    queryFn: () => fiadoService.historico(id, { page_size: 100 }),
    enabled: Boolean(contaQuery.data),
    staleTime: 10_000,
  })

  const baixarPdfMutation = useMutation({
    mutationFn: () => fiadoService.baixarPdfContaFiado(id),
    onError: (error) => toast.error(error),
  })

  const previewCobrancaMutation = useMutation({
    mutationFn: () => cobrancasService.preview({ conta_id: id }),
    onSuccess: setCobrancaPreview,
    onError: (error) => toast.error(error),
  })

  const enviarCobrancaMutation = useMutation({
    mutationFn: (preview: CobrancaPreview) =>
      cobrancasService.enviar({
        conta_id: preview.conta_id,
        tipo: preview.tipo,
        idempotency_key: createIdempotencyKey("fiado-cobranca"),
      }),
    onSuccess: () => {
      toast.success("Cobrança enviada para a fila do WhatsApp.")
      setCobrancaPreview(null)
      queryClient.invalidateQueries({ queryKey: ["fiado"] })
      queryClient.invalidateQueries({ queryKey: ["cobrancas"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
    onError: (error) => toast.error(error),
  })

  const conta = contaQuery.data
  const contaAberta = conta?.status === "ABERTA"

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "F2" && contaAberta) {
        e.preventDefault()
        setItemDialogOpen(true)
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [contaAberta])

  if (contaQuery.isLoading) {
    return (
      <Shell>
        <Topbar title="Fiado" />
        <main className="flex-1 space-y-5 p-4 md:p-6">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-80 w-full" />
        </main>
      </Shell>
    )
  }

  if (!conta) {
    return (
      <Shell>
        <Topbar title="Fiado não encontrado" />
        <main className="flex flex-1 flex-col items-center justify-center gap-3 p-6">
          <XCircle className="size-12 text-zinc-300" />
          <p className="text-sm text-zinc-500">Conta de fiado não encontrada.</p>
          <Link href="/fiado">
            <Button variant="outline" size="sm" icon={<ArrowLeft className="size-3.5" />}>
              Voltar
            </Button>
          </Link>
        </main>
      </Shell>
    )
  }

  const itens = itensQuery.data?.results ?? []
  const pagamentos = pagamentosQuery.data?.results ?? []
  const historico = historicoQuery.data?.results ?? []
  const status = contaStatus(conta.status, conta.is_atrasada, conta.is_parcial)
  const total = toNumber(conta.valor_total)
  const pago = toNumber(conta.valor_pago)
  const pctPago = total > 0 ? Math.round((pago / total) * 100) : 0
  const contaFechada = conta.status === "FECHADA"

  return (
    <Shell>
      <FiadoItemDialog conta={conta} open={itemDialogOpen} onOpenChange={setItemDialogOpen} />
      <FiadoPagamentoDialog conta={conta} open={pagamentoDialogOpen} onOpenChange={setPagamentoDialogOpen} />
      <Dialog.Root open={Boolean(cobrancaPreview)} onOpenChange={(open) => { if (!open) setCobrancaPreview(null) }}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px]" />
          <Dialog.Content
            className="fixed left-1/2 top-1/2 z-50 w-[calc(100vw-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-lg border border-zinc-200 bg-white p-5 shadow-xl focus:outline-none"
            aria-describedby={undefined}
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <Dialog.Title className="text-sm font-semibold text-zinc-900">Preview da cobrança</Dialog.Title>
                {cobrancaPreview && (
                  <p className="mt-1 text-xs text-zinc-500">
                    {cobrancaPreview.cliente_nome} · {formatCurrency(cobrancaPreview.valor)} · {cobrancaPreview.dias_atraso}d atraso
                  </p>
                )}
              </div>
              <Dialog.Close asChild>
                <button className="rounded-md p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700" aria-label="Fechar">
                  <X className="size-4" />
                </button>
              </Dialog.Close>
            </div>
            {cobrancaPreview && (
              <div className="mt-4 space-y-4">
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded-md border border-zinc-200 px-3 py-2">
                    <p className="text-zinc-400">Vencimento</p>
                    <p className="mt-0.5 font-semibold text-zinc-900">{cobrancaPreview.data_vencimento_formatada}</p>
                  </div>
                  <div className="rounded-md border border-zinc-200 px-3 py-2">
                    <p className="text-zinc-400">Valor</p>
                    <p className="mt-0.5 font-semibold text-zinc-900">{formatCurrency(cobrancaPreview.valor)}</p>
                  </div>
                </div>
                <div className="whitespace-pre-wrap rounded-md border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm leading-relaxed text-zinc-800">
                  {cobrancaPreview.mensagem}
                </div>
                <div className="flex justify-end gap-2">
                  <Dialog.Close asChild>
                    <Button variant="outline" size="sm">Cancelar</Button>
                  </Dialog.Close>
                  <Button
                    size="sm"
                    icon={<Send className="size-3.5" />}
                    loading={enviarCobrancaMutation.isPending}
                    onClick={() => enviarCobrancaMutation.mutate(cobrancaPreview)}
                  >
                    Enviar
                  </Button>
                </div>
              </div>
            )}
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      <Topbar
        title={conta.cliente_nome}
        subtitle={`Fiado #${conta.id.slice(0, 8)} · Aberto em ${formatDate(conta.data_abertura)}`}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={!contaAberta || toNumber(conta.valor_restante) <= 0}
              loading={previewCobrancaMutation.isPending}
              icon={<MessageCircle className="size-3.5" />}
              onClick={() => previewCobrancaMutation.mutate()}
            >
              Cobrar
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={!contaAberta}
              icon={<Banknote className="size-3.5" />}
              onClick={() => setPagamentoDialogOpen(true)}
            >
              Pagamento
            </Button>
            <Button
              size="sm"
              disabled={!contaAberta}
              icon={<Plus className="size-3.5" />}
              onClick={() => setItemDialogOpen(true)}
              onMouseEnter={handlePrefetchProducts}
              className="bg-orange-500 hover:bg-orange-600 text-white font-bold"
            >
              Item (F2)
            </Button>
            <Button
              variant="outline"
              size="sm"
              icon={<FileDown className="size-3.5" />}
              loading={baixarPdfMutation.isPending}
              onClick={() => baixarPdfMutation.mutate()}
            >
              PDF
            </Button>
            <Button
              variant="outline"
              size="sm"
              icon={<Printer className="size-3.5" />}
              onClick={() => window.print()}
            >
              Imprimir
            </Button>
            <Link href={`/clientes/${conta.cliente}`}>
              <Button variant="ghost" size="sm" icon={<User className="size-3.5" />}>
                Cliente
              </Button>
            </Link>
            <Link href="/fiado">
              <Button variant="ghost" size="sm" icon={<ArrowLeft className="size-3.5" />}>
                Voltar
              </Button>
            </Link>
          </div>
        }
      />

      <main className="flex-1 space-y-5 p-4 md:p-6">
        {contaFechada && (
          <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="success">Conta finalizada</Badge>
              <p className="text-sm font-medium text-green-900">
                Esta conta já foi quitada e está disponível apenas para consulta.
              </p>
            </div>
            <p className="mt-1 text-xs text-green-700">
              Itens, pagamentos e histórico permanecem salvos. Você pode baixar o PDF, imprimir ou abrir uma nova conta pelo cliente.
            </p>
          </div>
        )}

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
          <Card className="border border-zinc-200 bg-white">
            <CardContent className="space-y-4 py-5 flex flex-col justify-between h-full">
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <div className="flex size-10 flex-shrink-0 items-center justify-center rounded-full bg-orange-100">
                    <span className="text-sm font-bold text-orange-700">{initials(conta.cliente_nome)}</span>
                  </div>
                  <div>
                    <p className="text-sm font-bold text-zinc-950">{conta.cliente_nome}</p>
                    <p className="text-xs text-zinc-400 font-mono">{formatDocument(conta.cliente_cpf_cnpj)}</p>
                  </div>
                </div>
                <div className="space-y-1.5 pt-2 border-t border-zinc-100 text-xs text-zinc-700">
                  <div className="flex items-center gap-2">
                    <User className="size-3.5 text-zinc-400" />
                    <span>Operador: {conta.created_by_nome || "Sistema"}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CreditCard className="size-3.5 text-zinc-400" />
                    <span>Vencimento da fatura: {conta.data_vencimento ? formatDate(conta.data_vencimento) : "Imediato"}</span>
                  </div>
                </div>
              </div>
              <div className="pt-2">
                <Badge variant={status.variant} className="font-bold">{status.label.toUpperCase()}</Badge>
              </div>
            </CardContent>
          </Card>

          <Card className="lg:col-span-2 bg-zinc-900 border-none text-white overflow-hidden relative shadow-md flex flex-col justify-between">
            <CardContent className="py-5 flex-1 flex flex-col justify-between">
              <div className="grid grid-cols-1 gap-3 md:grid-cols-3 border-b border-zinc-800 pb-4">
                <div>
                  <p className="mb-1 text-[10px] font-bold uppercase tracking-wider text-zinc-400">Total Lançado</p>
                  <p className="text-2xl font-bold tabular-nums text-white">{formatCurrency(conta.valor_total)}</p>
                </div>
                <div>
                  <p className="mb-1 text-[10px] font-bold uppercase tracking-wider text-zinc-500">Valor Pago</p>
                  <p className="text-2xl font-bold tabular-nums text-green-400">{formatCurrency(conta.valor_pago)}</p>
                </div>
                <div>
                  <p className="mb-1 text-[10px] font-bold uppercase tracking-wider text-zinc-500">Saldo Devedor</p>
                  <p className="text-2xl font-black tabular-nums text-orange-400">
                    {formatCurrency(conta.valor_restante)}
                  </p>
                </div>
              </div>

              <div className="mt-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div className="flex-1 max-w-xs">
                  <div className="mb-1 flex justify-between text-[10px] font-medium text-zinc-400">
                    <span>Progresso de quitação</span>
                    <span className="font-bold text-zinc-200">{pctPago}%</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-zinc-800">
                    <div className="h-full rounded-full bg-green-500 transition-all duration-300" style={{ width: `${Math.min(pctPago, 100)}%` }} />
                  </div>
                </div>

                {contaAberta && (
                  <Button
                    type="button"
                    size="sm"
                    onClick={() => setItemDialogOpen(true)}
                    onMouseEnter={handlePrefetchProducts}
                    className="bg-orange-500 hover:bg-orange-600 text-white font-bold border-none flex items-center gap-1.5 shadow-sm"
                    icon={<Plus className="size-4" />}
                  >
                    Lançar Produto (F2)
                  </Button>
                )}
              </div>

              {conta.observacao && (
                <p className="mt-3 rounded-md bg-zinc-900 px-3 py-1.5 text-[11px] text-zinc-400 border border-zinc-800">
                  Obs: {conta.observacao}
                </p>
              )}
            </CardContent>
          </Card>
        </div>

        <Card>
          <div className="flex gap-1 border-b border-zinc-100 px-5">
            {(["itens", "pagamentos", "historico"] as Tab[]).map((item) => (
              <button
                key={item}
                onClick={() => setTab(item)}
                className={cn(
                  "-mb-px border-b-2 px-1 py-3 text-sm font-medium capitalize transition-colors",
                  tab === item
                    ? "border-orange-500 text-orange-600"
                    : "border-transparent text-zinc-400 hover:text-zinc-700"
                )}
              >
                {item === "itens"
                  ? `Itens (${itensQuery.data?.count ?? 0})`
                  : item === "pagamentos"
                    ? `Pagamentos (${pagamentosQuery.data?.count ?? 0})`
                    : `Histórico (${historicoQuery.data?.count ?? 0})`}
              </button>
            ))}
            <div className="ml-auto flex items-center gap-2 py-2">
              {tab === "pagamentos" ? (
                <Button
                  size="xs"
                  variant="outline"
                  disabled={!contaAberta}
                  icon={<Banknote className="size-3.5" />}
                  onClick={() => setPagamentoDialogOpen(true)}
                >
                  Registrar
                </Button>
              ) : tab === "itens" ? (
                <Button
                  size="xs"
                  disabled={!contaAberta}
                  icon={<Plus className="size-3.5" />}
                  onClick={() => setItemDialogOpen(true)}
                  onMouseEnter={handlePrefetchProducts}
                >
                  Adicionar
                </Button>
              ) : null}
            </div>
          </div>

          {tab === "itens" && (
            <CardContent className="p-0">
              {itensQuery.isLoading ? (
                <div className="space-y-2 p-5">
                  {Array.from({ length: 4 }).map((_, index) => (
                    <Skeleton key={index} className="h-12 w-full" />
                  ))}
                </div>
              ) : itens.length === 0 ? (
                <div className="flex flex-col items-center gap-2 py-12 text-center">
                  <Package className="size-8 text-zinc-300" />
                  <p className="text-sm text-zinc-400">Nenhum item lançado.</p>
                </div>
              ) : (
                <div>
                  <div className="divide-y divide-zinc-100">
                    {itens.map((item) => (
                      <div key={item.id} className="flex items-center gap-4 px-5 py-3.5">
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium text-zinc-800">{item.produto_nome}</p>
                          <p className="mt-0.5 text-xs text-zinc-400">
                            {item.quantidade_informada && item.forma_venda_nome
                              ? `${formatNumber(item.quantidade_informada, 3)} ${item.forma_venda_nome} -> ${formatNumber(item.quantidade, 3)} base`
                              : `${formatNumber(item.quantidade, 3)} unidade base`}{" "}
                            x {formatCurrency(item.preco_unitario)}
                          </p>
                        </div>
                        <Badge variant={item.status === "ATIVO" ? "success" : "outline"}>{item.status}</Badge>
                        <span className="text-sm font-semibold tabular-nums text-zinc-900">{formatCurrency(item.subtotal)}</span>
                      </div>
                    ))}
                  </div>
                  <div className="flex justify-end border-t border-zinc-100 bg-zinc-50/50 px-5 py-3">
                    <div className="text-sm font-semibold tabular-nums text-zinc-900">Total: {formatCurrency(conta.valor_total)}</div>
                  </div>
                </div>
              )}
            </CardContent>
          )}

          {tab === "pagamentos" && (
            <CardContent className="p-0">
              {pagamentosQuery.isLoading ? (
                <div className="space-y-2 p-5">
                  {Array.from({ length: 4 }).map((_, index) => (
                    <Skeleton key={index} className="h-12 w-full" />
                  ))}
                </div>
              ) : pagamentos.length === 0 ? (
                <div className="flex flex-col items-center gap-2 py-12 text-center">
                  <CreditCard className="size-8 text-zinc-300" />
                  <p className="text-sm text-zinc-400">Nenhum pagamento registrado.</p>
                </div>
              ) : (
                <div className="divide-y divide-zinc-100">
                  {pagamentos.map((pagamento) => (
                    <div key={pagamento.id} className="flex items-center gap-4 px-5 py-3.5">
                      <div className="flex size-8 flex-shrink-0 items-center justify-center rounded-lg bg-green-50">
                        <CheckCircle2 className="size-4 text-green-500" />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-zinc-800">Pagamento via {pagamento.forma_pagamento}</p>
                        <p className="text-xs text-zinc-400">{formatDatetime(pagamento.data_pagamento)}</p>
                      </div>
                      <Badge variant={pagamento.status === "CONFIRMADO" ? "success" : "outline"}>{pagamento.status}</Badge>
                      <span className="text-sm font-semibold tabular-nums text-green-600">+{formatCurrency(pagamento.valor)}</span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          )}

          {tab === "historico" && (
            <CardContent className="py-5">
              {historicoQuery.isLoading ? (
                <div className="space-y-2">
                  {Array.from({ length: 5 }).map((_, index) => (
                    <Skeleton key={index} className="h-12 w-full" />
                  ))}
                </div>
              ) : historico.length === 0 ? (
                <div className="flex flex-col items-center gap-2 py-8 text-center">
                  <History className="size-8 text-zinc-300" />
                  <p className="text-sm text-zinc-400">Nenhum evento registrado.</p>
                </div>
              ) : (
                <div className="relative pl-6">
                  <div className="absolute bottom-2 left-[9px] top-2 w-px bg-zinc-200" />
                  {historico.map((evento) => (
                    <div key={evento.id} className="relative flex gap-3 pb-5 last:pb-0">
                      <div className="absolute -left-6 flex size-4 items-center justify-center rounded-full border-2 border-white bg-orange-500">
                        <History className="size-2.5 text-white" />
                      </div>
                      <div className="mt-0.5 min-w-0 flex-1">
                        <p className="text-sm font-medium text-zinc-800">{evento.descricao || evento.evento}</p>
                        <div className="mt-0.5 flex items-center gap-2">
                          <p className="text-xs text-zinc-400">{formatDatetime(evento.created_at)}</p>
                          {evento.created_by_nome && <span className="text-xs text-zinc-500">{evento.created_by_nome}</span>}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          )}
        </Card>
      </main>
    </Shell>
  )
}
