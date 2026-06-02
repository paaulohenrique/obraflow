"use client"

import * as Dialog from "@radix-ui/react-dialog"
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { PackagePlus, X } from "lucide-react"
import { useEffect, useMemo } from "react"
import { useForm, useWatch } from "react-hook-form"
import { z } from "zod"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useApiToast } from "@/hooks/use-api-toast"
import { createIdempotencyKey } from "@/lib/idempotency"
import { formatCurrency } from "@/lib/utils"
import { formatNumber, toNumber } from "@/lib/format"
import { normalizeApiError } from "@/services/api"
import { estoqueService } from "@/services/estoque.service"
import { fiadoService } from "@/services/fiado.service"
import type { ContaFiado, ItemFiadoPayload } from "@/types"

const itemSchema = z.object({
  produto: z.string().min(1, "Selecione o produto."),
  forma_venda: z.string().min(1, "Selecione a forma de venda."),
  quantidade: z.number().min(0.001, "Informe uma quantidade maior que zero."),
  preco_unitario: z.number().min(0, "Informe um preço válido."),
  observacao: z.string().optional(),
})

type ItemFormData = z.infer<typeof itemSchema>

interface FiadoItemDialogProps {
  conta: ContaFiado
  open: boolean
  onOpenChange: (open: boolean) => void
}

function firstMessage(value: string | string[]) {
  return Array.isArray(value) ? value[0] : value
}

function fieldNameFromApi(field: string): keyof ItemFormData | null {
  const map: Record<string, keyof ItemFormData> = {
    produto: "produto",
    forma_venda: "forma_venda",
    quantidade: "quantidade",
    quantidade_informada: "quantidade",
    preco_unitario: "preco_unitario",
    observacao: "observacao",
  }
  return map[field] ?? null
}

export function FiadoItemDialog({ conta, open, onOpenChange }: FiadoItemDialogProps) {
  const queryClient = useQueryClient()
  const toast = useApiToast()

  const form = useForm<ItemFormData>({
    resolver: zodResolver(itemSchema),
    defaultValues: {
      produto: "",
      forma_venda: "",
      quantidade: 1,
      preco_unitario: 0,
      observacao: "",
    },
  })

  const produtoId = useWatch({ control: form.control, name: "produto" })
  const formaVendaId = useWatch({ control: form.control, name: "forma_venda" })
  const quantidade = useWatch({ control: form.control, name: "quantidade" })
  const precoUnitario = useWatch({ control: form.control, name: "preco_unitario" })

  const produtosQuery = useQuery({
    queryKey: ["estoque", "produtos", "fiado-select"],
    queryFn: () => estoqueService.list({ page_size: 100, ordering: "nome" }),
    enabled: open,
  })

  const formasQuery = useQuery({
    queryKey: ["estoque", "formas-venda", produtoId],
    queryFn: () => estoqueService.formasVenda({ produto: produtoId, page_size: 100 }),
    enabled: open && Boolean(produtoId),
  })

  const produtos = useMemo(
    () => (produtosQuery.data?.results ?? []).filter((produto) => produto.is_active),
    [produtosQuery.data?.results]
  )
  const formasVenda = useMemo(
    () => (formasQuery.data?.results ?? []).filter((forma) => forma.ativo && forma.is_active),
    [formasQuery.data?.results]
  )
  const produto = produtos.find((item) => item.id === produtoId)
  const formaVenda = formasVenda.find((item) => item.id === formaVendaId)
  const quantidadeConvertida = formaVenda ? toNumber(quantidade) * toNumber(formaVenda.fator_conversao) : 0

  useEffect(() => {
    if (!open) {
      form.reset({
        produto: "",
        forma_venda: "",
        quantidade: 1,
        preco_unitario: 0,
        observacao: "",
      })
    }
  }, [form, open])

  useEffect(() => {
    form.setValue("forma_venda", "")
    form.clearErrors(["forma_venda", "quantidade"])
    if (produto) {
      form.setValue("preco_unitario", toNumber(produto.preco_venda))
    }
  }, [form, produto, produtoId])

  useEffect(() => {
    if (!formaVenda) return
    const preco = toNumber(formaVenda.preco_venda)
    form.setValue("preco_unitario", preco > 0 ? preco : toNumber(produto?.preco_venda))
    form.clearErrors("forma_venda")
  }, [form, formaVenda, produto?.preco_venda])

  const mutation = useMutation({
    mutationFn: (data: ItemFormData) => {
      const payload: ItemFiadoPayload = {
        produto: data.produto,
        forma_venda: data.forma_venda,
        quantidade_informada: data.quantidade.toFixed(3),
        preco_unitario: data.preco_unitario.toFixed(2),
        observacao: data.observacao ?? "",
        idempotency_key: createIdempotencyKey(`fiado-item:${conta.id}`),
      }
      return fiadoService.adicionarItem(conta.id, payload)
    },
    onSuccess: (item) => {
      queryClient.invalidateQueries({ queryKey: ["fiado"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
      queryClient.invalidateQueries({ queryKey: ["clientes"] })
      queryClient.invalidateQueries({ queryKey: ["estoque"] })
      queryClient.invalidateQueries({ queryKey: ["estoque", "produtos", item.produto] })
      toast.success("Item adicionado")
      onOpenChange(false)
    },
    onError: (error) => {
      const apiError = normalizeApiError(error)
      let handled = false

      for (const [field, messages] of Object.entries(apiError.errors ?? {})) {
        const formField = fieldNameFromApi(field)
        if (!formField) continue
        form.setError(formField, { message: firstMessage(messages) })
        handled = true
      }

      if (!handled) toast.error(error)
    },
  })

  const errors = form.formState.errors
  const disabled = conta.status !== "ABERTA"

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px] transition-all duration-150 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 z-50 w-full max-w-2xl -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-xl border border-zinc-200 bg-white p-5 shadow-xl focus:outline-none"
          aria-describedby={undefined}
        >
          <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
            <Dialog.Title className="text-sm font-semibold text-zinc-900">Adicionar Item</Dialog.Title>
            <Dialog.Close asChild>
              <button className="text-zinc-400 transition-colors hover:text-zinc-600">
                <X className="size-4" />
              </button>
            </Dialog.Close>
          </div>

          <form onSubmit={form.handleSubmit((data) => mutation.mutate(data))} className="space-y-4 pt-4">
            {disabled && (
              <div className="rounded-md border border-yellow-200 bg-yellow-50 px-3 py-2 text-xs text-yellow-800">
                Esta conta não está aberta para novos itens.
              </div>
            )}

            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <div className="space-y-1">
                <label className="text-xs font-medium text-zinc-600">Produto</label>
                <select
                  className="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 text-sm text-zinc-900 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/30 disabled:bg-zinc-50 disabled:opacity-60"
                  disabled={disabled || produtosQuery.isLoading}
                  {...form.register("produto")}
                >
                  <option value="">Selecione</option>
                  {produtos.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.nome} · {formatNumber(item.estoque_atual, 3)} {item.unidade_sigla}
                    </option>
                  ))}
                </select>
                {errors.produto && <p className="text-xs text-red-600">{errors.produto.message}</p>}
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-zinc-600">Forma de Venda</label>
                <select
                  className="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 text-sm text-zinc-900 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/30 disabled:bg-zinc-50 disabled:opacity-60"
                  disabled={disabled || !produtoId || formasQuery.isLoading}
                  {...form.register("forma_venda")}
                >
                  <option value="">Selecione</option>
                  {formasVenda.map((forma) => (
                    <option key={forma.id} value={forma.id}>
                      {forma.nome} · x{formatNumber(forma.fator_conversao, 3)}
                    </option>
                  ))}
                </select>
                {errors.forma_venda && <p className="text-xs text-red-600">{errors.forma_venda.message}</p>}
              </div>
            </div>

            <div className="grid grid-cols-1 gap-3 md:grid-cols-[1fr_1fr_1.2fr]">
              <div className="space-y-1">
                <label className="text-xs font-medium text-zinc-600">Quantidade</label>
                <Input
                  type="number"
                  step="0.001"
                  min="0.001"
                  disabled={disabled}
                  error={Boolean(errors.quantidade)}
                  {...form.register("quantidade", { valueAsNumber: true })}
                />
                {errors.quantidade && <p className="text-xs text-red-600">{errors.quantidade.message}</p>}
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-zinc-600">Preço unitário base</label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  disabled={disabled}
                  error={Boolean(errors.preco_unitario)}
                  {...form.register("preco_unitario", { valueAsNumber: true })}
                />
                {errors.preco_unitario && <p className="text-xs text-red-600">{errors.preco_unitario.message}</p>}
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-zinc-600">Observação</label>
                <Input disabled={disabled} {...form.register("observacao")} />
              </div>
            </div>

            {produto && formaVenda && (
              <div className="rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-600">
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                  <PackagePlus className="size-3.5 text-orange-500" />
                  <span>
                    {formatNumber(quantidade, 3)} {formaVenda.unidade} x {formatNumber(formaVenda.fator_conversao, 3)} {produto.unidade_sigla} =
                  </span>
                  <span className="font-semibold text-zinc-900">
                    {formatNumber(quantidadeConvertida, 3)} {produto.unidade_sigla}
                  </span>
                  <span>· saldo atual {formatNumber(produto.estoque_atual, 3)} {produto.unidade_sigla}</span>
                  <span>· preço {formatCurrency(precoUnitario)}/{produto.unidade_sigla}</span>
                </div>
              </div>
            )}

            {produtoId && !formasQuery.isLoading && formasVenda.length === 0 && (
              <div className="rounded-md border border-yellow-200 bg-yellow-50 px-3 py-2 text-xs text-yellow-800">
                Nenhuma forma de venda ativa para este produto.
              </div>
            )}

            <div className="flex justify-end gap-2 border-t border-zinc-100 pt-3">
              <Dialog.Close asChild>
                <Button type="button" variant="outline" size="sm">
                  Cancelar
                </Button>
              </Dialog.Close>
              <Button type="submit" size="sm" loading={mutation.isPending} disabled={disabled}>
                Adicionar
              </Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
