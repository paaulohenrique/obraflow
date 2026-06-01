"use client"

import { useQuery } from "@tanstack/react-query"
import { AlertTriangle, Landmark, Wallet } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { StatCard } from "@/components/ui/stat-card"
import { Table, Tbody, Td, Th, Thead, Tr } from "@/components/ui/table"
import { Shell } from "@/components/layout/shell"
import { Topbar } from "@/components/layout/topbar"
import { formatCurrency, formatDate } from "@/lib/utils"
import { financeiroService } from "@/services/financeiro.service"

export default function FinanceiroPage() {
  const dashboardQuery = useQuery({
    queryKey: ["financeiro", "dashboard"],
    queryFn: financeiroService.dashboard,
  })

  const contasPagarQuery = useQuery({
    queryKey: ["financeiro", "contas-pagar", "abertas"],
    queryFn: () => financeiroService.contasPagar({ status: "ABERTA", ordering: "data_vencimento", page_size: 20 }),
  })

  const contas = contasPagarQuery.data?.results ?? []

  return (
    <Shell>
      <Topbar title="Financeiro" subtitle="Contas a pagar e fluxo financeiro" />

      <main className="flex-1 space-y-5 p-6">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatCard label="Recebido Hoje" value={formatCurrency(dashboardQuery.data?.recebido_hoje)} accent icon={<Wallet className="size-4" />} />
          <StatCard label="Recebido no Mês" value={formatCurrency(dashboardQuery.data?.recebido_mes)} />
          <StatCard label="A Pagar Aberto" value={formatCurrency(dashboardQuery.data?.total_contas_pagar_abertas)} />
          <StatCard
            label="Vencidas"
            value={formatCurrency(dashboardQuery.data?.total_contas_pagar_vencidas)}
            icon={<AlertTriangle className="size-4" />}
          />
        </div>

        <Card>
          <CardHeader className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Landmark className="size-4 text-zinc-400" />
              <h3 className="text-sm font-semibold text-zinc-900">Contas a Pagar</h3>
            </div>
            <Badge variant="outline">{contasPagarQuery.data?.count ?? 0}</Badge>
          </CardHeader>
          <CardContent className="p-0">
            {contasPagarQuery.isLoading ? (
              <div className="space-y-2 p-5">
                {Array.from({ length: 6 }).map((_, index) => (
                  <Skeleton key={index} className="h-12 w-full" />
                ))}
              </div>
            ) : contas.length === 0 ? (
              <div className="py-12 text-center text-sm text-zinc-400">Nenhuma conta a pagar aberta.</div>
            ) : (
              <Table>
                <Thead>
                  <tr>
                    <Th>Descrição</Th>
                    <Th>Fornecedor</Th>
                    <Th>Categoria</Th>
                    <Th className="text-right">Total</Th>
                    <Th className="text-right">Restante</Th>
                    <Th>Vencimento</Th>
                    <Th>Status</Th>
                  </tr>
                </Thead>
                <Tbody>
                  {contas.map((conta) => (
                    <Tr key={conta.id}>
                      <Td className="font-medium text-zinc-900">{conta.descricao}</Td>
                      <Td>{conta.fornecedor_nome || "-"}</Td>
                      <Td>{conta.categoria_nome}</Td>
                      <Td className="text-right tabular-nums">{formatCurrency(conta.valor_total)}</Td>
                      <Td className="text-right font-semibold tabular-nums text-red-600">{formatCurrency(conta.valor_restante)}</Td>
                      <Td className="text-xs text-zinc-500">{formatDate(conta.data_vencimento)}</Td>
                      <Td>
                        <Badge variant={conta.is_atrasada ? "error" : conta.is_parcial ? "default" : "warning"}>
                          {conta.is_atrasada ? "Atrasada" : conta.is_parcial ? "Parcial" : "Aberta"}
                        </Badge>
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            )}
          </CardContent>
        </Card>
      </main>
    </Shell>
  )
}
