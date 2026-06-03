"use client"

import * as Dialog from "@radix-ui/react-dialog"
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { TrendingDown, TrendingUp, X } from "lucide-react"
import { useEffect } from "react"
import { useForm, useWatch } from "react-hook-form"
import { z } from "zod"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useApiToast } from "@/hooks/use-api-toast"
import { createIdempotencyKey } from "@/lib/idempotency"
import { normalizeApiError } from "@/services/api"
import { financeiroService } from "@/services/financeiro.service"
import type { CriarLancamentoPayload, FormaPagamento, TipoLancamento } from "@/types"

const FORMAS: { value: FormaPagamento; label: string }[] = [
  { value: "PIX", label: "PIX" },
  { value: "DINHEIRO", label: "Dinheiro" },
  { value: "CARTAO", label: "Cartão" },
  { value: "TRANSFERENCIA", label: "Transferência" },
  { value: "BOLETO", label: "Boleto" },
  { value: "OUTRO", label: "Outro" },
]

const schema = z.object({
  tipo: z.enum(["ENTRADA", "SAIDA"]),
  conta_financeira: z.string().min(1, "Selecione a conta."),
  categoria: z.string().min(1, "Selecione a categoria."),
  valor: z.number().min(0.01, "Valor deve ser maior que zero."),
  forma_pagamento: z.enum(["PIX", "DINHEIRO", "CARTAO", "TRANSFERENCIA", "BOLETO", "OUTRO"]),
  descricao: z.string().optional(),
})

type FormData = z.infer<typeof schema>

function fieldFromApi(field: string): keyof FormData | null {
  const map: Record<string, keyof FormData> = {
    conta_financeira: "conta_financeira",
    categoria: "categoria",
    valor: "valor",
    forma_pagamento: "forma_pagamento",
    descricao: "descricao",
  }
  return map[field] ?? null
}

interface NovaLancamentoDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  tipoInicial?: TipoLancamento
}

export function NovaLancamentoDialog({
  open,
  onOpenChange,
  tipoInicial = "ENTRADA",
}: NovaLancamentoDialogProps) {
  const queryClient = useQueryClient()
  const toast = useApiToast()

  const form = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      tipo: tipoInicial,
      conta_financeira: "",
      categoria: "",
      valor: 0,
      forma_pagamento: "PIX",
      descricao: "",
    },
  })

  const tipo = useWatch({ control: form.control, name: "tipo" })
  const formaPagamento = useWatch({ control: form.control, name: "forma_pagamento" })

  useEffect(() => {
    if (open) {
      form.setValue("tipo", tipoInicial)
      form.setValue("categoria", "")
    }
  }, [open, tipoInicial, form])

  // Reset categoria when tipo changes
  useEffect(() => {
    form.setValue("categoria", "")
  }, [tipo, form])

  const contasQuery = useQuery({
    queryKey: ["financeiro", "contas-financeiras"],
    queryFn: () => financeiroService.contasFinanceiras({ page_size: 100 }),
    staleTime: 60_000,
    enabled: open,
  })
  const contas = (contasQuery.data?.results ?? []).filter((c) => c.ativo)

  const categoriasQuery = useQuery({
    queryKey: ["financeiro", "categorias"],
    queryFn: () => financeiroService.categorias({ page_size: 100 }),
    staleTime: 60_000,
    enabled: open,
  })
  const categorias = (categoriasQuery.data?.results ?? []).filter((c) => {
    const tipoCategoria = tipo === "ENTRADA" ? "RECEITA" : "DESPESA"
    return c.tipo === tipoCategoria && c.ativa
  })

  const mutation = useMutation({
    mutationFn: (data: FormData) => {
      const payload: CriarLancamentoPayload = {
        conta_financeira: data.conta_financeira,
        categoria: data.categoria,
        tipo: data.tipo,
        valor: data.valor.toFixed(2),
        forma_pagamento: data.forma_pagamento,
        descricao: data.descricao ?? "",
        idempotency_key: createIdempotencyKey(`lancamento:${data.tipo}`),
      }
      return financeiroService.criarLancamento(payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["financeiro"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
      toast.success(tipo === "ENTRADA" ? "Receita registrada." : "Despesa registrada.")
      form.reset({ tipo: tipoInicial, conta_financeira: "", categoria: "", valor: 0, forma_pagamento: "PIX", descricao: "" })
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

  const errors = form.formState.errors
  const isEntrada = tipo === "ENTRADA"
  const title = tipoInicial === "ENTRADA" ? "Nova Receita" : "Nova Despesa"

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
            <div className="flex items-center gap-2">
              {isEntrada ? (
                <TrendingUp className="size-4 text-green-600" />
              ) : (
                <TrendingDown className="size-4 text-red-500" />
              )}
              <Dialog.Title className="text-sm font-semibold text-zinc-900">{title}</Dialog.Title>
            </div>
            <Dialog.Close asChild>
              <button className="text-zinc-400 transition-colors hover:text-zinc-600">
                <X className="size-4" />
              </button>
            </Dialog.Close>
          </div>

          <form
            onSubmit={form.handleSubmit((data) => mutation.mutate(data))}
            className="mt-4 space-y-4"
          >
            {/* Tipo toggle (só visível quando aberto genericamente) */}
            <input type="hidden" {...form.register("tipo")} />

            {/* Conta financeira */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-600">
                {isEntrada ? "Conta de entrada" : "Conta de saída"}
              </label>
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
                    <option key={c.id} value={c.id}>{c.nome}</option>
                  ))}
                </select>
              )}
              {errors.conta_financeira && (
                <p className="text-xs text-red-600">{errors.conta_financeira.message}</p>
              )}
            </div>

            {/* Categoria */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-600">Categoria</label>
              {categoriasQuery.isLoading ? (
                <div className="h-9 animate-pulse rounded-md bg-zinc-100" />
              ) : categorias.length === 0 ? (
                <div className="rounded-md border border-dashed border-zinc-200 px-3 py-2 text-xs text-zinc-400">
                  Nenhuma categoria de {isEntrada ? "receita" : "despesa"} cadastrada.
                </div>
              ) : (
                <select
                  className={`h-9 w-full rounded-md border px-3 text-sm bg-white text-zinc-900 focus:outline-none focus:ring-2 focus:ring-orange-500/30 focus:border-orange-500 transition-colors ${
                    errors.categoria ? "border-red-500" : "border-zinc-300"
                  }`}
                  {...form.register("categoria")}
                >
                  <option value="">Selecione...</option>
                  {categorias.map((c) => (
                    <option key={c.id} value={c.id}>{c.nome}</option>
                  ))}
                </select>
              )}
              {errors.categoria && <p className="text-xs text-red-600">{errors.categoria.message}</p>}
            </div>

            {/* Valor */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-600">Valor</label>
              <Input
                type="number"
                step="0.01"
                min="0.01"
                placeholder="0,00"
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
            </div>

            {/* Descrição */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-600">Descrição <span className="text-zinc-400">(opcional)</span></label>
              <Input placeholder="Ex: venda de materiais à vista" {...form.register("descricao")} />
            </div>

            <div className="flex justify-end gap-2 border-t border-zinc-100 pt-3">
              <Dialog.Close asChild>
                <Button type="button" variant="outline" size="sm">Cancelar</Button>
              </Dialog.Close>
              <Button
                type="submit"
                size="sm"
                loading={mutation.isPending}
                className={isEntrada ? "bg-green-600 hover:bg-green-700 text-white border-transparent" : ""}
                variant={isEntrada ? "primary" : "danger"}
              >
                {isEntrada ? "Registrar Receita" : "Registrar Despesa"}
              </Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
