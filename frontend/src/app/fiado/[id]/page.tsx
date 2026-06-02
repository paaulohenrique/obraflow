"use client"

import Link from "next/link"
import { useParams } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import { ArrowLeft, Banknote, CheckCircle2, CreditCard, History, Package, Plus, User, XCircle } from "lucide-react"
import { useState } from "react"
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
  const [tab, setTab] = useState<Tab>("itens")
  const [itemDialogOpen, setItemDialogOpen] = useState(false)
  const [pagamentoDialogOpen, setPagamentoDialogOpen] = useState(false)

  const contaQuery = useQuery({
    queryKey: ["fiado", "contas", id],
    queryFn: () => fiadoService.get(id),
  })

  const itensQuery = useQuery({
    queryKey: ["fiado", "contas", id, "itens"],
    queryFn: () => fiadoService.itens(id, { page_size: 100 }),
    enabled: Boolean(contaQuery.data),
  })

  const pagamentosQuery = useQuery({
    queryKey: ["fiado", "contas", id, "pagamentos"],
    queryFn: () => fiadoService.pagamentos(id, { page_size: 100 }),
    enabled: Boolean(contaQuery.data),
  })

  const historicoQuery = useQuery({
    queryKey: ["fiado", "contas", id, "historico"],
    queryFn: () => fiadoService.historico(id, { page_size: 100 }),
    enabled: Boolean(contaQuery.data),
  })

  const conta = contaQuery.data

  if (contaQuery.isLoading) {
    return (
      <Shell>
        <Topbar title="Fiado" />
        <main className="flex-1 space-y-5 p-6">
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
  const contaAberta = conta.status === "ABERTA"

  return (
    <Shell>
      <FiadoItemDialog conta={conta} open={itemDialogOpen} onOpenChange={setItemDialogOpen} />
      <FiadoPagamentoDialog conta={conta} open={pagamentoDialogOpen} onOpenChange={setPagamentoDialogOpen} />

      <Topbar
        title={conta.cliente_nome}
        subtitle={`Fiado #${conta.id.slice(0, 8)} · Aberto em ${formatDate(conta.data_abertura)}`}
        actions={
          <div className="flex items-center gap-2">
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
            >
              Item
            </Button>
            <Link href="/fiado">
              <Button variant="ghost" size="sm" icon={<ArrowLeft className="size-3.5" />}>
                Voltar
              </Button>
            </Link>
          </div>
        }
      />

      <main className="flex-1 space-y-5 p-6">
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
          <Card>
            <CardContent className="space-y-3 py-5">
              <div className="flex items-center gap-3">
                <div className="flex size-10 flex-shrink-0 items-center justify-center rounded-full bg-orange-100">
                  <span className="text-sm font-bold text-orange-700">{initials(conta.cliente_nome)}</span>
                </div>
                <div>
                  <p className="text-sm font-semibold text-zinc-900">{conta.cliente_nome}</p>
                  <p className="text-xs text-zinc-500">{formatDocument(conta.cliente_cpf_cnpj)}</p>
                </div>
              </div>
              <div className="space-y-1.5 pt-1">
                <div className="flex items-center gap-2 text-xs text-zinc-600">
                  <User className="size-3.5 text-zinc-400" />
                  {conta.created_by_nome || "Sem usuário registrado"}
                </div>
                <div className="flex items-center gap-2 text-xs text-zinc-600">
                  <CreditCard className="size-3.5 text-zinc-400" />
                  Vencimento: {conta.data_vencimento ? formatDate(conta.data_vencimento) : "-"}
                </div>
              </div>
              <Badge variant={status.variant}>{status.label}</Badge>
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardContent className="py-5">
              <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
                <div>
                  <p className="mb-1 text-xs font-medium uppercase tracking-wide text-zinc-500">Total</p>
                  <p className="text-2xl font-semibold tabular-nums text-zinc-900">{formatCurrency(conta.valor_total)}</p>
                </div>
                <div>
                  <p className="mb-1 text-xs font-medium uppercase tracking-wide text-zinc-500">Pago</p>
                  <p className="text-2xl font-semibold tabular-nums text-green-600">{formatCurrency(conta.valor_pago)}</p>
                </div>
                <div>
                  <p className="mb-1 text-xs font-medium uppercase tracking-wide text-zinc-500">Restante</p>
                  <p className={cn("text-2xl font-semibold tabular-nums", toNumber(conta.valor_restante) > 0 ? "text-red-600" : "text-zinc-400")}>
                    {formatCurrency(conta.valor_restante)}
                  </p>
                </div>
              </div>

              <div className="mt-5">
                <div className="mb-1.5 flex justify-between text-xs text-zinc-500">
                  <span>Progresso do pagamento</span>
                  <span className="font-medium text-zinc-700">{pctPago}%</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-zinc-100">
                  <div className="h-full rounded-full bg-green-500 transition-all duration-500" style={{ width: `${Math.min(pctPago, 100)}%` }} />
                </div>
              </div>

              {conta.observacao && (
                <p className="mt-4 rounded-md border border-zinc-100 bg-zinc-50 px-3 py-2 text-xs text-zinc-500">
                  {conta.observacao}
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
