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
  ncm: string
  cfop_padrao: string
  cst_csosn: string
  cest: string
  origem_mercadoria: string
  unidade_tributavel: string
  ean_tributavel: string
  codigo_beneficio_fiscal: string
  aliquota_icms: string
  aliquota_ipi: string
  aliquota_pis: string
  aliquota_cofins: string
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
  ncm: "",
  cfop_padrao: "",
  cst_csosn: "",
  cest: "",
  origem_mercadoria: "0",
  unidade_tributavel: "",
  ean_tributavel: "SEM GTIN",
  codigo_beneficio_fiscal: "",
  aliquota_icms: "0",
  aliquota_ipi: "0",
  aliquota_pis: "0",
  aliquota_cofins: "0",
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
    ncm: produto.ncm ?? "",
    cfop_padrao: produto.cfop_padrao ?? "",
    cst_csosn: produto.cst_csosn ?? "",
    cest: produto.cest ?? "",
    origem_mercadoria: produto.origem_mercadoria ?? "0",
    unidade_tributavel: produto.unidade_tributavel ?? "",
    ean_tributavel: produto.ean_tributavel ?? "SEM GTIN",
    codigo_beneficio_fiscal: produto.codigo_beneficio_fiscal ?? "",
    aliquota_icms: String(produto.aliquota_icms ?? "0"),
    aliquota_ipi: String(produto.aliquota_ipi ?? "0"),
    aliquota_pis: String(produto.aliquota_pis ?? "0"),
    aliquota_cofins: String(produto.aliquota_cofins ?? "0"),
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
    if (form.ncm && !/^\d{8}$/.test(form.ncm.replace(/\D/g, ""))) errors.ncm = "NCM deve ter 8 dígitos."
    if (form.cfop_padrao && !/^\d{4}$/.test(form.cfop_padrao.replace(/\D/g, ""))) errors.cfop_padrao = "CFOP deve ter 4 dígitos."
    if (form.cest && !/^\d{7}$/.test(form.cest.replace(/\D/g, ""))) errors.cest = "CEST deve ter 7 dígitos."
    for (const field of ["aliquota_icms", "aliquota_ipi", "aliquota_pis", "aliquota_cofins"] as const) {
      if (Number(normalizeDecimal(form[field])) < 0) errors[field] = "Alíquota inválida."
    }
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
        ncm: form.ncm.trim(),
        cfop_padrao: form.cfop_padrao.trim(),
        cst_csosn: form.cst_csosn.trim(),
        cest: form.cest.trim(),
        origem_mercadoria: form.origem_mercadoria,
        unidade_tributavel: form.unidade_tributavel.trim().toUpperCase(),
        ean_tributavel: form.ean_tributavel.trim() || "SEM GTIN",
        codigo_beneficio_fiscal: form.codigo_beneficio_fiscal.trim(),
        aliquota_icms: normalizeDecimal(form.aliquota_icms),
        aliquota_ipi: normalizeDecimal(form.aliquota_ipi),
        aliquota_pis: normalizeDecimal(form.aliquota_pis),
        aliquota_cofins: normalizeDecimal(form.aliquota_cofins),
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

              <div className="space-y-4 rounded-md border border-yellow-200 bg-yellow-50/50 p-3 md:col-span-2">
                <div>
                  <p className="text-xs font-bold text-zinc-800">Dados fiscais</p>
                  <p className="text-[11px] text-zinc-600">
                    Estes dados serão usados futuramente para emissão de NF-e. Confirme as regras fiscais com seu contador.
                  </p>
                </div>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
                  <Field label="NCM" error={showError("ncm")}>
                    <Input
                      value={form.ncm}
                      maxLength={8}
                      error={Boolean(showError("ncm"))}
                      onChange={(event) => updateField("ncm", event.target.value.replace(/\D/g, ""))}
                      disabled={mutation.isPending}
                    />
                  </Field>
                  <Field label="CFOP padrão" error={showError("cfop_padrao")}>
                    <Input
                      value={form.cfop_padrao}
                      maxLength={4}
                      error={Boolean(showError("cfop_padrao"))}
                      onChange={(event) => updateField("cfop_padrao", event.target.value.replace(/\D/g, ""))}
                      disabled={mutation.isPending}
                    />
                  </Field>
                  <Field label="CST/CSOSN">
                    <Input
                      value={form.cst_csosn}
                      maxLength={4}
                      onChange={(event) => updateField("cst_csosn", event.target.value.toUpperCase())}
                      disabled={mutation.isPending}
                    />
                  </Field>
                  <Field label="CEST" error={showError("cest")}>
                    <Input
                      value={form.cest}
                      maxLength={7}
                      error={Boolean(showError("cest"))}
                      onChange={(event) => updateField("cest", event.target.value.replace(/\D/g, ""))}
                      disabled={mutation.isPending}
                    />
                  </Field>
                  <Field label="Origem" >
                    <select
                      value={form.origem_mercadoria}
                      onChange={(event) => updateField("origem_mercadoria", event.target.value)}
                      disabled={mutation.isPending}
                      className="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 text-sm text-zinc-900 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/30 disabled:bg-zinc-50 disabled:opacity-50"
                    >
                      <option value="0">0 - Nacional</option>
                      <option value="1">1 - Estrangeira direta</option>
                      <option value="2">2 - Estrangeira mercado interno</option>
                      <option value="3">3 - Nacional importação &gt; 40%</option>
                      <option value="4">4 - Nacional PPB</option>
                      <option value="5">5 - Nacional importação &lt;= 40%</option>
                      <option value="6">6 - Estrangeira direta sem similar</option>
                      <option value="7">7 - Estrangeira mercado interno sem similar</option>
                      <option value="8">8 - Nacional importação &gt; 70%</option>
                    </select>
                  </Field>
                  <Field label="Unidade tributável">
                    <Input
                      value={form.unidade_tributavel}
                      onChange={(event) => updateField("unidade_tributavel", event.target.value.toUpperCase())}
                      disabled={mutation.isPending}
                    />
                  </Field>
                  <Field label="EAN tributável">
                    <Input
                      value={form.ean_tributavel}
                      onChange={(event) => updateField("ean_tributavel", event.target.value)}
                      disabled={mutation.isPending}
                    />
                  </Field>
                  <Field label="Benefício fiscal">
                    <Input
                      value={form.codigo_beneficio_fiscal}
                      onChange={(event) => updateField("codigo_beneficio_fiscal", event.target.value.toUpperCase())}
                      disabled={mutation.isPending}
                    />
                  </Field>
                  <Field label="ICMS %" error={showError("aliquota_icms")}>
                    <Input type="number" min="0" step="0.0001" value={form.aliquota_icms} onChange={(event) => updateField("aliquota_icms", event.target.value)} disabled={mutation.isPending} />
                  </Field>
                  <Field label="IPI %" error={showError("aliquota_ipi")}>
                    <Input type="number" min="0" step="0.0001" value={form.aliquota_ipi} onChange={(event) => updateField("aliquota_ipi", event.target.value)} disabled={mutation.isPending} />
                  </Field>
                  <Field label="PIS %" error={showError("aliquota_pis")}>
                    <Input type="number" min="0" step="0.0001" value={form.aliquota_pis} onChange={(event) => updateField("aliquota_pis", event.target.value)} disabled={mutation.isPending} />
                  </Field>
                  <Field label="COFINS %" error={showError("aliquota_cofins")}>
                    <Input type="number" min="0" step="0.0001" value={form.aliquota_cofins} onChange={(event) => updateField("aliquota_cofins", event.target.value)} disabled={mutation.isPending} />
                  </Field>
                </div>
              </div>

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
