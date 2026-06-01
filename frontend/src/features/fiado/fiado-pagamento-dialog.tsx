"use client"

import * as Dialog from "@radix-ui/react-dialog"
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { X } from "lucide-react"
import { useEffect } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useApiToast } from "@/hooks/use-api-toast"
import { formatCurrency } from "@/lib/utils"
import { toNumber } from "@/lib/format"
import { createIdempotencyKey } from "@/lib/idempotency"
import { normalizeApiError } from "@/services/api"
import { fiadoService } from "@/services/fiado.service"
import type { ContaFiado, FormaPagamentoFiado, PagamentoFiadoPayload } from "@/types"

const formasPagamento: { value: FormaPagamentoFiado; label: string }[] = [
  { value: "DINHEIRO", label: "Dinheiro" },
  { value: "PIX", label: "PIX" },
  { value: "CARTAO", label: "Cartão" },
  { value: "BOLETO", label: "Boleto" },
  { value: "TRANSFERENCIA", label: "Transferência" },
  { value: "OUTRO", label: "Outro" },
]

const pagamentoSchema = z.object({
  valor: z.number().min(0.01, "Informe um valor maior que zero."),
  forma_pagamento: z.enum(["DINHEIRO", "PIX", "CARTAO", "BOLETO", "TRANSFERENCIA", "OUTRO"]),
  observacao: z.string().optional(),
})

type PagamentoFormData = z.infer<typeof pagamentoSchema>

interface FiadoPagamentoDialogProps {
  conta: ContaFiado
  open: boolean
  onOpenChange: (open: boolean) => void
}

function firstMessage(value: string | string[]) {
  return Array.isArray(value) ? value[0] : value
}

function fieldNameFromApi(field: string): keyof PagamentoFormData | null {
  const map: Record<string, keyof PagamentoFormData> = {
    valor: "valor",
    forma_pagamento: "forma_pagamento",
    observacao: "observacao",
  }
  return map[field] ?? null
}

export function FiadoPagamentoDialog({ conta, open, onOpenChange }: FiadoPagamentoDialogProps) {
  const queryClient = useQueryClient()
  const toast = useApiToast()

  const form = useForm<PagamentoFormData>({
    resolver: zodResolver(pagamentoSchema),
    defaultValues: {
      valor: 0,
      forma_pagamento: "PIX",
      observacao: "",
    },
  })

  useEffect(() => {
    if (!open) return

    form.reset({
      valor: toNumber(conta.valor_restante),
      forma_pagamento: "PIX",
      observacao: "",
    })
  }, [conta.valor_restante, form, open])

  const mutation = useMutation({
    mutationFn: (data: PagamentoFormData) => {
      const payload: PagamentoFiadoPayload = {
        valor: data.valor.toFixed(2),
        forma_pagamento: data.forma_pagamento,
        observacao: data.observacao ?? "",
        idempotency_key: createIdempotencyKey(`fiado-pagamento:${conta.id}`),
      }
      return fiadoService.registrarPagamento(conta.id, payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fiado"] })
      queryClient.invalidateQueries({ queryKey: ["financeiro"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
      queryClient.invalidateQueries({ queryKey: ["clientes"] })
      toast.success("Pagamento registrado")
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
  const disabled = conta.status !== "ABERTA" || toNumber(conta.valor_restante) <= 0

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px] transition-all duration-150 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 z-50 w-full max-w-lg -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-xl border border-zinc-200 bg-white p-5 shadow-xl focus:outline-none"
          aria-describedby={undefined}
        >
          <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
            <Dialog.Title className="text-sm font-semibold text-zinc-900">Registrar Pagamento</Dialog.Title>
            <Dialog.Close asChild>
              <button className="text-zinc-400 transition-colors hover:text-zinc-600">
                <X className="size-4" />
              </button>
            </Dialog.Close>
          </div>

          <form onSubmit={form.handleSubmit((data) => mutation.mutate(data))} className="space-y-4 pt-4">
            <div className="rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-600">
              Restante da conta: <span className="font-semibold text-zinc-900">{formatCurrency(conta.valor_restante)}</span>
            </div>

            {disabled && (
              <div className="rounded-md border border-yellow-200 bg-yellow-50 px-3 py-2 text-xs text-yellow-800">
                Esta conta não está aberta para novos pagamentos.
              </div>
            )}

            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <div className="space-y-1">
                <label className="text-xs font-medium text-zinc-600">Valor</label>
                <Input
                  type="number"
                  step="0.01"
                  min="0.01"
                  disabled={disabled}
                  error={Boolean(errors.valor)}
                  {...form.register("valor", { valueAsNumber: true })}
                />
                {errors.valor && <p className="text-xs text-red-600">{errors.valor.message}</p>}
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-zinc-600">Forma de Pagamento</label>
                <select
                  className="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 text-sm text-zinc-900 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/30 disabled:bg-zinc-50 disabled:opacity-60"
                  disabled={disabled}
                  {...form.register("forma_pagamento")}
                >
                  {formasPagamento.map((forma) => (
                    <option key={forma.value} value={forma.value}>
                      {forma.label}
                    </option>
                  ))}
                </select>
                {errors.forma_pagamento && <p className="text-xs text-red-600">{errors.forma_pagamento.message}</p>}
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-medium text-zinc-600">Observação</label>
              <Input disabled={disabled} {...form.register("observacao")} />
            </div>

            <div className="flex justify-end gap-2 border-t border-zinc-100 pt-3">
              <Dialog.Close asChild>
                <Button type="button" variant="outline" size="sm">
                  Cancelar
                </Button>
              </Dialog.Close>
              <Button type="submit" size="sm" loading={mutation.isPending} disabled={disabled}>
                Registrar
              </Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
