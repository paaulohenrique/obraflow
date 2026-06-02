"use client"

import * as Dialog from "@radix-ui/react-dialog"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  CornerDownRight,
  FileCode,
  History,
  Sparkles,
  Trash2,
  X,
  XCircle,
} from "lucide-react"
import { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useApiToast } from "@/hooks/use-api-toast"
import { fornecedorDisplayName } from "@/lib/estoque"
import { cn, formatCurrency, formatDate, formatDatetime, formatDocument } from "@/lib/utils"
import { formatNumber, statusLabel } from "@/lib/format"
import { notasEntradaService } from "@/services/notas-entrada.service"
import { estoqueService } from "@/services/estoque.service"
import { financeiroService } from "@/services/financeiro.service"
import { ProdutoAutocomplete } from "@/features/fiado/produto-autocomplete"
import type { NotaItem, ProductSuggestion, Produto } from "@/types"

interface NotaReviewDrawerProps {
  notaId: string | null
  initialHistoryOpen?: boolean
  onClose: () => void
}

export function NotaReviewDrawer({ notaId, initialHistoryOpen = false, onClose }: NotaReviewDrawerProps) {
  const queryClient = useQueryClient()
  const toast = useApiToast()
  const [confirming, setConfirming] = useState(false)
  const [rejecting, setRejecting] = useState(false)
  const [motivoRejeicao, setMotivoRejeicao] = useState("")
  const [showHistory, setShowHistory] = useState(initialHistoryOpen)

  // Payable settings on confirmation
  const [criarContaPagar, setCriarContaPagar] = useState(false)
  const [categoriaPagar, setCategoriaPagar] = useState("")
  const [vencimentoPagar, setVencimentoPagar] = useState("")
  const [obsPagar, setObsPagar] = useState("")

  // Supplier link state
  const [fornecedorSelecionado, setFornecedorSelecionado] = useState("")

  const open = Boolean(notaId)

  // Fetch full details of the XML invoice including items
  const notaQuery = useQuery({
    queryKey: ["notas-entrada", notaId],
    queryFn: () => notasEntradaService.get(notaId!),
    enabled: open && Boolean(notaId),
    staleTime: 5000,
  })

  // Fetch suppliers to allow manual linkage
  const fornecedoresQuery = useQuery({
    queryKey: ["estoque", "fornecedores"],
    queryFn: () => estoqueService.fornecedores({ page_size: 100 }),
    enabled: open,
    staleTime: 60000,
  })

  // Fetch financial categories for despesas
  const categoriasQuery = useQuery({
    queryKey: ["financeiro", "categorias", "despesas"],
    queryFn: () => financeiroService.categorias({ page_size: 100, tipo: "DESPESA" }),
    enabled: open && confirming,
    staleTime: 60000,
  })

  const historicoQuery = useQuery({
    queryKey: ["notas-entrada", notaId, "historico"],
    queryFn: () => notasEntradaService.historico(notaId!, { page_size: 20 }),
    enabled: open && showHistory && Boolean(notaId),
    staleTime: 15_000,
  })

  const vincularFornecedorMutation = useMutation({
    mutationFn: (fornecedorId: string) =>
      notasEntradaService.vincularFornecedor(notaId!, { fornecedor: fornecedorId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notas-entrada"] })
      toast.success("Fornecedor vinculado com sucesso!")
    },
    onError: (err) => toast.error(err),
  })

  const confirmarMutation = useMutation({
    mutationFn: () =>
      notasEntradaService.confirmar(notaId!, {
        criar_conta_pagar: criarContaPagar,
        dados_conta_pagar: criarContaPagar
          ? {
              categoria: categoriaPagar,
              data_vencimento: vencimentoPagar,
              observacao: obsPagar,
            }
          : null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notas-entrada"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
      queryClient.invalidateQueries({ queryKey: ["estoque"] })
      toast.success("Nota fiscal confirmada e estoque atualizado!")
      setConfirming(false)
      onClose()
    },
    onError: (err) => toast.error(err),
  })

  const rejeitarMutation = useMutation({
    mutationFn: () =>
      notasEntradaService.rejeitar(notaId!, { motivo: motivoRejeicao }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notas-entrada"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
      toast.success("Nota fiscal rejeitada.")
      setRejecting(false)
      onClose()
    },
    onError: (err) => toast.error(err),
  })

  const nota = notaQuery.data
  const fornecedores = fornecedoresQuery.data?.results ?? []
  const categorias = categoriasQuery.data?.results ?? []
  const [notaStateKey, setNotaStateKey] = useState("closed")
  const nextNotaStateKey = nota
    ? `${nota.id}:${nota.fornecedor ?? ""}:${initialHistoryOpen ? "history" : "review"}`
    : "closed"

  if (notaStateKey !== nextNotaStateKey) {
    setNotaStateKey(nextNotaStateKey)
    if (nota) {
      setFornecedorSelecionado(nota.fornecedor || "")
      setConfirming(false)
      setRejecting(false)
      setMotivoRejeicao("")
      setShowHistory(initialHistoryOpen)
    }
  }

  if (!open) return null

  return (
    <Dialog.Root open={open} onOpenChange={(v) => { if (!v) onClose() }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-zinc-950/20 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0" />
        <Dialog.Content
          className={cn(
            "fixed right-0 top-0 z-50 flex h-full w-full max-w-6xl flex-col bg-white shadow-2xl border-l border-zinc-150",
            "data-[state=open]:animate-in data-[state=closed]:animate-out",
            "data-[state=open]:slide-in-from-right data-[state=closed]:slide-out-to-right",
            "duration-200"
          )}
          aria-describedby={undefined}
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-zinc-100 px-6 py-4 bg-zinc-50/50">
            <div>
              <Dialog.Title className="text-sm font-semibold text-zinc-900 flex items-center gap-2">
                <FileCode className="size-4.5 text-zinc-500" />
                Conciliação de Nota Fiscal de Entrada
              </Dialog.Title>
              <p className="text-[11px] text-zinc-400 mt-0.5">Associe os itens da nota fiscal aos produtos do seu estoque e confirme a importação.</p>
            </div>
            <Dialog.Close asChild>
              <button
                className="rounded-md p-1.5 text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-700"
                aria-label="Fechar"
              >
                <X className="size-4.5" />
              </button>
            </Dialog.Close>
          </div>

          {notaQuery.isLoading ? (
            <div className="flex-1 grid grid-cols-3 divide-x divide-zinc-100 h-full">
              <div className="p-6 space-y-4">
                <Skeleton className="h-4 w-1/2" />
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-24 w-full" />
              </div>
              <div className="col-span-2 p-6 space-y-4">
                <Skeleton className="h-4 w-1/4" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
              </div>
            </div>
          ) : !nota ? (
            <div className="flex-1 flex flex-col items-center justify-center gap-3 p-6 text-center">
              <XCircle className="size-10 text-red-500" />
              <p className="text-sm font-medium text-zinc-750">Erro ao carregar detalhes da nota fiscal.</p>
              <Button variant="outline" size="sm" onClick={() => notaQuery.refetch()}>Tentar Novamente</Button>
            </div>
          ) : (
            <div className="flex-1 overflow-hidden grid grid-cols-1 lg:grid-cols-12 divide-y lg:divide-y-0 lg:divide-x divide-zinc-100">
              
              {/* Lado Esquerdo: Resumo do XML & Ações de Nota */}
              <div className="lg:col-span-4 overflow-y-auto p-6 space-y-6 bg-zinc-50/20">
                
                {/* Info Nota */}
                <div className="space-y-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">Nota Fiscal</h4>
                      <p className="text-xl font-bold text-zinc-950 font-mono">#{nota.numero} <span className="text-xs text-zinc-400 font-normal">Série {nota.serie}</span></p>
                    </div>
                    <Badge variant={nota.status === "CONFIRMADA" ? "success" : nota.status === "REJEITADA" ? "error" : "warning"} className="font-semibold">
                      {statusLabel(nota.status)}
                    </Badge>
                  </div>

                  <div className="rounded-lg border border-zinc-150 bg-white p-3 space-y-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-zinc-400 font-medium">Emissor XML</span>
                      <span className="font-semibold text-zinc-900 truncate max-w-[160px]" title={nota.fornecedor_nome_final}>
                        {nota.fornecedor_nome_final}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-400 font-medium">CNPJ Fornecedor</span>
                      <span className="font-mono text-zinc-650">{formatDocument(nota.fornecedor_cnpj_xml)}</span>
                    </div>
                    <div className="flex justify-between border-t border-zinc-100 pt-2 mt-1">
                      <span className="text-zinc-400 font-medium">Data Emissão</span>
                      <span className="text-zinc-700">{nota.data_emissao ? formatDate(nota.data_emissao) : "-"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-400 font-medium">Valor Total</span>
                      <span className="font-bold text-zinc-950 tabular-nums">{formatCurrency(nota.valor_total)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-400 font-medium">Total de Itens</span>
                      <span className="font-semibold text-zinc-900">{nota.itens_total} itens</span>
                    </div>
                    {nota.itens_sem_produto > 0 && (
                      <div className="flex justify-between text-red-650 bg-red-50/50 px-2 py-0.5 rounded border border-red-100">
                        <span className="font-medium">Itens sem vínculo</span>
                        <span className="font-bold">{nota.itens_sem_produto} pendentes</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Fornecedor linkage form */}
                <div className="space-y-2">
                  <h5 className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">Vincular a Fornecedor Cadastrado</h5>
                  <div className="flex gap-2">
                    <select
                      value={fornecedorSelecionado}
                      disabled={nota.status !== "AGUARDANDO_REVISAO" || vincularFornecedorMutation.isPending}
                      onChange={(e) => setFornecedorSelecionado(e.target.value)}
                      className="block w-full text-xs font-semibold h-9 rounded-md border border-zinc-300 bg-white px-2.5 focus:border-zinc-900 focus:outline-none"
                    >
                      <option value="">-- Selecione Fornecedor --</option>
                      {fornecedores.map((f) => (
                        <option key={f.id} value={f.id}>
                          {fornecedorDisplayName(f)} ({formatDocument(f.cnpj)})
                        </option>
                      ))}
                    </select>
                    {nota.status === "AGUARDANDO_REVISAO" && (
                      <Button
                        size="sm"
                        variant="outline"
                        loading={vincularFornecedorMutation.isPending}
                        disabled={!fornecedorSelecionado || fornecedorSelecionado === nota.fornecedor || vincularFornecedorMutation.isPending}
                        onClick={() => vincularFornecedorMutation.mutate(fornecedorSelecionado)}
                      >
                        Salvar
                      </Button>
                    )}
                  </div>
                </div>

                <div className="space-y-2 border-t border-zinc-150 pt-5">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="w-full justify-center"
                    icon={<History className="size-3.5" />}
                    onClick={() => setShowHistory((value) => !value)}
                  >
                    {showHistory ? "Ocultar Histórico" : "Ver Histórico"}
                  </Button>

                  {showHistory && (
                    <div className="max-h-64 overflow-y-auto rounded-lg border border-zinc-150 bg-white">
                      {historicoQuery.isLoading ? (
                        <div className="space-y-2 p-3">
                          <Skeleton className="h-9 w-full" />
                          <Skeleton className="h-9 w-full" />
                        </div>
                      ) : (historicoQuery.data?.results ?? []).length === 0 ? (
                        <div className="px-3 py-6 text-center text-[11px] text-zinc-400">
                          Nenhum evento registrado.
                        </div>
                      ) : (
                        <div className="divide-y divide-zinc-100">
                          {(historicoQuery.data?.results ?? []).map((evento) => (
                            <div key={evento.id} className="p-3 text-xs">
                              <div className="flex items-start justify-between gap-3">
                                <span className="font-bold text-zinc-900">{statusLabel(evento.evento)}</span>
                                <span className="shrink-0 text-[10px] text-zinc-400">
                                  {formatDatetime(evento.created_at)}
                                </span>
                              </div>
                              <p className="mt-1 leading-relaxed text-zinc-500">{evento.descricao}</p>
                              {evento.created_by_nome && (
                                <p className="mt-1 text-[10px] font-medium text-zinc-400">
                                  {evento.created_by_nome}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Confirm / Reject forms */}
                {nota.status === "AGUARDANDO_REVISAO" && (
                  <div className="border-t border-zinc-150 pt-5 space-y-4">
                    
                    {!confirming && !rejecting && (
                      <div className="grid grid-cols-2 gap-3">
                        <Button
                          variant="outline"
                          className="border-red-200 text-red-600 hover:bg-red-50"
                          onClick={() => setRejecting(true)}
                        >
                          Rejeitar Nota
                        </Button>
                        <Button
                          className="bg-orange-500 hover:bg-orange-600 text-white font-bold"
                          disabled={nota.itens_sem_produto > 0}
                          title={nota.itens_sem_produto > 0 ? "Vincule todos os itens para poder confirmar" : ""}
                          onClick={() => setConfirming(true)}
                        >
                          Confirmar Entrada
                        </Button>
                      </div>
                    )}

                    {nota.itens_sem_produto > 0 && !confirming && !rejecting && (
                      <p className="text-[10px] text-center text-zinc-450 leading-relaxed">
                        ⚠️ Você precisa vincular todos os <strong>{nota.itens_sem_produto} itens pendentes</strong> do XML aos produtos correspondentes antes de liberar a entrada de estoque.
                      </p>
                    )}

                    {/* Reject Form */}
                    {rejecting && (
                      <div className="rounded-lg border border-red-200 bg-red-50/30 p-4 space-y-3">
                        <div className="flex justify-between items-center">
                          <h6 className="text-xs font-bold text-red-900">Rejeitar Nota Fiscal</h6>
                          <button onClick={() => setRejecting(false)} className="text-zinc-400 hover:text-zinc-650">
                            <X className="size-4" />
                          </button>
                        </div>
                        <div className="space-y-1">
                          <label className="text-[10px] font-bold text-zinc-500 uppercase">Motivo da Rejeição</label>
                          <textarea
                            value={motivoRejeicao}
                            onChange={(e) => setMotivoRejeicao(e.target.value)}
                            placeholder="Descreva o motivo da rejeição comercial ou erro no XML..."
                            rows={3}
                            className="block w-full text-xs rounded-md border border-zinc-300 p-2 focus:border-zinc-900 focus:outline-none"
                          />
                        </div>
                        <Button
                          className="w-full bg-red-600 hover:bg-red-700 text-white font-bold"
                          size="sm"
                          loading={rejeitarMutation.isPending}
                          disabled={!motivoRejeicao.trim() || rejeitarMutation.isPending}
                          onClick={() => rejeitarMutation.mutate()}
                        >
                          Confirmar Rejeição
                        </Button>
                      </div>
                    )}

                    {/* Confirm Form */}
                    {confirming && (
                      <div className="rounded-lg border border-zinc-200 bg-white p-4 space-y-4">
                        <div className="flex justify-between items-center">
                          <h6 className="text-xs font-bold text-zinc-950">Configurações de Lançamento</h6>
                          <button onClick={() => setConfirming(false)} className="text-zinc-400 hover:text-zinc-650">
                            <X className="size-4" />
                          </button>
                        </div>

                        {/* Payables options */}
                        <div className="space-y-3">
                          <label className="flex items-center gap-2 cursor-pointer select-none">
                            <input
                              type="checkbox"
                              checked={criarContaPagar}
                              onChange={(e) => {
                                setCriarContaPagar(e.target.checked)
                                if (e.target.checked && !vencimentoPagar) {
                                  const d = new Date()
                                  d.setDate(d.getDate() + 30)
                                  setVencimentoPagar(d.toISOString().split("T")[0])
                                }
                              }}
                              className="rounded border-zinc-300 text-orange-500 focus:ring-orange-500/20"
                            />
                            <span className="text-xs font-bold text-zinc-700">Lançar no contas a pagar?</span>
                          </label>

                          {criarContaPagar && (
                            <div className="space-y-3 border-l-2 border-zinc-200 pl-3 pt-1">
                              <div className="space-y-1">
                                <label className="text-[10px] font-bold text-zinc-500 uppercase">Categoria Financeira</label>
                                <select
                                  value={categoriaPagar}
                                  onChange={(e) => setCategoriaPagar(e.target.value)}
                                  className="block w-full text-xs font-semibold h-8 rounded-md border border-zinc-300 bg-white px-2 focus:border-zinc-900 focus:outline-none"
                                >
                                  <option value="">-- Selecione a Despesa --</option>
                                  {categorias.map((c) => (
                                    <option key={c.id} value={c.id}>
                                      {c.nome}
                                    </option>
                                  ))}
                                </select>
                              </div>

                              <div className="space-y-1">
                                <label className="text-[10px] font-bold text-zinc-500 uppercase">Data de Vencimento</label>
                                <input
                                  type="date"
                                  value={vencimentoPagar}
                                  onChange={(e) => setVencimentoPagar(e.target.value)}
                                  className="block w-full text-xs font-semibold h-8 rounded-md border border-zinc-300 px-2 focus:border-zinc-900 focus:outline-none"
                                />
                              </div>

                              <div className="space-y-1">
                                <label className="text-[10px] font-bold text-zinc-500 uppercase">Observações do Título</label>
                                <input
                                  type="text"
                                  value={obsPagar}
                                  onChange={(e) => setObsPagar(e.target.value)}
                                  placeholder="Ex: Compra de materiais de construção..."
                                  className="block w-full text-xs h-8 rounded-md border border-zinc-300 px-2 focus:border-zinc-900 focus:outline-none"
                                />
                              </div>
                            </div>
                          )}
                        </div>

                        <Button
                          className="w-full bg-orange-500 hover:bg-orange-600 text-white font-bold"
                          size="sm"
                          loading={confirmarMutation.isPending}
                          disabled={criarContaPagar && (!categoriaPagar || !vencimentoPagar) || confirmarMutation.isPending}
                          onClick={() => confirmarMutation.mutate()}
                        >
                          Confirmar Lançamento
                        </Button>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Lado Direito: Itens do XML & Conciliação */}
              <div className="lg:col-span-8 flex flex-col h-full overflow-hidden">
                <div className="px-6 py-4 border-b border-zinc-100 flex items-center justify-between flex-shrink-0">
                  <h4 className="text-xs font-bold text-zinc-900 uppercase tracking-wider">Itens do XML da Nota</h4>
                  <Badge variant="outline">{nota.itens.length} itens no XML</Badge>
                </div>

                <div className="flex-1 overflow-y-auto divide-y divide-zinc-100 p-1">
                  {nota.itens.map((item) => (
                    <XMLItemRow
                      key={item.id}
                      item={item}
                      notaId={nota.id}
                      statusNota={nota.status}
                      onUpdated={() => notaQuery.refetch()}
                    />
                  ))}
                </div>
              </div>

            </div>
          )}

        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

/* Individual Item Conciliation Component */
function XMLItemRow({
  item,
  notaId,
  statusNota,
  onUpdated,
}: {
  item: NotaItem
  notaId: string
  statusNota: string
  onUpdated: () => void
}) {
  const toast = useApiToast()
  const [expanded, setExpanded] = useState(false)
  const [editing, setEditing] = useState(false)
  
  // Custom states for manual bindings
  const [selectedProduct, setSelectedProduct] = useState<ProductSuggestion | Produto | null>(null)
  const [selectedForma, setSelectedForma] = useState<string>("")
  const [custoUnitario, setCustoUnitario] = useState<string>("")

  // Fetch product suggestions for this item via Trigram similarity
  const suggestionsQuery = useQuery({
    queryKey: ["notas-entrada", notaId, "itens", item.id, "sugestoes"],
    queryFn: () => notasEntradaService.sugestoes(notaId, item.id),
    enabled: expanded && !item.produto && !item.ignorado,
    staleTime: 60000,
  })

  // Fetch conversion factor rules for the selected product
  const formasVendaQuery = useQuery({
    queryKey: ["estoque", "formas-venda", selectedProduct?.id],
    queryFn: () => estoqueService.formasVenda({ produto: selectedProduct?.id, page_size: 100 }),
    enabled: !!selectedProduct?.id,
    staleTime: 30000,
  })

  const linkItemMutation = useMutation({
    mutationFn: (payload: {
      produto?: string | null
      forma_venda?: string | null
      custo_unitario?: number | string | null
      ignorado?: boolean
    }) => notasEntradaService.vincularItem(notaId, item.id, payload),
    onSuccess: () => {
      onUpdated()
      toast.success("Vínculo do item atualizado!")
      setEditing(false)
      setSelectedProduct(null)
      setSelectedForma("")
      setCustoUnitario("")
    },
    onError: (err) => toast.error(err),
  })

  const suggestions = suggestionsQuery.data ?? []
  const formasVenda = (formasVendaQuery.data?.results ?? []).filter((forma) => forma.ativo)
  const selectedFormaObj = formasVenda.find((forma) => forma.id === selectedForma) ?? null
  const requiresForma = Boolean(selectedProduct && formasVenda.length > 1)
  const quantidadeConvertidaPreview = selectedFormaObj
    ? Number(item.quantidade) * Number(selectedFormaObj.fator_conversao)
    : Number(item.quantidade)
  const canApplyLink = Boolean(selectedProduct && (!requiresForma || selectedForma))

  // Initialize linkage inputs on edit mode open
  const startEditing = () => {
    setEditing(true)
    setCustoUnitario(item.custo_unitario ? item.custo_unitario.toString() : item.valor_unitario.toString())
  }

  const handleApplyLink = () => {
    if (!canApplyLink || !selectedProduct) return
    linkItemMutation.mutate({
      produto: selectedProduct.id,
      forma_venda: selectedForma || null,
      custo_unitario: custoUnitario || null,
      ignorado: false,
    })
  }

  const handleIgnore = () => {
    linkItemMutation.mutate({
      ignorado: true,
      produto: null,
      forma_venda: null,
    })
  }

  const handleRestore = () => {
    linkItemMutation.mutate({
      ignorado: false,
      produto: null,
      forma_venda: null,
    })
  }

  const isRevisavel = statusNota === "AGUARDANDO_REVISAO"

  return (
    <div className={cn(
      "p-4 transition-colors",
      expanded ? "bg-zinc-50/50" : "hover:bg-zinc-50/30"
    )}>
      {/* Resumo da Linha */}
      <div className="flex items-start justify-between gap-4 cursor-pointer select-none" onClick={() => setExpanded(!expanded)}>
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] font-bold text-zinc-450 bg-zinc-100 px-1.5 py-0.2 rounded">
              #{item.ordem}
            </span>
            <span className="text-xs font-bold text-zinc-900 leading-snug">{item.descricao_original}</span>
          </div>

          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-zinc-400">
            <span>Cod XML: {item.codigo_fornecedor || "-"}</span>
            {item.codigo_barras && (
              <span className="font-mono">EAN: {item.codigo_barras}</span>
            )}
            <span>NCM: {item.ncm}</span>
            <span>CFOP: {item.cfop}</span>
            <span>•</span>
            <span className="font-semibold text-zinc-500">
              Qtd XML: {formatNumber(item.quantidade, 2)} {item.unidade} x {formatCurrency(item.valor_unitario)}
            </span>
            <span className="font-bold text-zinc-800 tabular-nums">
              Total: {formatCurrency(item.valor_total_item)}
            </span>
          </div>
        </div>

        {/* Badge Vínculo */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {item.ignorado ? (
            <Badge variant="outline" className="bg-zinc-100 text-zinc-500 font-semibold border-zinc-200">IGNORADO</Badge>
          ) : item.produto ? (
            <div className="text-right">
              <Badge variant="success" className="font-bold flex items-center gap-1">
                <Check className="size-3" />
                VINCULADO
              </Badge>
              <span className="text-[10px] text-zinc-500 font-semibold block mt-0.5 max-w-[140px] truncate" title={item.produto_nome || ""}>
                {item.produto_nome}
              </span>
            </div>
          ) : (
            <Badge variant="error" className="font-bold animate-pulse">PENDENTE</Badge>
          )}

          {expanded ? <ChevronUp className="size-4 text-zinc-400" /> : <ChevronDown className="size-4 text-zinc-400" />}
        </div>
      </div>

      {/* Detalhes de Expansão (Mapeamento) */}
      {expanded && (
        <div className="mt-4 border-t border-zinc-100 pt-4 space-y-4">
          
          {/* Item is linked */}
          {item.produto && !editing && (
            <div className="bg-green-50/30 border border-green-100 rounded-lg p-3 flex flex-wrap justify-between items-center gap-3">
              <div className="text-xs space-y-1">
                <p className="font-semibold text-green-900 flex items-center gap-1.5">
                  <CheckCircle2 className="size-3.5 text-green-500" />
                  Mapeado para: <strong className="text-zinc-900">{item.produto_nome}</strong>
                </p>
                {item.forma_venda_nome && (
                  <p className="text-zinc-500 text-[10px] flex items-center gap-1 ml-5">
                    <CornerDownRight className="size-3 text-zinc-400" />
                    Unidade de venda convertida: <strong>{item.forma_venda_nome} (Conversão {item.forma_venda_fator}x)</strong>
                  </p>
                )}
                {item.custo_unitario && (
                  <p className="text-zinc-500 text-[10px] ml-5">
                    Custo Unitário Registrado: <strong className="text-zinc-800 tabular-nums">{formatCurrency(item.custo_unitario)}</strong>
                  </p>
                )}
              </div>
              
              {isRevisavel && (
                <div className="flex gap-2">
                  <Button variant="outline" size="xs" onClick={startEditing}>Alterar</Button>
                  <Button
                    variant="outline"
                    size="xs"
                    className="border-red-200 text-red-600 hover:bg-red-50"
                    icon={<Trash2 className="size-3" />}
                    loading={linkItemMutation.isPending}
                    onClick={() => linkItemMutation.mutate({ produto: null, forma_venda: null, custo_unitario: null })}
                  />
                </div>
              )}
            </div>
          )}

          {/* Item is ignored */}
          {item.ignorado && !editing && (
            <div className="bg-zinc-100/50 border border-zinc-200 rounded-lg p-3 flex justify-between items-center">
              <span className="text-xs text-zinc-500 font-medium">Este item será ignorado no controle de estoque.</span>
              {isRevisavel && (
                <Button size="xs" variant="outline" loading={linkItemMutation.isPending} onClick={handleRestore}>
                  Reativar Item
                </Button>
              )}
            </div>
          )}

          {/* Mapping Mode Form (When pending, or editing is active) */}
          {(editing || (!item.produto && !item.ignorado)) && (
            <div className="space-y-4">
              
              {/* Sugestões do Sistema */}
              {!selectedProduct && !item.ignorado && (
                <div className="space-y-2.5">
                  <div className="flex items-center gap-1.5 text-orange-600">
                    <Sparkles className="size-3.5 fill-orange-100" />
                    <span className="text-[10px] font-bold uppercase tracking-wider">Sugestões do Sistema (ObraFlow Match)</span>
                  </div>

                  {suggestionsQuery.isLoading ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      <Skeleton className="h-14 w-full" />
                      <Skeleton className="h-14 w-full" />
                    </div>
                  ) : suggestions.length === 0 ? (
                    <p className="text-[10px] text-zinc-400 font-medium italic">Nenhuma similaridade direta encontrada no cadastro de produtos.</p>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      {suggestions.map((sug) => {
                        const simPct = sug.similarity ? Math.round(sug.similarity * 100) : 0
                        return (
                          <button
                            key={sug.id}
                            type="button"
                            onClick={() => {
                              setSelectedProduct(sug)
                              setSelectedForma("")
                              setCustoUnitario(item.valor_unitario.toString())
                            }}
                            className="text-left p-2.5 rounded-lg border border-zinc-200 bg-white hover:border-orange-300 hover:bg-orange-50/10 transition-colors flex items-center justify-between gap-3 group"
                          >
                            <div className="min-w-0 flex-1">
                              <p className="text-xs font-bold text-zinc-900 truncate group-hover:text-orange-600 transition-colors">{sug.nome}</p>
                              <p className="text-[10px] text-zinc-400 mt-0.5">
                                SKU: {sug.sku || "sem"} • Estoque: {formatNumber(sug.estoque_atual, 1)}
                              </p>
                            </div>
                            <div className="text-right">
                              <span className="inline-block text-[9px] font-extrabold bg-green-50 text-green-700 px-1.5 py-0.2 rounded border border-green-150">
                                {simPct}% match
                              </span>
                            </div>
                          </button>
                        )
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* Autocomplete Input Search */}
              <div className="space-y-3">
                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-zinc-400 uppercase">Buscar Produto no Estoque</label>
                  {selectedProduct ? (
                    <div className="flex items-center justify-between p-3 rounded-lg border border-zinc-200 bg-zinc-50/50">
                      <div>
                        <p className="text-xs font-bold text-zinc-900">{selectedProduct.nome}</p>
                        <p className="text-[10px] text-zinc-400 mt-0.5">SKU: {selectedProduct.sku || "sem SKU"}</p>
                      </div>
                      <Button
                        variant="ghost"
                        size="xs"
                        onClick={() => {
                          setSelectedProduct(null)
                          setSelectedForma("")
                        }}
                      >
                        Limpar
                      </Button>
                    </div>
                  ) : (
                    <ProdutoAutocomplete
                      value={null}
                      onSelect={(p) => {
                        setSelectedProduct(p)
                        setSelectedForma("")
                        setCustoUnitario(item.valor_unitario.toString())
                      }}
                      onClear={() => {
                        setSelectedProduct(null)
                        setSelectedForma("")
                      }}
                    />
                  )}
                </div>

                {/* Form fields on product select */}
                {selectedProduct && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 border-l-2 border-orange-500 pl-3.5 py-1">
                    
                    {/* Forma de venda */}
                    <div className="space-y-1">
                      <div className="flex items-center gap-1">
                        <label className="text-[10px] font-bold text-zinc-500 uppercase">Unidade/Forma de Venda</label>
                        <span className="text-[9px] text-zinc-400">(Conversão do XML)</span>
                      </div>
                      <select
                        value={selectedForma}
                        onChange={(e) => setSelectedForma(e.target.value)}
                        className={cn(
                          "block h-8 w-full rounded-md border bg-white px-2 text-xs font-semibold focus:border-zinc-900 focus:outline-none",
                          requiresForma && !selectedForma ? "border-red-300" : "border-zinc-300"
                        )}
                      >
                        <option value="">
                          {requiresForma
                            ? "Selecione a forma"
                            : `Unidade Base (${("unidade_sigla" in selectedProduct && selectedProduct.unidade_sigla) || "un"})`}
                        </option>
                        {formasVenda.map((f) => (
                          <option key={f.id} value={f.id}>
                            {f.nome} (Fator: {f.fator_conversao}x)
                          </option>
                        ))}
                      </select>
                      {requiresForma && !selectedForma && (
                        <p className="text-[10px] font-medium text-red-600">
                          Produto com múltiplas formas exige seleção.
                        </p>
                      )}
                      <p className="text-[10px] text-zinc-500">
                        {selectedFormaObj
                          ? `${formatNumber(item.quantidade, 2)} ${selectedFormaObj.unidade} x ${formatNumber(selectedFormaObj.fator_conversao, 3)} = ${formatNumber(quantidadeConvertidaPreview, 3)} ${("unidade_sigla" in selectedProduct && selectedProduct.unidade_sigla) || "un"}`
                          : `${formatNumber(item.quantidade, 2)} ${("unidade_sigla" in selectedProduct && selectedProduct.unidade_sigla) || "un"}`}
                      </p>
                    </div>

                    {/* Custo Unitário */}
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-zinc-500 uppercase">Custo Unitário Final (R$)</label>
                      <input
                        type="number"
                        step="0.01"
                        value={custoUnitario}
                        onChange={(e) => setCustoUnitario(e.target.value)}
                        placeholder="0.00"
                        className="block w-full text-xs h-8 rounded-md border border-zinc-300 px-2 focus:border-zinc-900 focus:outline-none font-mono"
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Form Action buttons */}
              <div className="flex justify-between items-center gap-3 border-t border-zinc-100 pt-3">
                <div className="flex gap-2">
                  {editing && (
                    <Button variant="outline" size="sm" onClick={() => setEditing(false)}>
                      Cancelar
                    </Button>
                  )}
                  {!item.produto && !editing && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="border-zinc-200 text-zinc-500"
                      onClick={handleIgnore}
                    >
                      Ignorar este Item
                    </Button>
                  )}
                </div>
                
                {selectedProduct && (
                  <Button
                    size="sm"
                    className="bg-orange-500 hover:bg-orange-600 text-white font-bold"
                    loading={linkItemMutation.isPending}
                    disabled={!canApplyLink || linkItemMutation.isPending}
                    onClick={handleApplyLink}
                  >
                    Salvar Vínculo
                  </Button>
                )}
              </div>

            </div>
          )}

        </div>
      )}
    </div>
  )
}
