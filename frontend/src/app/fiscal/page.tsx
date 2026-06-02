"use client"

import { useQuery } from "@tanstack/react-query"
import { FileCode, PackageOpen } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { StatCard } from "@/components/ui/stat-card"
import { Table, Tbody, Td, Th, Thead, Tr } from "@/components/ui/table"
import { Shell } from "@/components/layout/shell"
import { Topbar } from "@/components/layout/topbar"
import { formatCurrency, formatDate, formatDocument } from "@/lib/utils"
import { notasEntradaService } from "@/services/documentos.service"

export default function FiscalPage() {
  const dashboardQuery = useQuery({
    queryKey: ["notas-entrada", "dashboard"],
    queryFn: notasEntradaService.dashboard,
  })

  const notasQuery = useQuery({
    queryKey: ["notas-entrada", "list"],
    queryFn: () => notasEntradaService.list({ page_size: 20, ordering: "-created_at" }),
  })

  const notas = notasQuery.data?.results ?? []

  return (
    <Shell>
      <Topbar title="Notas de Entrada" subtitle="XML de fornecedor e conciliação fiscal" />

      <main className="flex-1 space-y-5 p-6">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatCard label="Aguardando Revisão" value={`${dashboardQuery.data?.aguardando_revisao ?? 0}`} accent icon={<FileCode className="size-4" />} />
          <StatCard label="Confirmadas no Mês" value={`${dashboardQuery.data?.confirmadas_mes ?? 0}`} />
          <StatCard label="Itens sem Produto" value={`${dashboardQuery.data?.itens_sem_produto_pendentes ?? 0}`} />
          <StatCard label="Valor Importado" value={formatCurrency(dashboardQuery.data?.valor_total_importado_mes)} />
        </div>

        <Card>
          <CardHeader className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <PackageOpen className="size-4 text-zinc-400" />
              <h3 className="text-sm font-semibold text-zinc-900">Notas Fiscais de Entrada</h3>
            </div>
            <Badge variant="outline">{notasQuery.data?.count ?? 0}</Badge>
          </CardHeader>
          <CardContent className="p-0">
            {notasQuery.isLoading ? (
              <div className="space-y-2 p-5">
                {Array.from({ length: 6 }).map((_, index) => (
                  <Skeleton key={index} className="h-12 w-full" />
                ))}
              </div>
            ) : notas.length === 0 ? (
              <div className="py-12 text-center text-sm text-zinc-400">Nenhuma nota de entrada encontrada.</div>
            ) : (
              <Table>
                <Thead>
                  <tr>
                    <Th>Número</Th>
                    <Th>Fornecedor</Th>
                    <Th>CNPJ</Th>
                    <Th className="text-right">Valor</Th>
                    <Th>Emissão</Th>
                    <Th className="text-right">Itens</Th>
                    <Th>Status</Th>
                  </tr>
                </Thead>
                <Tbody>
                  {notas.map((nota) => (
                    <Tr key={nota.id}>
                      <Td className="font-mono text-xs font-semibold text-zinc-700">{nota.numero || "-"}</Td>
                      <Td className="font-medium text-zinc-900">{nota.fornecedor_nome_final || "-"}</Td>
                      <Td className="font-mono text-xs text-zinc-500">{nota.fornecedor_cnpj_xml ? formatDocument(nota.fornecedor_cnpj_xml) : "-"}</Td>
                      <Td className="text-right tabular-nums">{formatCurrency(nota.valor_total)}</Td>
                      <Td className="text-xs text-zinc-500">{nota.data_emissao ? formatDate(nota.data_emissao) : "-"}</Td>
                      <Td className="text-right tabular-nums">
                        {nota.itens_total}
                        {nota.itens_sem_produto > 0 && <span className="ml-1 text-red-600">({nota.itens_sem_produto})</span>}
                      </Td>
                      <Td>
                        <Badge variant={nota.status === "CONFIRMADA" ? "success" : nota.status === "REJEITADA" ? "error" : "warning"}>
                          {nota.status}
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
