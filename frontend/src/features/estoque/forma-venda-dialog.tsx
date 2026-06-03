"use client"

import * as Dialog from "@radix-ui/react-dialog"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { AlertTriangle, Ruler, X, Zap } from "lucide-react"
import { useMemo, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useApiToast } from "@/hooks/use-api-toast"
import { estoqueService } from "@/services/estoque.service"
import { formasVendaService } from "@/services/formas-venda.service"
import type { FormaVendaProduto, FormaVendaProdutoPayload } from "@/types"

interface FormaVendaDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  produtoId: string
  unidadeBase: string
  forma?: FormaVendaProduto | null
}

interface FormaVendaFormState {
  nome: string
  codigo: string
  unidade: string
  fator_conversao: string
  preco_venda: string
  padrao: boolean
  ativo: boolean
  permite_fracionado: boolean
}

const emptyForm: FormaVendaFormState = {
  nome: "",
  codigo: "",
  unidade: "",
  fator_conversao: "1",
  preco_venda: "0",
  padrao: false,
  ativo: true,
  permite_fracionado: true,
}

// Presets rápidos de formas de venda comuns na construção civil
const PRESETS = [
  { label: "KG", nome: "Quilograma", unidade: "KG", fator: "1", permite_fracionado: true },
  { label: "Saco 50kg", nome: "Saco 50kg", unidade: "SACO", fator: "50", permite_fracionado: false },
  { label: "Metro", nome: "Metro", unidade: "M", fator: "1", permite_fracionado: true },
  { label: "Barra 6m", nome: "Barra 6m", unidade: "BARRA", fator: "6", permite_fracionado: false },
  { label: "Rolo 100m", nome: "Rolo 100m", unidade: "ROLO", fator: "100", permite_fracionado: false },
  { label: "Unidade", nome: "Unidade", unidade: "UN", fator: "1", permite_fracionado: false },
  { label: "Milheiro", nome: "Milheiro", unidade: "MILHEIRO", fator: "1000", permite_fracionado: false },
] as const

// Unidades granulares que deveriam ser a unidade base do produto
const UNIDADES_IDEAIS_BASE = new Set(["KG", "G", "M", "UN", "L", "ML", "M2", "M3"])

// Infere unidade e fator automaticamente a partir do nome digitado
function inferirSugestao(nome: string): { unidade: string; fator: string; permite_fracionado: boolean } | null {
  const n = nome.toLowerCase().trim()
  const sacoMatch = n.match(/saco\s*(\d+)\s*kg?/)
  if (sacoMatch) return { unidade: "SACO", fator: sacoMatch[1], permite_fracionado: false }
  const barraMatch = n.match(/barra\s*(\d+(?:[.,]\d+)?)\s*m?/)
  if (barraMatch) return { unidade: "BARRA", fator: barraMatch[1].replace(",", "."), permite_fracionado: false }
  const roloMatch = n.match(/rolo\s*(\d+(?:[.,]\d+)?)\s*m?/)
  if (roloMatch) return { unidade: "ROLO", fator: roloMatch[1].replace(",", "."), permite_fracionado: false }
  if (n.includes("milheiro")) return { unidade: "MILHEIRO", fator: "1000", permite_fracionado: false }
  return null
}

// Detecta quando a unidade base do produto pode estar errada (ex: base=SACO vendendo por KG)
function avisoUnidadeBase(unidadeForm: string, unidadeBase: string): { mensagem: string; sugestao: string } | null {
  const u = unidadeForm.toUpperCase().trim()
  const base = unidadeBase.toUpperCase().trim()
  if (!u || u === base) return null
  if (!UNIDADES_IDEAIS_BASE.has(u)) return null
  if (UNIDADES_IDEAIS_BASE.has(base)) return null
  return {
    mensagem: `A unidade base atual é ${base}. Para vender por ${u} e por ${base}, a unidade base deve ser ${u} — senão ${u} e ${base} viram a mesma coisa no estoque.`,
    sugestao: u,
  }
}

function formatFator(fator: number): string {
  if (!Number.isFinite(fator) || fator <= 0) return "?"
  return fator % 1 === 0 ? String(fator) : fator.toFixed(3).replace(/\.?0+$/, "")
}

function formFromForma(forma?: FormaVendaProduto | null): FormaVendaFormState {
  if (!forma) return emptyForm
  return {
    nome: forma.nome,
    codigo: forma.codigo ?? "",
    unidade: forma.unidade,
    fator_conversao: String(forma.fator_conversao),
    preco_venda: String(forma.preco_venda),
    padrao: forma.padrao,
    ativo: forma.ativo,
    permite_fracionado: forma.permite_fracionado,
  }
}

function normalizeDecimal(value: string, fallback = "0") {
  const trimmed = value.trim().replace(",", ".")
  return trimmed || fallback
}

export function FormaVendaDialog({
  open,
  onOpenChange,
  produtoId,
  unidadeBase,
  forma,
}: FormaVendaDialogProps) {
  const queryClient = useQueryClient()
  const toast = useApiToast()
  const [form, setForm] = useState<FormaVendaFormState>(emptyForm)
  const [submitted, setSubmitted] = useState(false)
  const [formKey, setFormKey] = useState("closed")
  const isEditing = Boolean(forma)
  const nextFormKey = open ? `${forma?.id ?? "nova"}:${forma?.updated_at ?? ""}` : "closed"

  if (formKey !== nextFormKey) {
    setFormKey(nextFormKey)
    setForm(formFromForma(forma))
    setSubmitted(false)
  }

  const validation = useMemo(() => {
    const errors: Partial<Record<keyof FormaVendaFormState, string>> = {}
    if (!form.nome.trim()) errors.nome = "Informe o nome."
    if (!form.unidade.trim()) errors.unidade = "Informe a unidade."
    if (Number(normalizeDecimal(form.fator_conversao)) <= 0) {
      errors.fator_conversao = "Fator deve ser maior que zero."
    }
    if (Number(normalizeDecimal(form.preco_venda)) < 0) {
      errors.preco_venda = "Preço não pode ser negativo."
    }
    return errors
  }, [form])

  const isValid = Object.keys(validation).length === 0

  const mutation = useMutation({
    mutationFn: () => {
      const payload: FormaVendaProdutoPayload = {
        produto: produtoId,
        nome: form.nome.trim(),
        codigo: form.codigo.trim(),
        unidade: form.unidade.trim().toUpperCase(),
        fator_conversao: normalizeDecimal(form.fator_conversao, "1"),
        preco_venda: normalizeDecimal(form.preco_venda),
        ativo: form.ativo,
        padrao: form.padrao,
        permite_fracionado: form.permite_fracionado,
      }

      if (isEditing) {
        return formasVendaService.update(forma!.id, {
          nome: payload.nome,
          codigo: payload.codigo,
          unidade: payload.unidade,
          fator_conversao: payload.fator_conversao,
          preco_venda: payload.preco_venda,
          permite_fracionado: payload.permite_fracionado,
        })
      }

      return formasVendaService.create(payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["estoque"] })
      toast.success(isEditing ? "Forma de venda atualizada" : "Forma de venda cadastrada")
      onOpenChange(false)
    },
    onError: (error) => toast.error(error),
  })

  const corrigirUnidadeMutation = useMutation({
    mutationFn: async (siglaDesejada: string) => {
      const resp = await estoqueService.unidades({ page_size: 100 })
      const unit = resp.results.find((u) => u.sigla.toUpperCase() === siglaDesejada.toUpperCase())
      if (!unit) throw new Error(`Unidade "${siglaDesejada}" não encontrada. Cadastre-a em Configurações.`)
      await estoqueService.update(produtoId, { unidade: unit.id })
    },
    onSuccess: (_, sigla) => {
      queryClient.invalidateQueries({ queryKey: ["estoque"] })
      toast.success(`Unidade base corrigida para ${sigla}. Agora defina os fatores de conversão.`)
      onOpenChange(false)
    },
    onError: (error) => toast.error(error),
  })

  const updateField = <K extends keyof FormaVendaFormState>(field: K, value: FormaVendaFormState[K]) => {
    setForm((current) => ({ ...current, [field]: value }))
  }

  const handleNomeChange = (nome: string) => {
    const sugestao = inferirSugestao(nome)
    if (sugestao && !isEditing) {
      setForm((current) => ({
        ...current,
        nome,
        unidade: sugestao.unidade,
        fator_conversao: sugestao.fator,
        permite_fracionado: sugestao.permite_fracionado,
      }))
    } else {
      updateField("nome", nome)
    }
  }

  const applyPreset = (preset: (typeof PRESETS)[number]) => {
    setForm((current) => ({
      ...current,
      nome: preset.nome,
      unidade: preset.unidade,
      fator_conversao: preset.fator,
      permite_fracionado: preset.permite_fracionado,
    }))
  }

  const showError = (field: keyof FormaVendaFormState) => submitted && validation[field]
  const fator = Number(normalizeDecimal(form.fator_conversao, "1"))
  const aviso = avisoUnidadeBase(form.unidade, unidadeBase)

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
          className="fixed left-1/2 top-1/2 z-50 w-[calc(100vw-24px)] max-w-xl -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-lg border border-zinc-200 bg-white shadow-xl focus:outline-none"
          aria-describedby={undefined}
        >
          <div className="flex items-center justify-between border-b border-zinc-100 px-5 py-4">
            <Dialog.Title className="flex items-center gap-2 text-sm font-semibold text-zinc-950">
              <Ruler className="size-4 text-orange-600" />
              {isEditing ? "Editar Forma de Venda" : "Cadastrar Forma de Venda"}
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

          <div className="space-y-4 px-5 py-4">
            {!isEditing && (
              <div>
                <div className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                  <Zap className="size-3" />
                  Atalhos rápidos
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {PRESETS.map((preset) => (
                    <button
                      key={preset.label}
                      type="button"
                      disabled={mutation.isPending}
                      onClick={() => applyPreset(preset)}
                      className="rounded border border-zinc-200 bg-zinc-50 px-2.5 py-1 text-xs font-medium text-zinc-700 transition-colors hover:border-orange-300 hover:bg-orange-50 hover:text-orange-700 disabled:opacity-50"
                    >
                      {preset.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <Field label="Nome" error={showError("nome")}>
                <Input
                  value={form.nome}
                  error={Boolean(showError("nome"))}
                  onChange={(event) => handleNomeChange(event.target.value)}
                  disabled={mutation.isPending}
                  placeholder="Ex: Saco 50kg, Barra 6m…"
                />
              </Field>

              <Field label="Código">
                <Input
                  value={form.codigo}
                  onChange={(event) => updateField("codigo", event.target.value)}
                  disabled={mutation.isPending}
                />
              </Field>

              <Field label="Unidade" error={showError("unidade")}>
                <Input
                  value={form.unidade}
                  error={Boolean(showError("unidade"))}
                  onChange={(event) => updateField("unidade", event.target.value.toUpperCase())}
                  disabled={mutation.isPending}
                  placeholder="Ex: SACO, KG, M, UN"
                />
              </Field>

              <Field label="Fator de conversão" error={showError("fator_conversao")}>
                <Input
                  type="number"
                  min="0.000001"
                  step="0.001"
                  value={form.fator_conversao}
                  error={Boolean(showError("fator_conversao"))}
                  onChange={(event) => updateField("fator_conversao", event.target.value)}
                  disabled={mutation.isPending}
                />
              </Field>

              <Field label="Preço de venda" error={showError("preco_venda")}>
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

              <div className="rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-600">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Resultado da conversão</p>
                <p className="mt-1 font-semibold text-zinc-900">
                  {form.unidade
                    ? `1 ${form.unidade} baixa ${formatFator(fator)} ${unidadeBase} do estoque`
                    : `1 forma baixa ${formatFator(fator)} ${unidadeBase} do estoque`}
                </p>
              </div>
            </div>

            {aviso && (
              <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs text-amber-900">
                <AlertTriangle className="mt-0.5 size-3.5 flex-shrink-0 text-amber-600" />
                <div className="flex-1 space-y-2">
                  <p>{aviso.mensagem}</p>
                  <Button
                    type="button"
                    size="xs"
                    variant="outline"
                    loading={corrigirUnidadeMutation.isPending}
                    disabled={mutation.isPending || corrigirUnidadeMutation.isPending}
                    onClick={() => corrigirUnidadeMutation.mutate(aviso.sugestao)}
                  >
                    Corrigir unidade base para {aviso.sugestao}
                  </Button>
                </div>
              </div>
            )}

            <div className="flex flex-wrap gap-4 border-t border-zinc-100 pt-4">
              {!isEditing && (
                <label className="flex items-center gap-2 text-xs font-medium text-zinc-700">
                  <input
                    type="checkbox"
                    checked={form.padrao}
                    onChange={(event) => updateField("padrao", event.target.checked)}
                    disabled={mutation.isPending}
                    className="rounded border-zinc-300 text-orange-600 focus:ring-orange-500/20"
                  />
                  Padrão
                </label>
              )}
              {!isEditing && (
                <label className="flex items-center gap-2 text-xs font-medium text-zinc-700">
                  <input
                    type="checkbox"
                    checked={form.ativo}
                    onChange={(event) => updateField("ativo", event.target.checked)}
                    disabled={mutation.isPending}
                    className="rounded border-zinc-300 text-orange-600 focus:ring-orange-500/20"
                  />
                  Ativa
                </label>
              )}
              <label className="flex items-center gap-2 text-xs font-medium text-zinc-700">
                <input
                  type="checkbox"
                  checked={form.permite_fracionado}
                  onChange={(event) => updateField("permite_fracionado", event.target.checked)}
                  disabled={mutation.isPending}
                  className="rounded border-zinc-300 text-orange-600 focus:ring-orange-500/20"
                />
                Permite fracionado
              </label>
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
              Salvar Forma
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
