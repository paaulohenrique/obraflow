"use client"

import Link from "next/link"
import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft, MessageCircle, Save } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Shell } from "@/components/layout/shell"
import { Topbar } from "@/components/layout/topbar"
import { useApiToast } from "@/hooks/use-api-toast"
import { useCurrentUser } from "@/hooks/use-current-user"
import { cobrancasService } from "@/services/cobrancas.service"
import type { ConfiguracaoCobranca } from "@/types"

type Form = Pick<
  ConfiguracaoCobranca,
  | "ativo"
  | "enviar_1_dia_antes"
  | "enviar_no_vencimento"
  | "enviar_7_dias_apos"
  | "enviar_15_dias_apos"
  | "enviar_30_dias_apos"
>

const emptyForm: Form = {
  ativo: true,
  enviar_1_dia_antes: false,
  enviar_no_vencimento: true,
  enviar_7_dias_apos: true,
  enviar_15_dias_apos: true,
  enviar_30_dias_apos: false,
}

export default function ConfiguracaoCobrancasPage() {
  const queryClient = useQueryClient()
  const toast = useApiToast()
  const { user } = useCurrentUser()
  const [form, setForm] = useState<Form>(emptyForm)
  const [formKey, setFormKey] = useState("")
  const canEdit = user?.role === "admin" || user?.role === "manager"

  const configQuery = useQuery({
    queryKey: ["cobrancas", "configuracao"],
    queryFn: cobrancasService.configuracao,
    staleTime: 60_000,
  })

  const nextKey = configQuery.data?.updated_at ?? "loading"
  if (configQuery.data && formKey !== nextKey) {
    setFormKey(nextKey)
    setForm({
      ativo: configQuery.data.ativo,
      enviar_1_dia_antes: configQuery.data.enviar_1_dia_antes,
      enviar_no_vencimento: configQuery.data.enviar_no_vencimento,
      enviar_7_dias_apos: configQuery.data.enviar_7_dias_apos,
      enviar_15_dias_apos: configQuery.data.enviar_15_dias_apos,
      enviar_30_dias_apos: configQuery.data.enviar_30_dias_apos,
    })
  }

  const mutation = useMutation({
    mutationFn: () => cobrancasService.atualizarConfiguracao(form),
    onSuccess: (saved) => {
      queryClient.setQueryData(["cobrancas", "configuracao"], saved)
      queryClient.invalidateQueries({ queryKey: ["cobrancas"] })
      toast.success("Configuração de cobranças atualizada.")
    },
    onError: (error) => toast.error(error),
  })

  const update = <K extends keyof Form>(field: K, value: Form[K]) => {
    setForm((current) => ({ ...current, [field]: value }))
  }

  return (
    <Shell>
      <Topbar
        title="Configuração de Cobranças"
        subtitle="Automações operacionais por empresa"
        actions={
          <Link href="/configuracoes">
            <Button variant="ghost" size="sm" icon={<ArrowLeft className="size-3.5" />}>
              Voltar
            </Button>
          </Link>
        }
      />

      <main className="flex-1 p-4 md:p-6">
        <div className="max-w-3xl space-y-5">
          <Card>
            <CardHeader className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <MessageCircle className="size-4 text-orange-500" />
                <h3 className="text-sm font-semibold text-zinc-900">WhatsApp Cobranças</h3>
              </div>
              <Badge variant={form.ativo ? "success" : "outline"}>{form.ativo ? "Ativo" : "Inativo"}</Badge>
            </CardHeader>
            <CardContent>
              {configQuery.isLoading ? (
                <Skeleton className="h-72 w-full" />
              ) : (
                <div className="space-y-4">
                  <ToggleRow
                    label="Automação ativa"
                    checked={form.ativo}
                    disabled={!canEdit}
                    onChange={(checked) => update("ativo", checked)}
                  />
                  <div className="h-px bg-zinc-100" />
                  <ToggleRow
                    label="Enviar 1 dia antes"
                    checked={form.enviar_1_dia_antes}
                    disabled={!canEdit || !form.ativo}
                    onChange={(checked) => update("enviar_1_dia_antes", checked)}
                  />
                  <ToggleRow
                    label="Enviar no vencimento"
                    checked={form.enviar_no_vencimento}
                    disabled={!canEdit || !form.ativo}
                    onChange={(checked) => update("enviar_no_vencimento", checked)}
                  />
                  <ToggleRow
                    label="Enviar 7 dias após"
                    checked={form.enviar_7_dias_apos}
                    disabled={!canEdit || !form.ativo}
                    onChange={(checked) => update("enviar_7_dias_apos", checked)}
                  />
                  <ToggleRow
                    label="Enviar 15 dias após"
                    checked={form.enviar_15_dias_apos}
                    disabled={!canEdit || !form.ativo}
                    onChange={(checked) => update("enviar_15_dias_apos", checked)}
                  />
                  <ToggleRow
                    label="Enviar 30 dias após"
                    checked={form.enviar_30_dias_apos}
                    disabled={!canEdit || !form.ativo}
                    onChange={(checked) => update("enviar_30_dias_apos", checked)}
                  />

                  <div className="flex justify-end border-t border-zinc-100 pt-4">
                    <Button
                      size="sm"
                      icon={<Save className="size-3.5" />}
                      loading={mutation.isPending}
                      disabled={!canEdit || mutation.isPending}
                      onClick={() => mutation.mutate()}
                    >
                      Salvar
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </main>
    </Shell>
  )
}

function ToggleRow({
  label,
  checked,
  disabled,
  onChange,
}: {
  label: string
  checked: boolean
  disabled?: boolean
  onChange: (checked: boolean) => void
}) {
  return (
    <label className="flex min-h-11 items-center justify-between gap-4 rounded-md border border-zinc-200 bg-white px-3 py-2">
      <span className="text-sm font-medium text-zinc-800">{label}</span>
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
        className="size-4 rounded border-zinc-300 text-orange-500 focus:ring-orange-500 disabled:cursor-not-allowed disabled:opacity-50"
      />
    </label>
  )
}
