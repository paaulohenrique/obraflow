"use client"

import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Ban, Landmark } from "lucide-react"
import * as Dialog from "@radix-ui/react-dialog"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { EmptyState } from "@/components/ui/empty-state"
import { SkeletonTable } from "@/components/ui/skeleton"
import { Table, Tbody, Td, Th, Thead, Tr } from "@/components/ui/table"
import { useApiToast } from "@/hooks/use-api-toast"
import { useCurrentUser } from "@/hooks/use-current-user"
import { formatCurrency, formatDatetime } from "@/lib/utils"
import { financeiroService } from "@/services/financeiro.service"
import type { LancamentoFinanceiro } from "@/types"

const ORIGEM_LABEL: Record<string, string> = {
  MANUAL: "Manual",
  FIADO: "Fiado",
  CONTA_PAGAR: "Conta a pagar",
  ESTORNO: "Estorno",
  AJUSTE: "Ajuste",
}

const FORMA_LABEL: Record<string, string> = {
  DINHEIRO: "Dinheiro",
  PIX: "PIX",
  CARTAO: "Cartão",
  BOLETO: "Boleto",
  TRANSFERENCIA: "Transf.",
  OUTRO: "Outro",
}

interface LancamentosTableProps {
  lancamentos: LancamentoFinanceiro[]
  loading: boolean
}

interface CancelarDialogState {
  lancamento: LancamentoFinanceiro
  motivo: string
}

export function LancamentosTable({ lancamentos, loading }: LancamentosTableProps) {
  const queryClient = useQueryClient()
  const toast = useApiToast()
  const { user } = useCurrentUser()
  const canCancel = user?.role === "admin" || user?.role === "manager"

  const [cancelar, setCancelar] = useState<CancelarDialogState | null>(null)

  const cancelarMutation = useMutation({
    mutationFn: ({ id, motivo }: { id: string; motivo: string }) =>
      financeiroService.cancelarLancamento(id, { motivo }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["financeiro"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
      toast.success("Lançamento cancelado.")
      setCancelar(null)
    },
    onError: (error) => toast.error(error),
  })

  if (loading) {
    return <SkeletonTable rows={8} cols={6} />
  }

  if (lancamentos.length === 0) {
    return (
      <EmptyState
        icon={<Landmark className="size-5" />}
        title="Nenhum lançamento encontrado"
        description="Receitas, despesas, baixas de fiado e contas pagas aparecerão neste histórico financeiro."
      />
    )
  }

  return (
    <>
      <Table>
        <Thead>
          <tr>
            <Th>Data</Th>
            <Th>Descrição</Th>
            <Th>Conta</Th>
            <Th>Categoria</Th>
            <Th>Origem</Th>
            <Th>Forma</Th>
            <Th className="text-right">Valor</Th>
            <Th>Status</Th>
            {canCancel && <Th />}
          </tr>
        </Thead>
        <Tbody>
          {lancamentos.map((l) => (
            <Tr key={l.id}>
              <Td className="text-xs text-zinc-500 whitespace-nowrap">
                {formatDatetime(l.data_lancamento)}
              </Td>
              <Td className="max-w-[180px]">
                <span className="block truncate text-sm text-zinc-800">{l.descricao || "—"}</span>
              </Td>
              <Td className="text-xs text-zinc-500">{l.conta_financeira_nome}</Td>
              <Td className="text-xs text-zinc-500">{l.categoria_nome}</Td>
              <Td>
                <span className="text-xs text-zinc-500">{ORIGEM_LABEL[l.origem_tipo] ?? l.origem_tipo}</span>
              </Td>
              <Td>
                <span className="text-xs text-zinc-500">{FORMA_LABEL[l.forma_pagamento] ?? l.forma_pagamento}</span>
              </Td>
              <Td className="text-right">
                <span
                  className={`text-sm font-semibold tabular-nums ${
                    l.tipo === "ENTRADA" ? "text-green-600" : "text-red-600"
                  }`}
                >
                  {l.tipo === "ENTRADA" ? "+" : "−"} {formatCurrency(l.valor)}
                </span>
              </Td>
              <Td>
                {l.status === "CONFIRMADO" ? (
                  <Badge variant="success">Confirmado</Badge>
                ) : (
                  <Badge variant="error">Cancelado</Badge>
                )}
              </Td>
              {canCancel && (
                <Td>
                  {l.status === "CONFIRMADO" && l.origem_tipo === "MANUAL" && (
                    <button
                      type="button"
                      title="Cancelar lançamento"
                      onClick={() => setCancelar({ lancamento: l, motivo: "" })}
                      className="flex size-7 items-center justify-center rounded-md text-zinc-400 transition-colors hover:bg-red-50 hover:text-red-600"
                    >
                      <Ban className="size-3.5" />
                    </button>
                  )}
                </Td>
              )}
            </Tr>
          ))}
        </Tbody>
      </Table>

      {/* Confirmar cancelamento */}
      <Dialog.Root open={Boolean(cancelar)} onOpenChange={(open) => !open && setCancelar(null)}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px] data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0" />
          <Dialog.Content
            className="fixed left-1/2 top-1/2 z-50 w-full max-w-sm -translate-x-1/2 -translate-y-1/2 rounded-xl border border-zinc-200 bg-white p-5 shadow-xl focus:outline-none"
            aria-describedby={undefined}
          >
            <Dialog.Title className="text-sm font-semibold text-zinc-900">
              Cancelar lançamento
            </Dialog.Title>
            <p className="mt-1 text-xs text-zinc-500">
              Um lançamento de estorno será criado automaticamente. Informe o motivo.
            </p>

            {cancelar && (
              <div className="mt-3 rounded-lg border border-zinc-100 bg-zinc-50 px-3 py-2 text-xs text-zinc-700">
                <span className={`font-semibold ${cancelar.lancamento.tipo === "ENTRADA" ? "text-green-600" : "text-red-600"}`}>
                  {cancelar.lancamento.tipo === "ENTRADA" ? "+" : "−"} {formatCurrency(cancelar.lancamento.valor)}
                </span>
                {" · "}{cancelar.lancamento.descricao || "Sem descrição"}
              </div>
            )}

            <textarea
              className="mt-3 h-20 w-full rounded-md border border-zinc-300 px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/30 resize-none"
              placeholder="Motivo do cancelamento..."
              value={cancelar?.motivo ?? ""}
              onChange={(e) => setCancelar((prev) => prev ? { ...prev, motivo: e.target.value } : null)}
            />

            <div className="mt-4 flex justify-end gap-2">
              <Dialog.Close asChild>
                <Button variant="outline" size="sm">Voltar</Button>
              </Dialog.Close>
              <Button
                variant="danger"
                size="sm"
                loading={cancelarMutation.isPending}
                disabled={!cancelar?.motivo.trim()}
                onClick={() => {
                  if (!cancelar?.motivo.trim()) return
                  cancelarMutation.mutate({
                    id: cancelar.lancamento.id,
                    motivo: cancelar.motivo.trim(),
                  })
                }}
              >
                Confirmar Cancelamento
              </Button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </>
  )
}
