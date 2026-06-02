"use client"

import * as Dialog from "@radix-ui/react-dialog"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowDownToLine, ArrowUpFromLine, RotateCcw, SlidersHorizontal, X } from "lucide-react"
import { useMemo, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ProdutoAutocomplete } from "@/features/fiado/produto-autocomplete"
import { useApiToast } from "@/hooks/use-api-toast"
import { createOperationKey, fornecedorDisplayName } from "@/lib/estoque"
import { formatNumber, toNumber } from "@/lib/format"
import { cn, formatCurrency } from "@/lib/utils"
import { formasVendaService } from "@/services/formas-venda.service"
import { movimentacoesEstoqueService } from "@/services/movimentacoes-estoque.service"
import { produtosService } from "@/services/produtos.service"
import type { Produto, TipoMovimentacao } from "@/types"

type OperacaoTipo = Extract<TipoMovimentacao, "ENTRADA" | "SAIDA" | "AJUSTE" | "DEVOLUCAO">

interface MovimentacaoEstoqueDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  produto?: Produto | null
  tipoInicial?: OperacaoTipo
  bloquearProduto?: boolean
}

interface MovimentoFormState {
  tipo: OperacaoTipo
  quantidade: string
  forma_venda: string
  custo_unitario: string
  fornecedor: string
  motivo: string
  observacao: string
}

const labels: Record<OperacaoTipo, string> = {
  ENTRADA: "Entrada",
  SAIDA: "Saída",
  AJUSTE: "Ajuste",
  DEVOLUCAO: "Devolução",
}

const icons: Record<OperacaoTipo, React.ReactNode> = {
  ENTRADA: <ArrowDownToLine className="size-3.5" />,
  SAIDA: <ArrowUpFromLine className="size-3.5" />,
  AJUSTE: <SlidersHorizontal className="size-3.5" />,
  DEVOLUCAO: <RotateCcw className="size-3.5" />,
}

function initialState(tipo: OperacaoTipo): MovimentoFormState {
  return {
    tipo,
    quantidade: "",
    forma_venda: "",
    custo_unitario: "",
    fornecedor: "",
    motivo: "",
    observacao: "",
  }
}

function normalizeDecimal(value: string, fallback = "0") {
  const trimmed = value.trim().replace(",", ".")
  return trimmed || fallback
}

export function MovimentacaoEstoqueDialog({
  open,
  onOpenChange,
  produto,
  tipoInicial = "ENTRADA",
  bloquearProduto = false,
}: MovimentacaoEstoqueDialogProps) {
  const queryClient = useQueryClient()
  const toast = useApiToast()
  const [selectedProduct, setSelectedProduct] = useState<Produto | null>(produto ?? null)
  const [form, setForm] = useState<MovimentoFormState>(initialState(tipoInicial))
  const [submitted, setSubmitted] = useState(false)
  const [formKey, setFormKey] = useState("closed")
  const nextFormKey = open ? `${produto?.id ?? "livre"}:${produto?.updated_at ?? ""}:${tipoInicial}` : "closed"

  if (formKey !== nextFormKey) {
    setFormKey(nextFormKey)
    setSelectedProduct(produto ?? null)
    setForm({
      ...initialState(tipoInicial),
      fornecedor: produto?.fornecedor_principal ?? "",
      custo_unitario: produto?.preco_compra ? String(produto.preco_compra) : "",
    })
    setSubmitted(false)
  }

  const formasQuery = useQuery({
    queryKey: ["estoque", "formas-venda", selectedProduct?.id, "movimentacao"],
    queryFn: () => formasVendaService.list({ produto: selectedProduct!.id, page_size: 100 }),
    enabled: open && Boolean(selectedProduct),
    staleTime: 30_000,
  })

  const fornecedoresQuery = useQuery({
    queryKey: ["estoque", "fornecedores", "movimentacao"],
    queryFn: () => produtosService.fornecedores({ page_size: 200 }),
    enabled: open && form.tipo === "ENTRADA",
    staleTime: 60_000,
  })

  const formas = useMemo(
    () => (formasQuery.data?.results ?? []).filter((forma) => forma.ativo),
    [formasQuery.data?.results]
  )
  const fornecedores = fornecedoresQuery.data?.results ?? []
  const selectedForma = formas.find((forma) => forma.id === form.forma_venda) ?? null
  const usaForma = Boolean(selectedForma && (form.tipo === "ENTRADA" || form.tipo === "SAIDA"))
  const quantidade = Number(normalizeDecimal(form.quantidade))
  const fator = selectedForma ? toNumber(selectedForma.fator_conversao) : 1
  const quantidadeConvertida = usaForma ? quantidade * fator : quantidade
  const estoqueAtual = toNumber(selectedProduct?.estoque_atual)
  const delta =
    form.tipo === "SAIDA"
      ? -quantidadeConvertida
      : form.tipo === "AJUSTE"
        ? quantidade
        : quantidadeConvertida
  const estoqueDepois = estoqueAtual + (Number.isFinite(delta) ? delta : 0)
  const saldoNegativo = form.tipo === "SAIDA" && estoqueDepois < 0

  const validation = useMemo(() => {
    const errors: Record<string, string> = {}
    if (!selectedProduct) errors.produto = "Selecione o produto."
    if (!form.quantidade.trim()) {
      errors.quantidade = "Informe a quantidade."
    } else if (form.tipo === "AJUSTE" && quantidade === 0) {
      errors.quantidade = "Ajuste não pode ser zero."
    } else if (form.tipo !== "AJUSTE" && quantidade <= 0) {
      errors.quantidade = "Quantidade deve ser maior que zero."
    }
    if ((form.tipo === "AJUSTE" || form.tipo === "DEVOLUCAO") && !form.motivo.trim()) {
      errors.motivo = "Informe o motivo."
    }
    if (form.custo_unitario && Number(normalizeDecimal(form.custo_unitario)) < 0) {
      errors.custo_unitario = "Custo não pode ser negativo."
    }
    if (saldoNegativo) {
      errors.estoque = "Saldo insuficiente."
    }
    return errors
  }, [form, quantidade, saldoNegativo, selectedProduct])

  const isValid = Object.keys(validation).length === 0

  const mutation = useMutation({
    mutationFn: () => {
      const basePayload = {
        produto: selectedProduct!.id,
        motivo: form.motivo.trim(),
        observacao: form.observacao.trim(),
        idempotency_key: createOperationKey(`estoque-${form.tipo.toLowerCase()}`),
        metadata: { origem: "frontend_estoque" },
      }

      if (form.tipo === "ENTRADA") {
        return movimentacoesEstoqueService.entrada({
          ...basePayload,
          ...(usaForma
            ? { forma_venda: form.forma_venda, quantidade_informada: normalizeDecimal(form.quantidade) }
            : { quantidade: normalizeDecimal(form.quantidade) }),
          custo_unitario: form.custo_unitario ? normalizeDecimal(form.custo_unitario) : null,
          fornecedor: form.fornecedor || null,
        })
      }

      if (form.tipo === "SAIDA") {
        return movimentacoesEstoqueService.saida({
          ...basePayload,
          ...(usaForma
            ? { forma_venda: form.forma_venda, quantidade_informada: normalizeDecimal(form.quantidade) }
            : { quantidade: normalizeDecimal(form.quantidade) }),
        })
      }

      if (form.tipo === "AJUSTE") {
        return movimentacoesEstoqueService.ajuste({
          ...basePayload,
          quantidade: normalizeDecimal(form.quantidade),
          custo_unitario: form.custo_unitario ? normalizeDecimal(form.custo_unitario) : null,
        })
      }

      return movimentacoesEstoqueService.devolucao({
        ...basePayload,
        quantidade: normalizeDecimal(form.quantidade),
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["estoque"] })
      toast.success("Movimentação registrada")
      onOpenChange(false)
    },
    onError: (error) => toast.error(error),
  })

  const updateField = <K extends keyof MovimentoFormState>(field: K, value: MovimentoFormState[K]) => {
    setForm((current) => ({ ...current, [field]: value }))
  }

  const showError = (key: string) => submitted && validation[key]
  const unidadeBase = selectedProduct?.unidade_sigla ?? "un"
  const showForma = form.tipo === "ENTRADA" || form.tipo === "SAIDA"
  const showCusto = form.tipo === "ENTRADA" || form.tipo === "AJUSTE"

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(value) => {
        if (!mutation.isPending) onOpenChange(value)
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-zinc-950/30 backdrop-blur-[2px] data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=closed]:animate-out data-[state=closed]:fade-out-0" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 z-50 flex max-h-[92vh] w-[calc(100vw-24px)] max-w-2xl -translate-x-1/2 -translate-y-1/2 flex-col overflow-hidden rounded-lg border border-zinc-200 bg-white shadow-xl focus:outline-none"
          aria-describedby={undefined}
        >
          <div className="flex items-center justify-between border-b border-zinc-100 px-5 py-4">
            <Dialog.Title className="flex items-center gap-2 text-sm font-semibold text-zinc-950">
              {icons[form.tipo]}
              Movimentar Estoque
            </Dialog.Title>
            <button
              type="button"
              disabled={mutation.isPending}
              onClick={() => onOpenChange(false)}
              className="rounded-md p-1.5 text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-700 disabled:opacity-50"
              aria-label="Fechar"
            >
              <X className="size-4" />
            </button>
          </div>

          <div className="space-y-4 overflow-y-auto px-5 py-4">
            <div className="flex flex-wrap gap-1">
              {(Object.keys(labels) as OperacaoTipo[]).map((tipo) => (
                <button
                  key={tipo}
                  type="button"
                  disabled={mutation.isPending}
                  onClick={() =>
                    setForm((current) => ({
                      ...current,
                      tipo,
                      forma_venda: tipo === "ENTRADA" || tipo === "SAIDA" ? current.forma_venda : "",
                    }))
                  }
                  className={cn(
                    "inline-flex h-8 items-center gap-1.5 rounded-md border px-3 text-xs font-semibold transition-colors",
                    form.tipo === tipo
                      ? "border-zinc-900 bg-zinc-900 text-white"
                      : "border-zinc-200 bg-white text-zinc-600 hover:border-zinc-400"
                  )}
                >
                  {icons[tipo]}
                  {labels[tipo]}
                </button>
              ))}
            </div>

            <div className="space-y-1.5">
              <span className="text-xs font-medium text-zinc-600">Produto</span>
              {bloquearProduto && selectedProduct ? (
                <div className="rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm font-semibold text-zinc-900">
                  {selectedProduct.nome}
                </div>
              ) : (
                <ProdutoAutocomplete
                  value={selectedProduct}
                  onSelect={(item) => {
                    setSelectedProduct(item)
                    setForm((current) => ({
                      ...current,
                      forma_venda: "",
                      fornecedor: item.fornecedor_principal ?? "",
                      custo_unitario: String(item.preco_compra ?? ""),
                    }))
                  }}
                  onClear={() => {
                    setSelectedProduct(null)
                    setForm((current) => ({ ...current, forma_venda: "", fornecedor: "", custo_unitario: "" }))
                  }}
                  error={Boolean(showError("produto"))}
                  disabled={mutation.isPending}
                />
              )}
              {showError("produto") && <span className="text-[11px] font-medium text-red-600">{showError("produto")}</span>}
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <Field label={form.tipo === "AJUSTE" ? "Quantidade do ajuste" : "Quantidade"} error={showError("quantidade")}>
                <Input
                  type="number"
                  step="0.001"
                  min={form.tipo === "AJUSTE" ? undefined : "0.001"}
                  value={form.quantidade}
                  error={Boolean(showError("quantidade"))}
                  onChange={(event) => updateField("quantidade", event.target.value)}
                  disabled={mutation.isPending}
                />
              </Field>

              {showForma ? (
                <Field label="Forma de venda">
                  <select
                    value={form.forma_venda}
                    onChange={(event) => updateField("forma_venda", event.target.value)}
                    disabled={mutation.isPending || !selectedProduct || formasQuery.isLoading}
                    className="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 text-sm text-zinc-900 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/30 disabled:bg-zinc-50 disabled:opacity-50"
                  >
                    <option value="">Unidade base ({unidadeBase})</option>
                    {formas.map((forma) => (
                      <option key={forma.id} value={forma.id}>
                        {forma.nome} ({forma.unidade})
                      </option>
                    ))}
                  </select>
                </Field>
              ) : (
                <Field label="Unidade base">
                  <div className="flex h-9 items-center rounded-md border border-zinc-200 bg-zinc-50 px-3 text-sm font-semibold text-zinc-700">
                    {unidadeBase}
                  </div>
                </Field>
              )}

              {showCusto && (
                <Field label="Custo unitário" error={showError("custo_unitario")}>
                  <Input
                    type="number"
                    min="0"
                    step="0.01"
                    value={form.custo_unitario}
                    error={Boolean(showError("custo_unitario"))}
                    onChange={(event) => updateField("custo_unitario", event.target.value)}
                    disabled={mutation.isPending}
                  />
                </Field>
              )}

              {form.tipo === "ENTRADA" && (
                <Field label="Fornecedor">
                  <select
                    value={form.fornecedor}
                    onChange={(event) => updateField("fornecedor", event.target.value)}
                    disabled={mutation.isPending || fornecedoresQuery.isLoading}
                    className="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 text-sm text-zinc-900 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/30 disabled:bg-zinc-50 disabled:opacity-50"
                  >
                    <option value="">Sem fornecedor</option>
                    {fornecedores.map((fornecedor) => (
                      <option key={fornecedor.id} value={fornecedor.id}>
                        {fornecedorDisplayName(fornecedor)}
                      </option>
                    ))}
                  </select>
                </Field>
              )}
            </div>

            <Field label={form.tipo === "AJUSTE" || form.tipo === "DEVOLUCAO" ? "Motivo" : "Motivo"}>
              <Input
                value={form.motivo}
                error={Boolean(showError("motivo"))}
                onChange={(event) => updateField("motivo", event.target.value)}
                disabled={mutation.isPending}
              />
              {showError("motivo") && <span className="block text-[11px] font-medium text-red-600">{showError("motivo")}</span>}
            </Field>

            <Field label="Observação">
              <textarea
                value={form.observacao}
                rows={2}
                onChange={(event) => updateField("observacao", event.target.value)}
                disabled={mutation.isPending}
                className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/30 disabled:bg-zinc-50 disabled:opacity-50"
              />
            </Field>

            <div className="grid grid-cols-1 gap-3 rounded-md border border-zinc-200 bg-zinc-50 p-3 text-xs md:grid-cols-3">
              <div>
                <span className="block text-zinc-500">Conversão</span>
                <strong className="mt-1 block text-zinc-900">
                  {form.quantidade
                    ? usaForma && selectedForma
                      ? `${formatNumber(quantidade, 3)} ${selectedForma.unidade} x ${formatNumber(selectedForma.fator_conversao, 3)} ${unidadeBase} = ${formatNumber(quantidadeConvertida, 3)} ${unidadeBase}`
                      : `${formatNumber(quantidade, 3)} ${unidadeBase}`
                    : "-"}
                </strong>
              </div>
              <div>
                <span className="block text-zinc-500">Estoque atual</span>
                <strong className="mt-1 block text-zinc-900">
                  {selectedProduct ? `${formatNumber(estoqueAtual, 3)} ${unidadeBase}` : "-"}
                </strong>
              </div>
              <div>
                <span className="block text-zinc-500">Estoque após</span>
                <strong className={cn("mt-1 block", saldoNegativo ? "text-red-600" : "text-zinc-900")}>
                  {selectedProduct && form.quantidade ? `${formatNumber(estoqueDepois, 3)} ${unidadeBase}` : "-"}
                </strong>
              </div>
              {showCusto && form.custo_unitario && form.quantidade && (
                <div className="md:col-span-3">
                  <span className="block text-zinc-500">Valor estimado</span>
                  <strong className="mt-1 block text-zinc-900">
                    {formatCurrency(toNumber(form.custo_unitario) * Math.abs(quantidadeConvertida))}
                  </strong>
                </div>
              )}
              {showError("estoque") && <span className="font-medium text-red-600 md:col-span-3">{showError("estoque")}</span>}
            </div>
          </div>

          <div className="flex justify-end gap-2 border-t border-zinc-100 bg-zinc-50/70 px-5 py-3">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={mutation.isPending}
              onClick={() => onOpenChange(false)}
            >
              Cancelar
            </Button>
            <Button
              type="button"
              size="sm"
              loading={mutation.isPending}
              onClick={() => {
                setSubmitted(true)
                if (isValid) mutation.mutate()
              }}
            >
              Salvar Movimentação
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

function Field({
  label,
  error,
  children,
}: {
  label: string
  error?: string | false
  children: React.ReactNode
}) {
  return (
    <label className="block space-y-1.5">
      <span className="text-xs font-medium text-zinc-600">{label}</span>
      {children}
      {error && <span className="block text-[11px] font-medium text-red-600">{error}</span>}
    </label>
  )
}
