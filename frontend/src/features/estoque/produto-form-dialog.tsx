"use client"

import * as Dialog from "@radix-ui/react-dialog"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { PackagePlus, X } from "lucide-react"
import { useMemo, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useApiToast } from "@/hooks/use-api-toast"
import { fornecedorDisplayName } from "@/lib/estoque"
import { produtosService } from "@/services/produtos.service"
import type { Produto, ProdutoPayload } from "@/types"

interface ProdutoFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  produto?: Produto | null
  onSuccess?: (produto: Produto) => void
}

interface ProdutoFormState {
  nome: string
  categoria: string
  sku: string
  codigo_barras: string
  unidade: string
  estoque_minimo: string
  preco_compra: string
  preco_venda: string
  fornecedor_principal: string
  descricao: string
}

const emptyForm: ProdutoFormState = {
  nome: "",
  categoria: "",
  sku: "",
  codigo_barras: "",
  unidade: "",
  estoque_minimo: "0",
  preco_compra: "0",
  preco_venda: "0",
  fornecedor_principal: "",
  descricao: "",
}

function formFromProduto(produto?: Produto | null): ProdutoFormState {
  if (!produto) return emptyForm
  return {
    nome: produto.nome ?? "",
    categoria: produto.categoria ?? "",
    sku: produto.sku ?? "",
    codigo_barras: produto.codigo_barras ?? "",
    unidade: produto.unidade ?? "",
    estoque_minimo: String(produto.estoque_minimo ?? "0"),
    preco_compra: String(produto.preco_compra ?? "0"),
    preco_venda: String(produto.preco_venda ?? "0"),
    fornecedor_principal: produto.fornecedor_principal ?? "",
    descricao: produto.descricao ?? "",
  }
}

function normalizeDecimal(value: string, fallback = "0") {
  const trimmed = value.trim().replace(",", ".")
  if (!trimmed) return fallback
  return trimmed
}

export function ProdutoFormDialog({ open, onOpenChange, produto, onSuccess }: ProdutoFormDialogProps) {
  const queryClient = useQueryClient()
  const toast = useApiToast()
  const [form, setForm] = useState<ProdutoFormState>(emptyForm)
  const [submitted, setSubmitted] = useState(false)
  const [formKey, setFormKey] = useState("closed")
  const isEditing = Boolean(produto)
  const nextFormKey = open ? `${produto?.id ?? "novo"}:${produto?.updated_at ?? ""}` : "closed"

  if (formKey !== nextFormKey) {
    setFormKey(nextFormKey)
    setForm(formFromProduto(produto))
    setSubmitted(false)
  }

  const categoriasQuery = useQuery({
    queryKey: ["estoque", "categorias", "produto-form"],
    queryFn: () => produtosService.categorias({ page_size: 200, ordering: "nome" }),
    enabled: open,
    staleTime: 60_000,
  })

  const unidadesQuery = useQuery({
    queryKey: ["estoque", "unidades", "produto-form"],
    queryFn: () => produtosService.unidades({ page_size: 200, ordering: "sigla" }),
    enabled: open,
    staleTime: 60_000,
  })

  const fornecedoresQuery = useQuery({
    queryKey: ["estoque", "fornecedores", "produto-form"],
    queryFn: () => produtosService.fornecedores({ page_size: 200 }),
    enabled: open,
    staleTime: 60_000,
  })

  const categorias = categoriasQuery.data?.results ?? []
  const unidades = unidadesQuery.data?.results ?? []
  const fornecedores = fornecedoresQuery.data?.results ?? []

  const validation = useMemo(() => {
    const errors: Partial<Record<keyof ProdutoFormState, string>> = {}
    if (!form.nome.trim()) errors.nome = "Informe o nome."
    if (!form.categoria) errors.categoria = "Selecione a categoria."
    if (!form.unidade) errors.unidade = "Selecione a unidade base."
    if (Number(normalizeDecimal(form.estoque_minimo)) < 0) errors.estoque_minimo = "Valor inválido."
    if (Number(normalizeDecimal(form.preco_compra)) < 0) errors.preco_compra = "Valor inválido."
    if (Number(normalizeDecimal(form.preco_venda)) < 0) errors.preco_venda = "Valor inválido."
    return errors
  }, [form])

  const isValid = Object.keys(validation).length === 0

  const mutation = useMutation({
    mutationFn: () => {
      const payload: ProdutoPayload = {
        nome: form.nome.trim(),
        descricao: form.descricao.trim(),
        sku: form.sku.trim(),
        codigo_barras: form.codigo_barras.trim(),
        categoria: form.categoria,
        fornecedor_principal: form.fornecedor_principal || null,
        unidade: form.unidade,
        preco_compra: normalizeDecimal(form.preco_compra),
        preco_venda: normalizeDecimal(form.preco_venda),
        custo_medio: produto?.custo_medio ?? normalizeDecimal(form.preco_compra),
        estoque_minimo: normalizeDecimal(form.estoque_minimo),
      }
      return isEditing ? produtosService.update(produto!.id, payload) : produtosService.create(payload)
    },
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: ["estoque"] })
      toast.success(isEditing ? "Produto atualizado" : "Produto cadastrado")
      onOpenChange(false)
      onSuccess?.(saved)
    },
    onError: (error) => toast.error(error),
  })

  const updateField = (field: keyof ProdutoFormState, value: string) => {
    setForm((current) => ({ ...current, [field]: value }))
  }

  const showError = (field: keyof ProdutoFormState) => submitted && validation[field]

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
          className="fixed left-1/2 top-1/2 z-50 flex max-h-[92vh] w-[calc(100vw-24px)] max-w-3xl -translate-x-1/2 -translate-y-1/2 flex-col overflow-hidden rounded-lg border border-zinc-200 bg-white shadow-xl focus:outline-none"
          aria-describedby={undefined}
        >
          <div className="flex items-center justify-between border-b border-zinc-100 px-5 py-4">
            <Dialog.Title className="flex items-center gap-2 text-sm font-semibold text-zinc-950">
              <PackagePlus className="size-4 text-orange-600" />
              {isEditing ? "Editar Produto" : "Cadastrar Produto"}
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

          <div className="overflow-y-auto px-5 py-4">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <Field label="Nome" error={showError("nome")}>
                <Input
                  value={form.nome}
                  error={Boolean(showError("nome"))}
                  onChange={(event) => updateField("nome", event.target.value)}
                  disabled={mutation.isPending}
                />
              </Field>

              <Field label="Categoria" error={showError("categoria")}>
                <select
                  value={form.categoria}
                  onChange={(event) => updateField("categoria", event.target.value)}
                  disabled={mutation.isPending || categoriasQuery.isLoading}
                  className="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 text-sm text-zinc-900 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/30 disabled:bg-zinc-50 disabled:opacity-50"
                >
                  <option value="">Selecione</option>
                  {categorias.map((categoria) => (
                    <option key={categoria.id} value={categoria.id}>
                      {categoria.nome}
                    </option>
                  ))}
                </select>
              </Field>

              <Field label="Código / SKU">
                <Input
                  value={form.sku}
                  onChange={(event) => updateField("sku", event.target.value)}
                  disabled={mutation.isPending}
                />
              </Field>

              <Field label="Código de barras">
                <Input
                  value={form.codigo_barras}
                  onChange={(event) => updateField("codigo_barras", event.target.value)}
                  disabled={mutation.isPending}
                />
              </Field>

              <Field label="Unidade base" error={showError("unidade")}>
                <select
                  value={form.unidade}
                  onChange={(event) => updateField("unidade", event.target.value)}
                  disabled={mutation.isPending || unidadesQuery.isLoading}
                  className="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 text-sm text-zinc-900 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/30 disabled:bg-zinc-50 disabled:opacity-50"
                >
                  <option value="">Selecione</option>
                  {unidades.map((unidade) => (
                    <option key={unidade.id} value={unidade.id}>
                      {unidade.nome} ({unidade.sigla})
                    </option>
                  ))}
                </select>
              </Field>

              <Field label="Fornecedor">
                <select
                  value={form.fornecedor_principal}
                  onChange={(event) => updateField("fornecedor_principal", event.target.value)}
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

              <Field label="Estoque mínimo" error={showError("estoque_minimo")}>
                <Input
                  type="number"
                  min="0"
                  step="0.001"
                  value={form.estoque_minimo}
                  error={Boolean(showError("estoque_minimo"))}
                  onChange={(event) => updateField("estoque_minimo", event.target.value)}
                  disabled={mutation.isPending}
                />
              </Field>

              <Field label="Preço de compra" error={showError("preco_compra")}>
                <Input
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.preco_compra}
                  error={Boolean(showError("preco_compra"))}
                  onChange={(event) => updateField("preco_compra", event.target.value)}
                  disabled={mutation.isPending}
                />
              </Field>

              <Field label="Preço de venda padrão" error={showError("preco_venda")}>
                <Input
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.preco_venda}
                  error={Boolean(showError("preco_venda"))}
                  onChange={(event) => updateField("preco_venda", event.target.value)}
                  disabled={mutation.isPending}
                />
              </Field>

              <div className="md:col-span-2">
                <Field label="Observação">
                  <textarea
                    value={form.descricao}
                    rows={3}
                    onChange={(event) => updateField("descricao", event.target.value)}
                    disabled={mutation.isPending}
                    className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/30 disabled:bg-zinc-50 disabled:opacity-50"
                  />
                </Field>
              </div>
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
              Salvar Produto
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
