"use client"

import * as Dialog from "@radix-ui/react-dialog"
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { X } from "lucide-react"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useApiToast } from "@/hooks/use-api-toast"
import { normalizeApiError } from "@/services/api"
import { financeiroService } from "@/services/financeiro.service"
import type { CriarContaPagarPayload } from "@/types"

const today = () => new Date().toISOString().split("T")[0]

const schema = z.object({
  descricao: z.string().min(1, "Descrição obrigatória."),
  categoria: z.string().min(1, "Selecione a categoria."),
  valor_total: z.number().min(0.01, "Valor deve ser maior que zero."),
  data_vencimento: z.string().min(1, "Informe o vencimento."),
  observacao: z.string().optional(),
})

type FormData = z.infer<typeof schema>

function fieldFromApi(field: string): keyof FormData | null {
  const map: Record<string, keyof FormData> = {
    descricao: "descricao",
    categoria: "categoria",
    valor_total: "valor_total",
    data_vencimento: "data_vencimento",
    observacao: "observacao",
  }
  return map[field] ?? null
}

interface NovaContaPagarDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function NovaContaPagarDialog({ open, onOpenChange }: NovaContaPagarDialogProps) {
  const queryClient = useQueryClient()
  const toast = useApiToast()

  const categoriasQuery = useQuery({
    queryKey: ["financeiro", "categorias", "despesa"],
    queryFn: () => financeiroService.categorias({ page_size: 100 }),
    staleTime: 60_000,
    enabled: open,
  })
  const categorias = (categoriasQuery.data?.results ?? []).filter(
    (c) => c.tipo === "DESPESA" && c.ativa
  )

  const form = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      descricao: "",
      categoria: "",
      valor_total: 0,
      data_vencimento: today(),
      observacao: "",
    },
  })

  const mutation = useMutation({
    mutationFn: (data: FormData) => {
      const payload: CriarContaPagarPayload = {
        descricao: data.descricao,
        categoria: data.categoria,
        valor_total: data.valor_total.toFixed(2),
        data_vencimento: data.data_vencimento,
        observacao: data.observacao ?? "",
      }
      return financeiroService.criarContaPagar(payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["financeiro"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
      toast.success("Conta a pagar criada com sucesso.")
      form.reset()
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
            <Dialog.Title className="text-sm font-semibold text-zinc-900">Nova Conta a Pagar</Dialog.Title>
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
            {/* Descrição */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-600">Descrição</label>
              <Input
                placeholder="Ex: Conta de energia elétrica"
                error={Boolean(errors.descricao)}
                {...form.register("descricao")}
              />
              {errors.descricao && <p className="text-xs text-red-600">{errors.descricao.message}</p>}
            </div>

            {/* Categoria */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-600">Categoria</label>
              {categoriasQuery.isLoading ? (
                <div className="h-9 animate-pulse rounded-md bg-zinc-100" />
              ) : (
                <select
                  className={`h-9 w-full rounded-md border px-3 text-sm bg-white text-zinc-900 focus:outline-none focus:ring-2 focus:ring-orange-500/30 focus:border-orange-500 transition-colors ${
                    errors.categoria ? "border-red-500" : "border-zinc-300"
                  }`}
                  {...form.register("categoria")}
                >
                  <option value="">Selecione a categoria...</option>
                  {categorias.map((c) => (
                    <option key={c.id} value={c.id}>{c.nome}</option>
                  ))}
                </select>
              )}
              {errors.categoria && <p className="text-xs text-red-600">{errors.categoria.message}</p>}
            </div>

            {/* Valor e Vencimento */}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-600">Valor total</label>
                <Input
                  type="number"
                  step="0.01"
                  min="0.01"
                  placeholder="0,00"
                  error={Boolean(errors.valor_total)}
                  {...form.register("valor_total", { valueAsNumber: true })}
                />
                {errors.valor_total && <p className="text-xs text-red-600">{errors.valor_total.message}</p>}
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-600">Vencimento</label>
                <Input
                  type="date"
                  error={Boolean(errors.data_vencimento)}
                  {...form.register("data_vencimento")}
                />
                {errors.data_vencimento && <p className="text-xs text-red-600">{errors.data_vencimento.message}</p>}
              </div>
            </div>

            {/* Observação */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-600">Observação <span className="text-zinc-400">(opcional)</span></label>
              <Input placeholder="Informações adicionais..." {...form.register("observacao")} />
            </div>

            <div className="flex justify-end gap-2 border-t border-zinc-100 pt-3">
              <Dialog.Close asChild>
                <Button type="button" variant="outline" size="sm">Cancelar</Button>
              </Dialog.Close>
              <Button type="submit" size="sm" loading={mutation.isPending}>
                Criar Conta
              </Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
