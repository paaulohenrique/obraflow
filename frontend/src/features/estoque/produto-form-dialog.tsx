"use client"

import * as Dialog from "@radix-ui/react-dialog"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { PackagePlus, Plus, X } from "lucide-react"
import { useMemo, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useApiToast } from "@/hooks/use-api-toast"
import { fornecedorDisplayName } from "@/lib/estoque"
import { formasVendaService } from "@/services/formas-venda.service"
import { produtosService } from "@/services/produtos.service"
import type { CategoriaProduto, PaginatedResponse, Produto, ProdutoPayload, UnidadeMedida } from "@/types"

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

interface CategoriaDraft {
  nome: string
  descricao: string
}

interface UnidadeDraft {
  nome: string
  sigla: string
  descricao: string
}

// Embalagens de compra comuns na construção civil
// baseUnidade = sigla da unidade que deve ser a base do produto
// fator = quantas baseUnidades há em 1 embalagem
const EMBALAGEM_PRESETS = [
  { key: "saco_50kg",  label: "Saco 50kg",  nome: "Saco 50kg",  unidade: "SACO",    fator: "50",   baseUnidade: "KG", baseNome: "Quilograma" },
  { key: "saco_25kg",  label: "Saco 25kg",  nome: "Saco 25kg",  unidade: "SACO",    fator: "25",   baseUnidade: "KG", baseNome: "Quilograma" },
  { key: "barra_6m",   label: "Barra 6m",   nome: "Barra 6m",   unidade: "BARRA",   fator: "6",    baseUnidade: "M",  baseNome: "Metro"      },
  { key: "rolo_100m",  label: "Rolo 100m",  nome: "Rolo 100m",  unidade: "ROLO",    fator: "100",  baseUnidade: "M",  baseNome: "Metro"      },
  { key: "milheiro",   label: "Milheiro",   nome: "Milheiro",   unidade: "MILHEIRO", fator: "1000", baseUnidade: "UN", baseNome: "Unidade"    },
] as const

type EmbalagemPreset = (typeof EMBALAGEM_PRESETS)[number]

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

const emptyCategoriaDraft: CategoriaDraft = {
  nome: "",
  descricao: "",
}

const emptyUnidadeDraft: UnidadeDraft = {
  nome: "",
  sigla: "",
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

function upsertPaginatedItem<T extends { id: string }>(
  current: PaginatedResponse<T> | undefined,
  item: T,
  sortFn: (a: T, b: T) => number
) {
  if (!current) return current
  const exists = current.results.some((currentItem) => currentItem.id === item.id)
  const results = [
    ...current.results.filter((currentItem) => currentItem.id !== item.id),
    item,
  ].sort(sortFn)
  return {
    ...current,
    count: exists ? current.count : current.count + 1,
    results,
  }
}

export function ProdutoFormDialog({ open, onOpenChange, produto, onSuccess }: ProdutoFormDialogProps) {
  const queryClient = useQueryClient()
  const toast = useApiToast()
  const [form, setForm] = useState<ProdutoFormState>(emptyForm)
  const [submitted, setSubmitted] = useState(false)
  const [formKey, setFormKey] = useState("closed")
  const [categoriaCreatorOpen, setCategoriaCreatorOpen] = useState(false)
  const [unidadeCreatorOpen, setUnidadeCreatorOpen] = useState(false)
  const [categoriaDraft, setCategoriaDraft] = useState<CategoriaDraft>(emptyCategoriaDraft)
  const [unidadeDraft, setUnidadeDraft] = useState<UnidadeDraft>(emptyUnidadeDraft)
  const [categoriaSubmitted, setCategoriaSubmitted] = useState(false)
  const [unidadeSubmitted, setUnidadeSubmitted] = useState(false)
  const [embalagemPreset, setEmbalagemPreset] = useState<EmbalagemPreset | null>(null)
  const [fiscalAberto, setFiscalAberto] = useState(false)
  const isEditing = Boolean(produto)
  const nextFormKey = open ? `${produto?.id ?? "novo"}:${produto?.updated_at ?? ""}` : "closed"

  if (formKey !== nextFormKey) {
    setFormKey(nextFormKey)
    setForm(formFromProduto(produto))
    setSubmitted(false)
    setCategoriaCreatorOpen(false)
    setUnidadeCreatorOpen(false)
    setCategoriaDraft(emptyCategoriaDraft)
    setUnidadeDraft(emptyUnidadeDraft)
    setCategoriaSubmitted(false)
    setUnidadeSubmitted(false)
    setEmbalagemPreset(null)
    setFiscalAberto(false)
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
  const categoriaDraftError = categoriaSubmitted && !categoriaDraft.nome.trim()
    ? "Informe o nome."
    : undefined
  const unidadeNomeError = unidadeSubmitted && !unidadeDraft.nome.trim()
    ? "Informe o nome."
    : undefined
  const unidadeSiglaError = unidadeSubmitted && !unidadeDraft.sigla.trim()
    ? "Informe a sigla."
    : undefined

  const mutation = useMutation({
    mutationFn: async () => {
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

      const saved = isEditing
        ? await produtosService.update(produto!.id, payload)
        : await produtosService.create(payload)

      // Cria formas de venda automaticamente ao cadastrar com embalagem
      if (embalagemPreset && !isEditing) {
        // Busca a forma "Unidade" criada automaticamente pelo backend
        const formasExistentes = await formasVendaService.list({ produto: saved.id, page_size: 100 })
        const formaDefault = formasExistentes.results.find(
          (f) => f.nome === "Unidade" && Number(f.fator_conversao) === 1
        )
        // Forma na unidade base (ex: Quilograma KG fator=1) para venda fracionada
        await formasVendaService.create({
          produto: saved.id,
          nome: embalagemPreset.baseNome,
          unidade: embalagemPreset.baseUnidade,
          fator_conversao: "1",
          permite_fracionado: true,
          padrao: false,
        })
        // Forma da embalagem (ex: Saco 50kg fator=50) como padrão
        await formasVendaService.create({
          produto: saved.id,
          nome: embalagemPreset.nome,
          unidade: embalagemPreset.unidade,
          fator_conversao: embalagemPreset.fator,
          permite_fracionado: false,
          padrao: true,
        })
        // Remove a forma genérica "Unidade" que o backend criou
        if (formaDefault) await formasVendaService.inativar(formaDefault.id)
      }

      return saved
    },
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: ["estoque"] })
      toast.success(isEditing ? "Produto atualizado" : "Produto cadastrado")
      onOpenChange(false)
      onSuccess?.(saved)
    },
    onError: (error) => toast.error(error),
  })

  const categoriaMutation = useMutation({
    mutationFn: () =>
      produtosService.createCategoria({
        nome: categoriaDraft.nome.trim(),
        descricao: categoriaDraft.descricao.trim(),
      }),
    onSuccess: (saved) => {
      queryClient.setQueryData<PaginatedResponse<CategoriaProduto>>(
        ["estoque", "categorias", "produto-form"],
        (current) =>
          upsertPaginatedItem(current, saved, (a, b) => a.nome.localeCompare(b.nome, "pt-BR"))
      )
      queryClient.invalidateQueries({ queryKey: ["estoque", "categorias"] })
      setForm((current) => ({ ...current, categoria: saved.id }))
      setCategoriaCreatorOpen(false)
      setCategoriaDraft(emptyCategoriaDraft)
      setCategoriaSubmitted(false)
      toast.success("Categoria criada")
    },
    onError: (error) => toast.error(error),
  })

  const unidadeMutation = useMutation({
    mutationFn: () =>
      produtosService.createUnidade({
        nome: unidadeDraft.nome.trim(),
        sigla: unidadeDraft.sigla.trim().toUpperCase(),
        descricao: unidadeDraft.descricao.trim(),
      }),
    onSuccess: (saved) => {
      queryClient.setQueryData<PaginatedResponse<UnidadeMedida>>(
        ["estoque", "unidades", "produto-form"],
        (current) =>
          upsertPaginatedItem(current, saved, (a, b) => a.sigla.localeCompare(b.sigla, "pt-BR"))
      )
      queryClient.invalidateQueries({ queryKey: ["estoque", "unidades"] })
      setForm((current) => ({ ...current, unidade: saved.id }))
      setUnidadeCreatorOpen(false)
      setUnidadeDraft(emptyUnidadeDraft)
      setUnidadeSubmitted(false)
      toast.success("Unidade criada")
    },
    onError: (error) => toast.error(error),
  })

  const isWorking = mutation.isPending || categoriaMutation.isPending || unidadeMutation.isPending

  const updateField = (field: keyof ProdutoFormState, value: string) => {
    setForm((current) => ({ ...current, [field]: value }))
  }

  const applyEmbalagemPreset = (preset: EmbalagemPreset) => {
    setEmbalagemPreset(preset)
    // Auto-seleciona a unidade base correta (ex: KG para saco, M para barra)
    const unitMatch = unidades.find((u) => u.sigla.toUpperCase() === preset.baseUnidade)
    if (unitMatch) setForm((current) => ({ ...current, unidade: unitMatch.id }))
  }

  const showError = (field: keyof ProdutoFormState) => submitted && validation[field]

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(value) => {
        if (!isWorking) onOpenChange(value)
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
              disabled={isWorking}
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
                  disabled={isWorking}
                />
              </Field>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-medium text-zinc-600">Categoria</span>
                  <button
                    type="button"
                    onClick={() => setCategoriaCreatorOpen((value) => !value)}
                    disabled={isWorking}
                    className="inline-flex h-7 items-center gap-1 rounded-md border border-zinc-200 bg-white px-2 text-xs font-medium text-zinc-700 transition-colors hover:border-orange-300 hover:text-orange-700 disabled:opacity-50"
                  >
                    <Plus className="size-3" />
                    Nova
                  </button>
                </div>
                <select
                  aria-label="Categoria"
                  value={form.categoria}
                  onChange={(event) => updateField("categoria", event.target.value)}
                  disabled={isWorking || categoriasQuery.isLoading}
                  className="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 text-sm text-zinc-900 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/30 disabled:bg-zinc-50 disabled:opacity-50"
                >
                  <option value="">Selecione</option>
                  {categorias.map((categoria) => (
                    <option key={categoria.id} value={categoria.id}>
                      {categoria.nome}
                    </option>
                  ))}
                </select>
                {categoriaCreatorOpen && (
                  <div className="space-y-2 rounded-md border border-orange-200 bg-orange-50/40 p-2">
                    <Input
                      placeholder="Nome da categoria"
                      value={categoriaDraft.nome}
                      error={Boolean(categoriaDraftError)}
                      onChange={(event) =>
                        setCategoriaDraft((current) => ({ ...current, nome: event.target.value }))
                      }
                      disabled={isWorking}
                    />
                    {categoriaDraftError && (
                      <span className="block text-[11px] font-medium text-red-600">
                        {categoriaDraftError}
                      </span>
                    )}
                    <textarea
                      placeholder="Descrição"
                      value={categoriaDraft.descricao}
                      rows={2}
                      onChange={(event) =>
                        setCategoriaDraft((current) => ({ ...current, descricao: event.target.value }))
                      }
                      disabled={isWorking}
                      className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/30 disabled:bg-zinc-50 disabled:opacity-50"
                    />
                    <div className="flex justify-end gap-1.5">
                      <Button
                        type="button"
                        variant="ghost"
                        size="xs"
                        disabled={isWorking}
                        onClick={() => {
                          setCategoriaCreatorOpen(false)
                          setCategoriaDraft(emptyCategoriaDraft)
                          setCategoriaSubmitted(false)
                        }}
                      >
                        Cancelar
                      </Button>
                      <Button
                        type="button"
                        size="xs"
                        loading={categoriaMutation.isPending}
                        disabled={isWorking}
                        onClick={() => {
                          setCategoriaSubmitted(true)
                          if (!categoriaDraft.nome.trim()) return
                          categoriaMutation.mutate()
                        }}
                      >
                        Criar
                      </Button>
                    </div>
                  </div>
                )}
                {showError("categoria") && (
                  <span className="block text-[11px] font-medium text-red-600">
                    {showError("categoria")}
                  </span>
                )}
              </div>

              <Field label="Código / SKU">
                <Input
                  value={form.sku}
                  onChange={(event) => updateField("sku", event.target.value)}
                  disabled={isWorking}
                />
              </Field>

              <Field label="Código de barras">
                <Input
                  value={form.codigo_barras}
                  onChange={(event) => updateField("codigo_barras", event.target.value)}
                  disabled={isWorking}
                />
              </Field>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-medium text-zinc-600">Unidade base</span>
                  <button
                    type="button"
                    onClick={() => setUnidadeCreatorOpen((value) => !value)}
                    disabled={isWorking}
                    className="inline-flex h-7 items-center gap-1 rounded-md border border-zinc-200 bg-white px-2 text-xs font-medium text-zinc-700 transition-colors hover:border-orange-300 hover:text-orange-700 disabled:opacity-50"
                  >
                    <Plus className="size-3" />
                    Nova
                  </button>
                </div>
                <select
                  aria-label="Unidade base"
                  value={form.unidade}
                  onChange={(event) => updateField("unidade", event.target.value)}
                  disabled={isWorking || unidadesQuery.isLoading}
                  className="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 text-sm text-zinc-900 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/30 disabled:bg-zinc-50 disabled:opacity-50"
                >
                  <option value="">Selecione</option>
                  {unidades.map((unidade) => (
                    <option key={unidade.id} value={unidade.id}>
                      {unidade.nome} ({unidade.sigla})
                    </option>
                  ))}
                </select>
                {unidadeCreatorOpen && (
                  <div className="space-y-2 rounded-md border border-orange-200 bg-orange-50/40 p-2">
                    <div className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_96px]">
                      <div>
                        <Input
                          placeholder="Nome da unidade"
                          value={unidadeDraft.nome}
                          error={Boolean(unidadeNomeError)}
                          onChange={(event) =>
                            setUnidadeDraft((current) => ({ ...current, nome: event.target.value }))
                          }
                          disabled={isWorking}
                        />
                        {unidadeNomeError && (
                          <span className="mt-1 block text-[11px] font-medium text-red-600">
                            {unidadeNomeError}
                          </span>
                        )}
                      </div>
                      <div>
                        <Input
                          placeholder="Sigla"
                          value={unidadeDraft.sigla}
                          maxLength={20}
                          error={Boolean(unidadeSiglaError)}
                          onChange={(event) =>
                            setUnidadeDraft((current) => ({
                              ...current,
                              sigla: event.target.value.toUpperCase(),
                            }))
                          }
                          disabled={isWorking}
                        />
                        {unidadeSiglaError && (
                          <span className="mt-1 block text-[11px] font-medium text-red-600">
                            {unidadeSiglaError}
                          </span>
                        )}
                      </div>
                    </div>
                    <textarea
                      placeholder="Descrição"
                      value={unidadeDraft.descricao}
                      rows={2}
                      onChange={(event) =>
                        setUnidadeDraft((current) => ({ ...current, descricao: event.target.value }))
                      }
                      disabled={isWorking}
                      className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/30 disabled:bg-zinc-50 disabled:opacity-50"
                    />
                    <div className="flex justify-end gap-1.5">
                      <Button
                        type="button"
                        variant="ghost"
                        size="xs"
                        disabled={isWorking}
                        onClick={() => {
                          setUnidadeCreatorOpen(false)
                          setUnidadeDraft(emptyUnidadeDraft)
                          setUnidadeSubmitted(false)
                        }}
                      >
                        Cancelar
                      </Button>
                      <Button
                        type="button"
                        size="xs"
                        loading={unidadeMutation.isPending}
                        disabled={isWorking}
                        onClick={() => {
                          setUnidadeSubmitted(true)
                          if (!unidadeDraft.nome.trim() || !unidadeDraft.sigla.trim()) return
                          unidadeMutation.mutate()
                        }}
                      >
                        Criar
                      </Button>
                    </div>
                  </div>
                )}
                {showError("unidade") && (
                  <span className="block text-[11px] font-medium text-red-600">
                    {showError("unidade")}
                  </span>
                )}
              </div>

              {!isEditing && (
                <div className="space-y-2 md:col-span-2">
                  <div>
                    <span className="text-xs font-medium text-zinc-600">Embalagem de compra</span>
                    <p className="text-[11px] text-zinc-400">Como este produto é comprado/fornecido? O sistema cria as formas de venda automaticamente.</p>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    <button
                      type="button"
                      disabled={isWorking}
                      onClick={() => setEmbalagemPreset(null)}
                      className={`rounded border px-2.5 py-1 text-xs font-medium transition-colors disabled:opacity-50 ${
                        embalagemPreset === null
                          ? "border-zinc-900 bg-zinc-900 text-white"
                          : "border-zinc-200 bg-zinc-50 text-zinc-700 hover:border-zinc-400"
                      }`}
                    >
                      Sem embalagem
                    </button>
                    {EMBALAGEM_PRESETS.map((preset) => (
                      <button
                        key={preset.key}
                        type="button"
                        disabled={isWorking}
                        onClick={() => applyEmbalagemPreset(preset)}
                        className={`rounded border px-2.5 py-1 text-xs font-medium transition-colors disabled:opacity-50 ${
                          embalagemPreset?.key === preset.key
                            ? "border-orange-600 bg-orange-600 text-white"
                            : "border-zinc-200 bg-zinc-50 text-zinc-700 hover:border-orange-300 hover:bg-orange-50 hover:text-orange-700"
                        }`}
                      >
                        {preset.label}
                      </button>
                    ))}
                  </div>
                  {embalagemPreset && (
                    <div className="rounded-md border border-blue-200 bg-blue-50 px-3 py-2.5 text-xs text-blue-900">
                      <p className="font-semibold">Estoque gerenciado em {embalagemPreset.baseUnidade}</p>
                      <ul className="mt-1 space-y-0.5 text-blue-700">
                        <li>· Entrada de 100 {embalagemPreset.label.toLowerCase()}s = {100 * Number(embalagemPreset.fator)} {embalagemPreset.baseUnidade} no estoque</li>
                        <li>· Venda de 1 {embalagemPreset.baseUnidade} baixa 1 {embalagemPreset.baseUnidade} do estoque</li>
                        <li>· Venda de 1 {embalagemPreset.label.toLowerCase()} baixa {embalagemPreset.fator} {embalagemPreset.baseUnidade} do estoque</li>
                      </ul>
                    </div>
                  )}
                </div>
              )}

              <Field label="Fornecedor">
                <select
                  value={form.fornecedor_principal}
                  onChange={(event) => updateField("fornecedor_principal", event.target.value)}
                  disabled={isWorking || fornecedoresQuery.isLoading}
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
                  disabled={isWorking}
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
                  disabled={isWorking}
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
                  disabled={isWorking}
                />
              </Field>

              <div className="rounded-md border border-yellow-200 bg-yellow-50/50 md:col-span-2">
                <button
                  type="button"
                  onClick={() => setFiscalAberto((v) => !v)}
                  className="flex w-full items-center justify-between px-3 py-2.5 text-left"
                >
                  <div>
                    <p className="text-xs font-bold text-zinc-800">Dados fiscais</p>
                    <p className="text-[11px] text-zinc-500">NCM, CFOP, alíquotas — necessário para NF-e</p>
                  </div>
                  <span className="text-xs text-zinc-500">{fiscalAberto ? "▲ Fechar" : "▼ Expandir"}</span>
                </button>
                {fiscalAberto && (
                <div className="space-y-4 border-t border-yellow-200 p-3">
                <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
                  <Field label="NCM" error={showError("ncm")}>
                    <Input
                      value={form.ncm}
                      maxLength={8}
                      error={Boolean(showError("ncm"))}
                      onChange={(event) => updateField("ncm", event.target.value.replace(/\D/g, ""))}
                      disabled={isWorking}
                    />
                  </Field>
                  <Field label="CFOP padrão" error={showError("cfop_padrao")}>
                    <Input
                      value={form.cfop_padrao}
                      maxLength={4}
                      error={Boolean(showError("cfop_padrao"))}
                      onChange={(event) => updateField("cfop_padrao", event.target.value.replace(/\D/g, ""))}
                      disabled={isWorking}
                    />
                  </Field>
                  <Field label="CST/CSOSN">
                    <Input
                      value={form.cst_csosn}
                      maxLength={4}
                      onChange={(event) => updateField("cst_csosn", event.target.value.toUpperCase())}
                      disabled={isWorking}
                    />
                  </Field>
                  <Field label="CEST" error={showError("cest")}>
                    <Input
                      value={form.cest}
                      maxLength={7}
                      error={Boolean(showError("cest"))}
                      onChange={(event) => updateField("cest", event.target.value.replace(/\D/g, ""))}
                      disabled={isWorking}
                    />
                  </Field>
                  <Field label="Origem" >
                    <select
                      value={form.origem_mercadoria}
                      onChange={(event) => updateField("origem_mercadoria", event.target.value)}
                      disabled={isWorking}
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
                      disabled={isWorking}
                    />
                  </Field>
                  <Field label="EAN tributável">
                    <Input
                      value={form.ean_tributavel}
                      onChange={(event) => updateField("ean_tributavel", event.target.value)}
                      disabled={isWorking}
                    />
                  </Field>
                  <Field label="Benefício fiscal">
                    <Input
                      value={form.codigo_beneficio_fiscal}
                      onChange={(event) => updateField("codigo_beneficio_fiscal", event.target.value.toUpperCase())}
                      disabled={isWorking}
                    />
                  </Field>
                  <Field label="ICMS %" error={showError("aliquota_icms")}>
                    <Input type="number" min="0" step="0.0001" value={form.aliquota_icms} onChange={(event) => updateField("aliquota_icms", event.target.value)} disabled={isWorking} />
                  </Field>
                  <Field label="IPI %" error={showError("aliquota_ipi")}>
                    <Input type="number" min="0" step="0.0001" value={form.aliquota_ipi} onChange={(event) => updateField("aliquota_ipi", event.target.value)} disabled={isWorking} />
                  </Field>
                  <Field label="PIS %" error={showError("aliquota_pis")}>
                    <Input type="number" min="0" step="0.0001" value={form.aliquota_pis} onChange={(event) => updateField("aliquota_pis", event.target.value)} disabled={isWorking} />
                  </Field>
                  <Field label="COFINS %" error={showError("aliquota_cofins")}>
                    <Input type="number" min="0" step="0.0001" value={form.aliquota_cofins} onChange={(event) => updateField("aliquota_cofins", event.target.value)} disabled={isWorking} />
                  </Field>
                </div>
                </div>
                )}
              </div>

              <div className="md:col-span-2">
                <Field label="Observação">
                  <textarea
                    value={form.descricao}
                    rows={3}
                    onChange={(event) => updateField("descricao", event.target.value)}
                    disabled={isWorking}
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
              disabled={isWorking}
              onClick={() => onOpenChange(false)}
            >
              Cancelar
            </Button>
            <Button
              type="button"
              size="sm"
              loading={mutation.isPending}
              disabled={isWorking}
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
