"use client"

import Link from "next/link"
import { useReducer, useState, useCallback, useMemo } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  AlertCircle,
  Banknote,
  CreditCard,
  Landmark,
  Package,
  ShoppingCart,
  Trash2,
  CheckCircle2,
  Download,
  Plus,
  Minus,
  QrCode,
  type LucideIcon,
} from "lucide-react"
import * as Dialog from "@radix-ui/react-dialog"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { StatCard } from "@/components/ui/stat-card"
import { Shell } from "@/components/layout/shell"
import { Topbar } from "@/components/layout/topbar"
import { useApiToast } from "@/hooks/use-api-toast"
import { formatNumber, toNumber } from "@/lib/format"
import { cn, formatCurrency } from "@/lib/utils"
import { financeiroService } from "@/services/financeiro.service"
import { vendasService } from "@/services/vendas.service"
import { ProdutoAutocomplete } from "@/features/fiado/produto-autocomplete"
import { estoqueService } from "@/services/estoque.service"
import { normalizeApiError } from "@/services/api"
import type {
  CartItem,
  CriarVendaPayload,
  FormaPagamentoPDV,
  FormaVendaProduto,
  Produto,
  Venda,
} from "@/types"


// ─── Helpers de formatação ────────────────────────────────────────────────────

function formatQtd(qty: number, unit: string): string {
  // Remove zeros desnecessários: 4,000 → "4", 4,500 → "4,5", 4,567 → "4,567"
  const raw = formatNumber(qty, 3)
  const stripped = raw.replace(/,?0+$/, "")
  return `${stripped} ${unit.toLowerCase()}`
}

// ─── Carrinho (reducer) ────────────────────────────────────────────────────────

type CartAction =
  | { type: "ADD"; item: CartItem }
  | { type: "REMOVE"; cartId: string }
  | { type: "UPDATE_QTY"; cartId: string; delta: number }
  | { type: "CLEAR" }

function cartReducer(state: CartItem[], action: CartAction): CartItem[] {
  switch (action.type) {
    case "ADD":
      return [...state, action.item]
    case "REMOVE":
      return state.filter((i) => i.cartId !== action.cartId)
    case "UPDATE_QTY": {
      return state
        .map((i) => {
          if (i.cartId !== action.cartId) return i
          const novaQtd = Math.max(0.001, i.quantidadeInformada + action.delta)
          const novaQtdConvertida = i.formaVenda
            ? novaQtd * toNumber(i.formaVenda.fator_conversao)
            : novaQtd
          return {
            ...i,
            quantidadeInformada: novaQtd,
            quantidade: novaQtdConvertida,
            subtotal: novaQtd * i.precoUnitario,
          }
        })
    }
    case "CLEAR":
      return []
    default:
      return state
  }
}

// ─── Constantes ───────────────────────────────────────────────────────────────

const FORMAS: { value: FormaPagamentoPDV; label: string; icon: LucideIcon }[] = [
  { value: "PIX", label: "PIX", icon: QrCode },
  { value: "DINHEIRO", label: "Dinheiro", icon: Banknote },
  { value: "CARTAO", label: "Cartão", icon: CreditCard },
  { value: "TRANSFERENCIA", label: "Transf.", icon: Landmark },
]

// ─── Dialog de sucesso ─────────────────────────────────────────────────────────

interface VendaSucessoDialogProps {
  venda: Venda
  onNova: () => void
  onDownload: () => void
}

function VendaSucessoDialog({ venda, onNova, onDownload }: VendaSucessoDialogProps) {
  return (
    <Dialog.Root open>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px]" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 z-50 w-full max-w-sm -translate-x-1/2 -translate-y-1/2 rounded-xl border border-zinc-200 bg-white p-6 shadow-xl focus:outline-none text-center"
          aria-describedby={undefined}
        >
          <div className="flex justify-center mb-4">
            <div className="flex size-14 items-center justify-center rounded-full bg-green-50 border border-green-200">
              <CheckCircle2 className="size-7 text-green-600" />
            </div>
          </div>
          <Dialog.Title className="text-base font-semibold text-zinc-900">
            Venda concluída!
          </Dialog.Title>
          <p className="mt-1 text-xs text-zinc-500">
            Número <span className="font-mono font-semibold text-zinc-700">{venda.numero}</span>
          </p>
          <div className="mt-4 rounded-lg bg-zinc-50 border border-zinc-100 px-4 py-3">
            <p className="text-2xl font-bold text-zinc-900">{formatCurrency(venda.valor_total)}</p>
            <p className="text-xs text-zinc-500 mt-0.5">
              {FORMAS.find((f) => f.value === venda.forma_pagamento)?.label ?? venda.forma_pagamento}
            </p>
          </div>
          <div className="mt-5 flex flex-col gap-2">
            <Button size="sm" variant="outline" icon={<Download className="size-3.5" />} onClick={onDownload}>
              Baixar comprovante PDF
            </Button>
            <Button size="sm" onClick={onNova}>
              Nova venda
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

// ─── Página principal ─────────────────────────────────────────────────────────

export default function PdvPage() {
  const queryClient = useQueryClient()
  const toast = useApiToast()

  // Estado do carrinho
  const [cart, dispatch] = useReducer(cartReducer, [])
  const [vendaConcluida, setVendaConcluida] = useState<Venda | null>(null)

  // Produto selecionado no autocomplete
  const [selectedProduto, setSelectedProduto] = useState<Produto | null>(null)
  const [selectedForma, setSelectedForma] = useState<FormaVendaProduto | null>(null)
  const [quantidade, setQuantidade] = useState<number>(1)
  const [preco, setPreco] = useState<number>(0)

  // Pagamento
  const [formaPagamento, setFormaPagamento] = useState<FormaPagamentoPDV>("PIX")
  const [desconto, setDesconto] = useState<number>(0)

  // Formas de venda do produto selecionado
  const formasQuery = useQuery({
    queryKey: ["estoque", "formas-venda", selectedProduto?.id],
    queryFn: () => estoqueService.formasVenda({ produto: selectedProduto!.id, page_size: 100 }),
    enabled: Boolean(selectedProduto),
    staleTime: 30_000,
  })
  const formasVenda = useMemo(
    () => (formasQuery.data?.results ?? []).filter((f) => f.ativo && f.is_active),
    [formasQuery.data?.results]
  )
  const formaOperacional = selectedForma ?? formasVenda.find((forma) => forma.padrao) ?? formasVenda[0] ?? null
  const formaOperacionalPreco = toNumber(formaOperacional?.preco_venda)
  const precoOperacional = !selectedForma && formaOperacionalPreco > 0 ? formaOperacionalPreco : preco

  const configFinanceiraQuery = useQuery({
    queryKey: ["financeiro", "configuracao-operacional"],
    queryFn: financeiroService.configuracaoOperacional,
    staleTime: 60_000,
  })
  const destinoPdv = configFinanceiraQuery.data?.destinos_pdv.find(
    (destino) => destino.forma_pagamento === formaPagamento
  )
  const contaFinanceira = destinoPdv?.conta ?? ""

  // Dashboard de vendas do dia
  const dashQuery = useQuery({
    queryKey: ["vendas", "dashboard"],
    queryFn: vendasService.dashboard,
    staleTime: 30_000,
  })

  // Cálculos do carrinho
  const subtotal = cart.reduce((acc, i) => acc + i.subtotal, 0)
  const descontoVal = Math.min(desconto, subtotal)
  const total = subtotal - descontoVal

  // Estoque disponível para o produto selecionado
  const estoqueAtual = selectedProduto ? toNumber(selectedProduto.estoque_atual) : 0
  const quantidadeConvertida = formaOperacional
    ? quantidade * toNumber(formaOperacional.fator_conversao)
    : quantidade
  const estoqueInsuficiente = selectedProduto != null && quantidadeConvertida > estoqueAtual

  // Quando seleciona produto, reseta estado de item
  const handleProdutoSelect = useCallback((p: Produto) => {
    setSelectedProduto(p)
    setSelectedForma(null)
    setQuantidade(1)
    setPreco(toNumber(p.preco_venda))
  }, [])

  const handleProdutoClear = useCallback(() => {
    setSelectedProduto(null)
    setSelectedForma(null)
    setQuantidade(1)
    setPreco(0)
  }, [])

  const handleFormaSelect = useCallback((forma: FormaVendaProduto) => {
    setSelectedForma(forma)
    const formaPreco = toNumber(forma.preco_venda)
    if (formaPreco > 0) setPreco(formaPreco)
  }, [])

  const criarFormaMutation = useMutation({
    mutationFn: (produtoId: string) => estoqueService.garantirFormaVenda(produtoId),
    onSuccess: (forma) => {
      queryClient.invalidateQueries({ queryKey: ["estoque", "formas-venda", forma.produto_id] })
      queryClient.invalidateQueries({ queryKey: ["estoque"] })
      handleFormaSelect(forma)
      toast.success("Forma de venda criada")
    },
    onError: (error) => toast.error(error),
  })

  // Adicionar item ao carrinho
  const handleAdicionarItem = () => {
    if (!selectedProduto || !formaOperacional || estoqueInsuficiente) return
    const cartId = crypto.randomUUID()
    const item: CartItem = {
      cartId,
      produto: selectedProduto,
      formaVenda: formaOperacional,
      quantidadeInformada: quantidade,
      quantidade: quantidadeConvertida,
      precoUnitario: precoOperacional,
      subtotal: quantidade * precoOperacional,
    }
    dispatch({ type: "ADD", item })
    setSelectedProduto(null)
    setSelectedForma(null)
    setQuantidade(1)
    setPreco(0)
  }

  // Finalizar venda
  const mutation = useMutation({
    mutationFn: (payload: CriarVendaPayload) => vendasService.criar(payload),
    onSuccess: (venda) => {
      queryClient.invalidateQueries({ queryKey: ["vendas"] })
      queryClient.invalidateQueries({ queryKey: ["financeiro"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
      queryClient.invalidateQueries({ queryKey: ["estoque"] })
      setVendaConcluida(venda)
    },
    onError: (error) => {
      const apiError = normalizeApiError(error)
      const msg = apiError.errors
        ? Object.values(apiError.errors).flat().join(" · ")
        : apiError.message
      toast.error(msg || "Erro ao finalizar venda.")
    },
  })

  const handleFinalizarVenda = () => {
    if (cart.length === 0) return
    if (!contaFinanceira) {
      toast.error("Defina a conta de destino em Configurações Financeiras.")
      return
    }
    const payload: CriarVendaPayload = {
      itens: cart.map((item) => ({
        produto: item.produto.id,
        forma_venda: item.formaVenda?.id ?? null,
        quantidade_informada: item.quantidadeInformada.toFixed(3),
        preco_unitario: item.precoUnitario.toFixed(2),
      })),
      forma_pagamento: formaPagamento,
      conta_financeira: contaFinanceira,
      desconto: descontoVal.toFixed(2),
      observacao: "",
    }
    mutation.mutate(payload)
  }

  const handleNovaVenda = () => {
    dispatch({ type: "CLEAR" })
    setVendaConcluida(null)
    setDesconto(0)
    setFormaPagamento("PIX")
  }

  const handleDownloadPdf = () => {
    if (!vendaConcluida) return
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"
    window.open(`${base}${vendasService.pdfUrl(vendaConcluida.id)}`, "_blank")
  }

  return (
    <Shell>
      <Topbar title="PDV" subtitle="Venda direta no balcão" />

      {vendaConcluida && (
        <VendaSucessoDialog
          venda={vendaConcluida}
          onNova={handleNovaVenda}
          onDownload={handleDownloadPdf}
        />
      )}

      <main className="flex-1 p-4 md:p-6 space-y-4">
        {/* KPIs do dia */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Vendas hoje" value={`${dashQuery.data?.count_hoje ?? 0}`} />
          <StatCard label="Faturado hoje" value={formatCurrency(dashQuery.data?.total_hoje)} accent />
          <StatCard label="Vendas no mês" value={`${dashQuery.data?.count_mes ?? 0}`} />
          <StatCard label="Ticket médio" value={formatCurrency(dashQuery.data?.ticket_medio)} />
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_360px]">

          {/* ─── Painel esquerdo: busca de produto ─── */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Package className="size-4 text-zinc-400" />
                <h3 className="text-sm font-semibold text-zinc-900">Adicionar Produto</h3>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Busca */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-600">Produto</label>
                <ProdutoAutocomplete
                  value={selectedProduto}
                  onSelect={handleProdutoSelect}
                  onClear={handleProdutoClear}
                />
              </div>

              {/* Formas de venda */}
              {selectedProduto && (
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-zinc-600">Forma de venda</label>
                  {formasQuery.isLoading ? (
                    <div className="h-14 animate-pulse rounded-md bg-zinc-100" />
                  ) : formasVenda.length === 0 ? (
                    <div className="rounded-md border border-yellow-200 bg-yellow-50 px-3 py-3 text-xs text-yellow-900">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span>Este produto ainda não possui forma de venda.</span>
                        <Button
                          type="button"
                          size="xs"
                          variant="outline"
                          loading={criarFormaMutation.isPending}
                          disabled={criarFormaMutation.isPending}
                          onClick={() => criarFormaMutation.mutate(selectedProduto.id)}
                        >
                          Criar agora
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
                      {formasVenda.map((forma) => {
                        const sel = (selectedForma?.id ?? formaOperacional?.id) === forma.id
                        return (
                          <button
                            key={forma.id}
                            type="button"
                            onClick={() => handleFormaSelect(forma)}
                            className={cn(
                              "rounded-md border px-3 py-2 text-left text-xs transition-colors",
                              sel
                                ? "border-orange-300 bg-orange-50 ring-1 ring-orange-100"
                                : "border-zinc-200 hover:border-zinc-300 hover:bg-zinc-50"
                            )}
                          >
                            <span className="block font-semibold text-zinc-900">{forma.nome}</span>
                            <span className="mt-0.5 block text-[11px] text-zinc-500">
                              1 {forma.unidade.toLowerCase()} baixa{" "}
                              {formatNumber(forma.fator_conversao, 3).replace(/,?0+$/, "")}{" "}
                              {selectedProduto.unidade_sigla.toLowerCase()}
                            </span>
                            {toNumber(forma.preco_venda) > 0 && (
                              <span className="mt-0.5 block text-[11px] font-medium text-zinc-700 tabular-nums">
                                {formatCurrency(forma.preco_venda)}
                              </span>
                            )}
                          </button>
                        )
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* Quantidade e preço */}
              {selectedProduto && (
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-zinc-600">Quantidade</label>
                    <Input
                      type="number"
                      step="0.001"
                      min="0.001"
                      value={quantidade}
                      onChange={(e) => setQuantidade(Number(e.target.value))}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-zinc-600">
                      Preço / {formaOperacional?.unidade ?? selectedProduto.unidade_sigla}
                    </label>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      value={precoOperacional}
                      onChange={(e) => {
                        if (!selectedForma && formaOperacional) setSelectedForma(formaOperacional)
                        setPreco(Number(e.target.value))
                      }}
                    />
                  </div>
                </div>
              )}

              {/* Preview de conversão e estoque */}
              {selectedProduto && formaOperacional && (
                <div className={cn(
                  "rounded-lg border px-3 py-2.5 text-xs",
                  estoqueInsuficiente
                    ? "border-red-200 bg-red-50 text-red-800"
                    : "border-zinc-100 bg-zinc-50 text-zinc-600"
                )}>
                  <div className="space-y-1">
                    <p>
                      {formatQtd(quantidade, formaOperacional.unidade)} baixa{quantidade !== 1 ? "m" : ""}{" "}
                      <strong className="text-zinc-900">
                        {formatQtd(quantidadeConvertida, selectedProduto.unidade_sigla)}
                      </strong>{" "}
                      do estoque
                    </p>
                    {estoqueInsuficiente ? (
                      <p className="font-medium text-red-700">
                        Você precisa de {formatNumber(quantidadeConvertida, 3)} {selectedProduto.unidade_sigla}.{" "}
                        Disponível: {formatNumber(estoqueAtual, 3)} {selectedProduto.unidade_sigla}.{" "}
                        Faltam: {formatNumber(quantidadeConvertida - estoqueAtual, 3)} {selectedProduto.unidade_sigla}.
                      </p>
                    ) : (
                      <p>
                        Disponível:{" "}
                        <strong className="text-zinc-900">
                          {formatNumber(estoqueAtual, 3)} {selectedProduto.unidade_sigla}
                        </strong>
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* Subtotal do item */}
              {selectedProduto && (
                <div className="flex items-center justify-between rounded-lg border border-zinc-100 bg-zinc-50 px-3 py-2 text-xs">
                  <span className="text-zinc-500">Subtotal do item</span>
                  <span className="font-semibold text-zinc-900 tabular-nums">
                    {formatCurrency(quantidade * precoOperacional)}
                  </span>
                </div>
              )}

              <Button
                size="sm"
                icon={<Plus className="size-3.5" />}
                disabled={!selectedProduto || !formaOperacional || estoqueInsuficiente || precoOperacional <= 0}
                onClick={handleAdicionarItem}
                className="w-full"
              >
                Adicionar ao carrinho
              </Button>
            </CardContent>
          </Card>

          {/* ─── Painel direito: carrinho + checkout ─── */}
          <div className="flex flex-col gap-4">
            {/* Carrinho */}
            <Card className="flex-1">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <ShoppingCart className="size-4 text-zinc-400" />
                    <h3 className="text-sm font-semibold text-zinc-900">Carrinho</h3>
                  </div>
                  <Badge variant="outline">{cart.length} {cart.length === 1 ? "item" : "itens"}</Badge>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                {cart.length === 0 ? (
                  <div className="flex flex-col items-center py-10 text-center">
                    <ShoppingCart className="size-8 text-zinc-200 mb-2" />
                    <p className="text-xs text-zinc-400">Carrinho vazio.</p>
                    <p className="text-xs text-zinc-300">Busque um produto acima.</p>
                  </div>
                ) : (
                  <div className="divide-y divide-zinc-100">
                    {cart.map((item) => (
                      <div key={item.cartId} className="flex items-start gap-3 px-4 py-3">
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-medium text-zinc-900 truncate">
                            {formatQtd(
                              item.quantidadeInformada,
                              item.formaVenda?.unidade ?? item.produto.unidade_sigla
                            )}{" "}
                            <span className="font-normal text-zinc-500">de</span>{" "}
                            {item.produto.nome}
                          </p>
                          <p className="text-[11px] text-zinc-400">
                            {formatCurrency(item.precoUnitario)}/{(item.formaVenda?.unidade ?? item.produto.unidade_sigla).toLowerCase()}
                          </p>
                        </div>
                        <div className="flex items-center gap-1">
                          <button
                            type="button"
                            onClick={() => dispatch({ type: "UPDATE_QTY", cartId: item.cartId, delta: -1 })}
                            className="flex size-5 items-center justify-center rounded border border-zinc-200 text-zinc-400 hover:border-zinc-300 hover:text-zinc-700"
                          >
                            <Minus className="size-2.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => dispatch({ type: "UPDATE_QTY", cartId: item.cartId, delta: 1 })}
                            className="flex size-5 items-center justify-center rounded border border-zinc-200 text-zinc-400 hover:border-zinc-300 hover:text-zinc-700"
                          >
                            <Plus className="size-2.5" />
                          </button>
                        </div>
                        <span className="tabular-nums text-xs font-semibold text-zinc-800 w-16 text-right shrink-0">
                          {formatCurrency(item.subtotal)}
                        </span>
                        <button
                          type="button"
                          onClick={() => dispatch({ type: "REMOVE", cartId: item.cartId })}
                          className="text-zinc-300 hover:text-red-500 transition-colors"
                        >
                          <Trash2 className="size-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Checkout */}
            {cart.length > 0 && (
              <Card>
                <CardContent className="space-y-4 pt-4">
                  {/* Forma de pagamento */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-zinc-600">Forma de pagamento</label>
                    <div className="grid grid-cols-4 gap-1">
                      {FORMAS.map(({ value, label, icon: Icon }) => (
                        <button
                          key={value}
                          type="button"
                          onClick={() => setFormaPagamento(value)}
                          className={cn(
                            "rounded-md border py-2 text-xs font-medium transition-colors",
                            formaPagamento === value
                              ? "border-orange-300 bg-orange-50 text-orange-700 ring-1 ring-orange-100"
                              : "border-zinc-200 text-zinc-600 hover:border-zinc-300 hover:bg-zinc-50"
                          )}
                        >
                          <Icon className="mx-auto mb-1 size-3.5" />
                          {label}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-zinc-600">Destino</label>
                    {configFinanceiraQuery.isLoading ? (
                      <div className="h-9 animate-pulse rounded-md bg-zinc-100" />
                    ) : contaFinanceira ? (
                      <div className="rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm font-semibold text-zinc-900">
                        {destinoPdv?.conta_nome}
                        {!destinoPdv?.configurada && (
                          <span className="ml-2 text-[11px] font-medium text-zinc-500">sugerida</span>
                        )}
                      </div>
                    ) : (
                      <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                        <div className="flex items-start gap-2">
                          <AlertCircle className="mt-0.5 size-3.5 shrink-0" />
                          <div>
                            <p className="font-medium">Nenhuma conta ativa para {formaPagamento}.</p>
                            <Link className="underline" href="/configuracoes/financeiro">
                              Abrir Configurações Financeiras
                            </Link>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Desconto */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-zinc-600">Desconto <span className="text-zinc-400">(opcional)</span></label>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      max={subtotal}
                      placeholder="0,00"
                      value={desconto || ""}
                      onChange={(e) => setDesconto(Number(e.target.value))}
                    />
                  </div>

                  {/* Totais */}
                  <div className="space-y-1 border-t border-zinc-100 pt-3">
                    <div className="flex justify-between text-xs text-zinc-500">
                      <span>Subtotal</span>
                      <span className="tabular-nums">{formatCurrency(subtotal)}</span>
                    </div>
                    {descontoVal > 0 && (
                      <div className="flex justify-between text-xs text-zinc-500">
                        <span>Desconto</span>
                        <span className="tabular-nums text-orange-600">− {formatCurrency(descontoVal)}</span>
                      </div>
                    )}
                    <div className="flex justify-between text-sm font-bold text-zinc-900 pt-1">
                      <span>Total</span>
                      <span className="tabular-nums">{formatCurrency(total)}</span>
                    </div>
                  </div>

                  <Button
                    size="md"
                    loading={mutation.isPending}
                    disabled={!contaFinanceira || total <= 0}
                    onClick={handleFinalizarVenda}
                    className="w-full"
                  >
                    Finalizar Venda — {formatCurrency(total)}
                  </Button>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </main>
    </Shell>
  )
}
