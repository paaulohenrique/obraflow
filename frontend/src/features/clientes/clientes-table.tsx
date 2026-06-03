"use client"

import Link from "next/link"
import { ChevronRight, Users } from "lucide-react"
import { useQueryClient } from "@tanstack/react-query"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { EmptyState } from "@/components/ui/empty-state"
import { SkeletonTable } from "@/components/ui/skeleton"
import { Table, Tbody, Td, Th, Thead, Tr } from "@/components/ui/table"
import { formatCurrency, formatDocument, formatPhone, initials } from "@/lib/utils"
import { toNumber } from "@/lib/format"
import { clientesService } from "@/services/clientes.service"
import { fiadoService } from "@/services/fiado.service"
import type { Cliente } from "@/types"

interface ClientesTableProps {
  clientes: Cliente[]
  loading?: boolean
  onClienteClick?: (cliente: Cliente) => void
  onCreateClick?: () => void
}

export function ClientesTable({ clientes, loading, onClienteClick, onCreateClick }: ClientesTableProps) {
  const queryClient = useQueryClient()

  const handlePrefetch = (id: string) => {
    queryClient.prefetchQuery({
      queryKey: ["clientes", id],
      queryFn: () => clientesService.get(id),
      staleTime: 60_000,
    })
    queryClient.prefetchQuery({
      queryKey: ["fiado", "cliente", id, "aberta"],
      queryFn: () => fiadoService.getContaAbertaByCliente(id),
      staleTime: 10_000,
    })
    queryClient.prefetchQuery({
      queryKey: ["fiado", "cliente", id, "fechadas"],
      queryFn: () => fiadoService.getHistoricoFiadoCliente(id, { page_size: 20 }),
      staleTime: 10_000,
    })
  }

  if (loading) {
    return <SkeletonTable rows={8} cols={6} />
  }

  if (clientes.length === 0) {
    return (
      <EmptyState
        icon={<Users className="size-5" />}
        title="Nenhum cliente cadastrado"
        description="Cadastre seu primeiro cliente para começar a registrar vendas, limites de crédito e contas fiado."
        actionLabel={onCreateClick ? "Cadastrar cliente" : undefined}
        onAction={onCreateClick}
      />
    )
  }

  return (
    <Table>
      <Thead>
        <tr>
          <Th>Cliente</Th>
          <Th>Documento</Th>
          <Th>Telefone</Th>
          <Th className="text-right">Limite</Th>
          <Th className="text-right">Saldo Devedor</Th>
          <Th>Status</Th>
          <Th />
        </tr>
      </Thead>
      <Tbody>
        {clientes.map((cliente) => {
          const saldo = toNumber(cliente.saldo_devedor)
          const limite = toNumber(cliente.limite_credito)
          const usagePercent = limite > 0 ? (saldo / limite) * 100 : 0

          return (
            <Tr
              key={cliente.id}
              clickable
              onClick={() => onClienteClick?.(cliente)}
              onMouseEnter={() => handlePrefetch(cliente.id)}
            >
              <Td>
                <div className="flex items-center gap-2.5">
                  <div className="flex size-8 flex-shrink-0 items-center justify-center rounded-full bg-orange-100">
                    <span className="text-xs font-semibold text-orange-700">{initials(cliente.nome)}</span>
                  </div>
                  <span className="font-medium text-zinc-900">{cliente.nome}</span>
                </div>
              </Td>
              <Td className="font-mono text-xs text-zinc-500">{formatDocument(cliente.cpf_cnpj)}</Td>
              <Td className="text-zinc-600">{cliente.telefone ? formatPhone(cliente.telefone) : "-"}</Td>
              <Td className="text-right tabular-nums">{formatCurrency(cliente.limite_credito)}</Td>
              <Td className="text-right">
                <div className="flex flex-col items-end gap-1">
                  <span className={`font-medium tabular-nums ${saldo > 0 ? "text-red-600" : "text-zinc-600"}`}>
                    {formatCurrency(cliente.saldo_devedor)}
                  </span>
                  {saldo > 0 && (
                    <div className="h-1 w-20 overflow-hidden rounded-full bg-zinc-200">
                      <div
                        className={`h-full rounded-full ${usagePercent > 80 ? "bg-red-500" : usagePercent > 50 ? "bg-yellow-500" : "bg-green-500"}`}
                        style={{ width: `${Math.min(usagePercent, 100)}%` }}
                      />
                    </div>
                  )}
                </div>
              </Td>
              <Td>
                <Badge variant={cliente.bloqueado ? "error" : cliente.is_active ? "success" : "outline"}>
                  {cliente.bloqueado ? "Bloqueado" : cliente.is_active ? "Ativo" : "Inativo"}
                </Badge>
              </Td>
              <Td onClick={(e) => e.stopPropagation()}>
                <Link href={`/clientes/${cliente.id}`}>
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
