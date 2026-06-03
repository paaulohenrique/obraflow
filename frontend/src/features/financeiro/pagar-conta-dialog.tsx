"use client"

import * as Dialog from "@radix-ui/react-dialog"
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { X } from "lucide-react"
import { useForm, useWatch } from "react-hook-form"
import { z } from "zod"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useApiToast } from "@/hooks/use-api-toast"
import { createIdempotencyKey } from "@/lib/idempotency"
import { formatCurrency } from "@/lib/utils"
import { normalizeApiError } from "@/services/api"
import { financeiroService } from "@/services/financeiro.service"
import type { ContaPagar, FormaPagamento, PagarContaPagarPayload } from "@/types"

const FORMAS: { value: FormaPagamento; label: string }[] = [
  { value: "PIX", label: "PIX" },
  { value: "DINHEIRO", label: "Dinheiro" },
  { value: "CARTAO", label: "Cartão" },
  { value: "TRANSFERENCIA", label: "Transferência" },
  { value: "BOLETO", label: "Boleto" },
  { value: "OUTRO", label: "Outro" },
]

const schema = z.object({
  conta_financeira: z.string().min(1, "Selecione a conta."),
  valor: z.number().min(0.01, "Valor deve ser maior que zero."),
  forma_pagamento: z.enum(["PIX", "DINHEIRO", "CARTAO", "TRANSFERENCIA", "BOLETO", "OUTRO"]),
  descricao: z.string().optional(),
})

type FormData = z.infer<typeof schema>

function fieldFromApi(field: string): keyof FormData | null {
  const map: Record<string, keyof FormData> = {
    conta_financeira: "conta_financeira",
    valor: "valor",
    forma_pagamento: "forma_pagamento",
    descricao: "descricao",
  }
  return map[field] ?? null
}

interface PagarContaDialogProps {
  conta: ContaPagar
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function PagarContaDialog({ conta, open, onOpenChange }: PagarContaDialogProps) {
  const queryClient = useQueryClient()
  const toast = useApiToast()

  const contasQuery = useQuery({
    queryKey: ["financeiro", "contas-financeiras"],
    queryFn: () => financeiroService.contasFinanceiras({ page_size: 100 }),
    staleTime: 60_000,
    enabled: open,
  })
  const contas = (contasQuery.data?.results ?? []).filter((c) => c.ativo)

  const form = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      conta_financeira: "",
      valor: Number(conta.valor_restante),
      forma_pagamento: "PIX",
      descricao: "",
    },
  })

  const mutation = useMutation({
    mutationFn: (data: FormData) => {
      const payload: PagarContaPagarPayload = {
        conta_financeira: data.conta_financeira,
        valor: data.valor.toFixed(2),
        forma_pagamento: data.forma_pagamento,
        descricao: data.descricao ?? "",
        idempotency_key: createIdempotencyKey(`pagar-conta:${conta.id}`),
      }
      return financeiroService.pagarContaPagar(conta.id, payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["financeiro"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
      toast.success("Pagamento registrado com sucesso.")
      onOpenChange(false)
    },
    onError: (error) => {
      const apiError = normalizeApiError(error)
      let handled = false
      for (const [field, messages] of Object.entries(apiError.errors ?? {})) {
        const f = fieldFromApi(field)
        if (!f) continue
        form.setError(f, { message: Array.isArray(messages) ? messages[0] : messages })
        handled = true
      }
      if (!handled) toast.error(error)
    },
  })

  const formaPagamento = useWatch({ control: form.control, name: "forma_pagamento" })
  const errors = form.formState.errors
  const valorRestante = Number(conta.valor_restante)

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(next) => {
        if (!next) form.reset()
        onOpenChange(next)
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px] data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-xl border border-zinc-200 bg-white p-5 shadow-xl focus:outline-none"
          aria-describedby={undefined}
        >
          <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
            <Dialog.Title className="text-sm font-semibold text-zinc-900">Baixar Conta</Dialog.Title>
            <Dialog.Close asChild>
              <button className="text-zinc-400 transition-colors hover:text-zinc-600">
                <X className="size-4" />
              </button>
            </Dialog.Close>
          </div>

          {/* Resumo da conta */}
          <div className="mt-4 rounded-lg border border-zinc-100 bg-zinc-50 px-4 py-3 text-xs">
            <p className="font-medium text-zinc-800 truncate">{conta.descricao}</p>
            <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-zinc-500">
              <span>Total: <span className="font-semibold text-zinc-700">{formatCurrency(conta.valor_total)}</span></span>
              <span>Pago: <span className="font-semibold text-zinc-700">{formatCurrency(conta.valor_pago)}</span></span>
              <span>Restante: <span className="font-semibold text-orange-600">{formatCurrency(conta.valor_restante)}</span></span>
            </div>
          </div>

          <form
            onSubmit={form.handleSubmit((data) => mutation.mutate(data))}
            className="mt-4 space-y-4"
          >
            {/* Conta financeira */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-600">Conta de saída</label>
              {contasQuery.isLoading ? (
                <div className="h-9 animate-pulse rounded-md bg-zinc-100" />
              ) : (
                <select
                  className={`h-9 w-full rounded-md border px-3 text-sm bg-white text-zinc-900 focus:outline-none focus:ring-2 focus:ring-orange-500/30 focus:border-orange-500 transition-colors ${
                    errors.conta_financeira ? "border-red-500" : "border-zinc-300"
                  }`}
                  {...form.register("conta_financeira")}
                >
                  <option value="">Selecione...</option>
                  {contas.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.nome} — {formatCurrency(c.saldo_atual)}
                    </option>
                  ))}
                </select>
              )}
              {errors.conta_financeira && (
                <p className="text-xs text-red-600">{errors.conta_financeira.message}</p>
              )}
            </div>

            {/* Valor */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-600">
                Valor pago <span className="text-zinc-400">(máx. {formatCurrency(valorRestante)})</span>
              </label>
              <Input
                type="number"
                step="0.01"
                min="0.01"
                max={valorRestante}
                error={Boolean(errors.valor)}
                {...form.register("valor", { valueAsNumber: true })}
              />
              {errors.valor && <p className="text-xs text-red-600">{errors.valor.message}</p>}
            </div>

            {/* Forma de pagamento */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-600">Forma de pagamento</label>
              <div className="grid grid-cols-3 gap-1.5">
                {FORMAS.map(({ value, label }) => (
                    <button
                      key={value}
                      type="button"
                      onClick={() => form.setValue("forma_pagamento", value, { shouldValidate: true })}
                      className={`rounded-md border px-2 py-1.5 text-xs font-medium transition-colors ${
                        formaPagamento === value
                          ? "border-orange-300 bg-orange-50 text-orange-700 ring-1 ring-orange-100"
                          : "border-zinc-200 text-zinc-600 hover:border-zinc-300 hover:bg-zinc-50"
                      }`}
                    >
                      {label}
                    </button>
                ))}
              </div>
              {errors.forma_pagamento && (
                <p className="text-xs text-red-600">{errors.forma_pagamento.message}</p>
              )}
            </div>

            {/* Observação */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-600">Observação <span className="text-zinc-400">(opcional)</span></label>
              <Input placeholder="Ex: boleto bancário ref. março" {...form.register("descricao")} />
            </div>

            <div className="flex justify-end gap-2 border-t border-zinc-100 pt-3">
              <Dialog.Close asChild>
                <Button type="button" variant="outline" size="sm">
                  Cancelar
                </Button>
              </Dialog.Close>
              <Button type="submit" size="sm" loading={mutation.isPending}>
                Confirmar Pagamento
              </Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
