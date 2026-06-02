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
import { normalizeApiError } from "@/services/api"
import { clientesService } from "@/services/clientes.service"
import type { Cliente, ClientePayload } from "@/types"

const clienteSchema = z.object({
  nome: z.string().min(2, "Informe o nome do cliente."),
  tipo_pessoa: z.enum(["PF", "PJ"]),
  cpf_cnpj: z.string().min(11, "Informe CPF ou CNPJ."),
  telefone: z.string().optional(),
  whatsapp: z.string().optional(),
  email: z.string().email("Informe um email válido.").optional().or(z.literal("")),
  cidade: z.string().optional(),
  estado: z.string().max(2, "Use a sigla do estado.").optional().or(z.literal("")),
  limite_credito: z.number().min(0, "O limite deve ser positivo."),
  observacao: z.string().optional(),
})

type ClienteFormData = z.infer<typeof clienteSchema>

interface ClienteFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  cliente?: Cliente
}

function buildPayload(data: ClienteFormData): ClientePayload {
  return {
    ...data,
    email: data.email || "",
    telefone: data.telefone || "",
    whatsapp: data.whatsapp || "",
    cidade: data.cidade || "",
    estado: data.estado || "",
    observacao: data.observacao || "",
  }
}

export function ClienteFormDialog({ open, onOpenChange, cliente }: ClienteFormDialogProps) {
  const queryClient = useQueryClient()
  const toast = useApiToast()
  const isEditing = Boolean(cliente)

  const form = useForm<ClienteFormData>({
    resolver: zodResolver(clienteSchema),
    defaultValues: {
      nome: "",
      tipo_pessoa: "PF",
      cpf_cnpj: "",
      telefone: "",
      whatsapp: "",
      email: "",
      cidade: "",
      estado: "",
      limite_credito: 0,
      observacao: "",
    },
  })

  useEffect(() => {
    if (!open) return

    form.reset({
      nome: cliente?.nome ?? "",
      tipo_pessoa: cliente?.tipo_pessoa ?? "PF",
      cpf_cnpj: cliente?.cpf_cnpj ?? "",
      telefone: cliente?.telefone ?? "",
      whatsapp: cliente?.whatsapp ?? "",
      email: cliente?.email ?? "",
      cidade: cliente?.cidade ?? "",
      estado: cliente?.estado ?? "",
      limite_credito: Number(cliente?.limite_credito ?? 0),
      observacao: cliente?.observacao ?? "",
    })
  }, [cliente, form, open])

  const mutation = useMutation({
    mutationFn: (data: ClienteFormData) => {
      const payload = buildPayload(data)
      return isEditing && cliente ? clientesService.update(cliente.id, payload) : clientesService.create(payload)
    },
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: ["clientes"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
      queryClient.setQueryData(["clientes", saved.id], saved)
      toast.success(isEditing ? "Cliente atualizado" : "Cliente cadastrado")
      onOpenChange(false)
    },
    onError: (error) => {
      const apiError = normalizeApiError(error)
      if (apiError.errors) {
        const formFields = Object.keys(form.getValues()) as (keyof ClienteFormData)[]
        let hasFieldError = false
        for (const [field, messages] of Object.entries(apiError.errors)) {
          if (formFields.includes(field as keyof ClienteFormData)) {
            const message = Array.isArray(messages) ? messages[0] : String(messages)
            form.setError(field as keyof ClienteFormData, { message })
            hasFieldError = true
          }
        }
        if (!hasFieldError) toast.error(error)
      } else {
        toast.error(error)
      }
    },
  })

  const errors = form.formState.errors

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px] transition-all duration-150 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 z-50 w-full max-w-2xl -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-xl border border-zinc-200 bg-white p-5 shadow-xl focus:outline-none"
          aria-describedby={undefined}
        >
          <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
            <Dialog.Title className="text-sm font-semibold text-zinc-900">
              {isEditing ? "Editar Cliente" : "Novo Cliente"}
            </Dialog.Title>
            <Dialog.Close asChild>
              <button className="text-zinc-400 transition-colors hover:text-zinc-600">
                <X className="size-4" />
              </button>
            </Dialog.Close>
          </div>

          <form onSubmit={form.handleSubmit((data) => mutation.mutate(data))} className="space-y-4 pt-4">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              <div className="space-y-1 md:col-span-2">
                <label className="text-xs font-medium text-zinc-600">Nome / Razão Social</label>
                <Input error={Boolean(errors.nome)} {...form.register("nome")} />
                {errors.nome && <p className="text-xs text-red-600">{errors.nome.message}</p>}
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-zinc-600">Tipo</label>
                <select
                  className="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 text-sm text-zinc-900 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/30"
                  {...form.register("tipo_pessoa")}
                >
                  <option value="PF">Pessoa Física</option>
                  <option value="PJ">Pessoa Jurídica</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-zinc-600">CPF/CNPJ</label>
                <Input error={Boolean(errors.cpf_cnpj)} {...form.register("cpf_cnpj")} />
                {errors.cpf_cnpj && <p className="text-xs text-red-600">{errors.cpf_cnpj.message}</p>}
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-zinc-600">Telefone</label>
                <Input {...form.register("telefone")} />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-zinc-600">WhatsApp</label>
                <Input {...form.register("whatsapp")} />
              </div>
            </div>

            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-zinc-600">Email</label>
                <Input error={Boolean(errors.email)} {...form.register("email")} />
                {errors.email && <p className="text-xs text-red-600">{errors.email.message}</p>}
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-zinc-600">Cidade</label>
                <Input {...form.register("cidade")} />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-zinc-600">Estado</label>
                <Input maxLength={2} {...form.register("estado")} />
              </div>
            </div>

            <div className="grid grid-cols-1 gap-3 md:grid-cols-[180px_1fr]">
              <div className="space-y-1">
                <label className="text-xs font-medium text-zinc-600">Limite de Crédito</label>
                <Input
                  type="number"
                  step="0.01"
                  error={Boolean(errors.limite_credito)}
                  {...form.register("limite_credito", { valueAsNumber: true })}
                />
                {errors.limite_credito && <p className="text-xs text-red-600">{errors.limite_credito.message}</p>}
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-zinc-600">Observação</label>
                <Input {...form.register("observacao")} />
              </div>
            </div>

            <div className="flex justify-end gap-2 border-t border-zinc-100 pt-3">
              <Dialog.Close asChild>
                <Button type="button" variant="outline" size="sm">
                  Cancelar
                </Button>
              </Dialog.Close>
              <Button type="submit" size="sm" loading={mutation.isPending}>
                Salvar
              </Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
