"use client"

import Link from "next/link"
import { ChevronRight, HandCoins } from "lucide-react"
import { useQueryClient } from "@tanstack/react-query"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, Tbody, Td, Th, Thead, Tr } from "@/components/ui/table"
import { formatCurrency, formatDate, formatDocument, initials } from "@/lib/utils"
import { fiadoService } from "@/services/fiado.service"
import type { ContaFiado } from "@/types"

interface FiadoTableProps {
  contas: ContaFiado[]
  loading?: boolean
}

function contaStatus(conta: ContaFiado) {
  if (conta.status === "FECHADA") return { label: "Fechada", variant: "success" as const }
  if (conta.status === "CANCELADA") return { label: "Cancelada", variant: "outline" as const }
  if (conta.is_atrasada) return { label: "Atrasada", variant: "error" as const }
  if (conta.is_parcial) return { label: "Parcial", variant: "default" as const }
  return { label: "Aberta", variant: "warning" as const }
}

export function FiadoTable({ contas, loading }: FiadoTableProps) {
  const queryClient = useQueryClient()

  const handlePrefetch = (id: string) => {
    queryClient.prefetchQuery({
      queryKey: ["fiado", "contas", id],
      queryFn: () => fiadoService.get(id),
      staleTime: 10_000,
    })
    queryClient.prefetchQuery({
      queryKey: ["fiado", "contas", id, "itens"],
      queryFn: () => fiadoService.itens(id, { page_size: 100 }),
      staleTime: 10_000,
    })
    queryClient.prefetchQuery({
      queryKey: ["fiado", "contas", id, "pagamentos"],
      queryFn: () => fiadoService.pagamentos(id, { page_size: 100 }),
      staleTime: 10_000,
    })
    queryClient.prefetchQuery({
      queryKey: ["fiado", "contas", id, "historico"],
      queryFn: () => fiadoService.historico(id, { page_size: 100 }),
      staleTime: 10_000,
    })
  }

  if (loading) {
    return (
      <div className="space-y-2 p-5">
        {Array.from({ length: 8 }).map((_, index) => (
          <Skeleton key={index} className="h-12 w-full" />
        ))}
      </div>
    )
  }

  if (contas.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="mb-3 flex size-12 items-center justify-center rounded-full bg-zinc-100">
          <HandCoins className="size-5 text-zinc-400" />
        </div>
        <p className="text-sm font-medium text-zinc-700">Nenhuma conta fiado encontrada</p>
        <p className="mt-1 text-xs text-zinc-400">Ajuste os filtros e tente novamente.</p>
      </div>
    )
  }

  return (
    <Table>
      <Thead>
        <tr>
          <Th>Cliente</Th>
          <Th>Status</Th>
          <Th className="text-right">Total</Th>
          <Th className="text-right">Pago</Th>
          <Th className="text-right">Restante</Th>
          <Th>Vencimento</Th>
          <Th />
        </tr>
      </Thead>
      <Tbody>
        {contas.map((conta) => {
          const status = contaStatus(conta)

          return (
            <Tr
              key={conta.id}
              clickable
              onMouseEnter={() => handlePrefetch(conta.id)}
            >
              <Td>
                <div className="flex items-center gap-2.5">
                  <div className="flex size-7 flex-shrink-0 items-center justify-center rounded-full bg-zinc-100">
                    <span className="text-[10px] font-semibold text-zinc-600">{initials(conta.cliente_nome)}</span>
                  </div>
                  <div>
                    <p className="font-medium leading-tight text-zinc-900">{conta.cliente_nome}</p>
                    <p className="text-[11px] text-zinc-400">{formatDocument(conta.cliente_cpf_cnpj)}</p>
                  </div>
                </div>
              </Td>
              <Td>
                <Badge variant={status.variant}>{status.label}</Badge>
              </Td>
              <Td className="text-right tabular-nums text-zinc-700">{formatCurrency(conta.valor_total)}</Td>
              <Td className="text-right tabular-nums text-green-600">{formatCurrency(conta.valor_pago)}</Td>
              <Td className="text-right font-medium tabular-nums text-red-600">{formatCurrency(conta.valor_restante)}</Td>
              <Td className="text-xs text-zinc-500">{conta.data_vencimento ? formatDate(conta.data_vencimento) : "-"}</Td>
              <Td>
                <Link href={`/fiado/${conta.id}`}>
                  <Button variant="ghost" size="xs" icon={<ChevronRight className="size-3.5" />} />
                </Link>
              </Td>
            </Tr>
          )
        })}
      </Tbody>
    </Table>
  )
}
