"use client"

import Link from "next/link"
import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft, Banknote, CreditCard, Landmark, QrCode, Save, type LucideIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Shell } from "@/components/layout/shell"
import { Topbar } from "@/components/layout/topbar"
import { useApiToast } from "@/hooks/use-api-toast"
import { financeiroService } from "@/services/financeiro.service"
import type { ConfiguracaoFinanceiraOperacionalPayload, FormaPagamentoOperacional } from "@/types"

type CampoConfig = keyof ConfiguracaoFinanceiraOperacionalPayload

const FORMAS: Array<{
  forma: FormaPagamentoOperacional
  label: string
  campo: CampoConfig
  icon: LucideIcon
}> = [
  { forma: "PIX", label: "PIX", campo: "conta_pix", icon: QrCode },
  { forma: "DINHEIRO", label: "Dinheiro", campo: "conta_dinheiro", icon: Banknote },
  { forma: "CARTAO", label: "Cartão", campo: "conta_cartao", icon: CreditCard },
  { forma: "TRANSFERENCIA", label: "Transferência", campo: "conta_transferencia", icon: Landmark },
]

const emptyConfig: ConfiguracaoFinanceiraOperacionalPayload = {
  conta_pix: null,
  conta_dinheiro: null,
  conta_cartao: null,
  conta_transferencia: null,
}

export default function ConfiguracoesFinanceiroPage() {
  const queryClient = useQueryClient()
  const toast = useApiToast()
  const [form, setForm] = useState<Partial<ConfiguracaoFinanceiraOperacionalPayload>>({})

  const configQuery = useQuery({
    queryKey: ["financeiro", "configuracao-operacional"],
    queryFn: financeiroService.configuracaoOperacional,
  })

  const contasQuery = useQuery({
    queryKey: ["financeiro", "contas-financeiras", "configuracao"],
    queryFn: () => financeiroService.contasFinanceiras({ page_size: 200, ordering: "nome" }),
    staleTime: 60_000,
  })

  const mutation = useMutation({
    mutationFn: (payload: ConfiguracaoFinanceiraOperacionalPayload) =>
      financeiroService.atualizarConfiguracaoOperacional(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["financeiro"] })
      toast.success("Configurações salvas")
    },
    onError: (error) => toast.error(error),
  })

  const contas = (contasQuery.data?.results ?? []).filter((conta) => conta.ativo && conta.is_active)
  const valueFor = (campo: CampoConfig) =>
    form[campo] !== undefined ? form[campo] : configQuery.data?.[campo] ?? emptyConfig[campo] ?? null
  const payload = FORMAS.reduce<ConfiguracaoFinanceiraOperacionalPayload>(
    (acc, item) => ({ ...acc, [item.campo]: valueFor(item.campo) }),
    { ...emptyConfig }
  )

  return (
    <Shell>
      <Topbar
        title="Configurações Financeiras"
        subtitle="Destino financeiro do PDV"
        actions={
          <Link href="/configuracoes">
            <Button size="sm" variant="outline" icon={<ArrowLeft className="size-3.5" />}>
              Voltar
            </Button>
          </Link>
        }
      />

      <main className="flex-1 p-4 md:p-6">
        <Card className="max-w-3xl">
          <CardHeader>
            <h3 className="text-sm font-semibold text-zinc-900">PDV</h3>
          </CardHeader>
          <CardContent className="space-y-3">
            {FORMAS.map(({ forma, label, campo, icon: Icon }) => {
              const destino = configQuery.data?.destinos_pdv.find((item) => item.forma_pagamento === forma)

              return (
                <div
                  key={forma}
                  className="grid grid-cols-1 gap-3 rounded-md border border-zinc-200 bg-white p-3 md:grid-cols-[180px_1fr]"
                >
                  <div className="flex items-center gap-2 text-sm font-semibold text-zinc-900">
                    <Icon className="size-4 text-orange-500" />
                    {label}
                  </div>
                  <div className="space-y-1.5">
                    <select
                      value={valueFor(campo) ?? ""}
                      onChange={(event) =>
                        setForm((current) => ({
                          ...current,
                          [campo]: event.target.value || null,
                        }))
                      }
                      disabled={configQuery.isLoading || contasQuery.isLoading || mutation.isPending}
                      className="h-9 w-full rounded-md border border-zinc-300 bg-white px-3 text-sm text-zinc-900 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/30 disabled:bg-zinc-50"
                    >
                      <option value="">Conta automática</option>
                      {contas.map((conta) => (
                        <option key={conta.id} value={conta.id}>
                          {conta.nome} ({conta.tipo})
                        </option>
                      ))}
                    </select>
                    <p className="text-[11px] text-zinc-500">
                      PDV: {destino?.conta_nome || "sem conta ativa"}
                    </p>
                  </div>
                </div>
              )
            })}

            <div className="flex justify-end border-t border-zinc-100 pt-3">
              <Button
                size="sm"
                icon={<Save className="size-3.5" />}
                loading={mutation.isPending}
                disabled={configQuery.isLoading || contasQuery.isLoading}
                onClick={() => mutation.mutate(payload)}
              >
                Salvar
              </Button>
            </div>
          </CardContent>
        </Card>
      </main>
    </Shell>
  )
}
