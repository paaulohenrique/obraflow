"use client"

import { useQuery } from "@tanstack/react-query"
import { FileText, Landmark } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { StatCard } from "@/components/ui/stat-card"
import { Table, Tbody, Td, Th, Thead, Tr } from "@/components/ui/table"
import { Shell } from "@/components/layout/shell"
import { Topbar } from "@/components/layout/topbar"
import { formatCurrency, formatDate } from "@/lib/utils"
import { formatNumber } from "@/lib/format"
import { boletosService } from "@/services/documentos.service"

export default function BoletosPage() {
  const dashboardQuery = useQuery({
    queryKey: ["boletos", "dashboard"],
    queryFn: boletosService.dashboard,
  })

  const boletosQuery = useQuery({
    queryKey: ["boletos", "list"],
    queryFn: () => boletosService.list({ page_size: 20, ordering: "-created_at" }),
  })

  const boletos = boletosQuery.data?.results ?? []

  return (
    <Shell>
      <Topbar title="Boletos" subtitle="OCR e conferência de contas a pagar" />

      <main className="flex-1 space-y-5 p-6">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatCard label="Pendentes" value={`${dashboardQuery.data?.pendentes_revisao ?? 0}`} accent icon={<FileText className="size-4" />} />
          <StatCard label="Processados Hoje" value={`${dashboardQuery.data?.boletos_processados_hoje ?? 0}`} />
          <StatCard label="OCR com Erro" value={`${dashboardQuery.data?.ocrs_com_erro ?? 0}`} />
          <StatCard label="Valor Identificado" value={formatCurrency(dashboardQuery.data?.valor_total_identificado)} />
        </div>

        <Card>
          <CardHeader className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Landmark className="size-4 text-zinc-400" />
              <h3 className="text-sm font-semibold text-zinc-900">Boletos Processados</h3>
            </div>
            <Badge variant="outline">{boletosQuery.data?.count ?? 0}</Badge>
          </CardHeader>
          <CardContent className="p-0">
            {boletosQuery.isLoading ? (
              <div className="space-y-2 p-5">
                {Array.from({ length: 6 }).map((_, index) => (
                  <Skeleton key={index} className="h-12 w-full" />
                ))}
              </div>
            ) : boletos.length === 0 ? (
              <div className="py-12 text-center text-sm text-zinc-400">Nenhum boleto processado.</div>
            ) : (
              <Table>
                <Thead>
                  <tr>
                    <Th>Arquivo</Th>
                    <Th>Fornecedor</Th>
                    <Th>Banco</Th>
                    <Th className="text-right">Valor</Th>
                    <Th>Vencimento</Th>
                    <Th className="text-right">Confiança</Th>
                    <Th>Status</Th>
                  </tr>
                </Thead>
                <Tbody>
                  {boletos.map((boleto) => (
                    <Tr key={boleto.id}>
                      <Td className="max-w-[220px] truncate font-medium text-zinc-900">{boleto.arquivo_nome_original}</Td>
                      <Td>{boleto.fornecedor_nome_final || "-"}</Td>
                      <Td>{boleto.banco_nome || "-"}</Td>
                      <Td className="text-right tabular-nums">{formatCurrency(boleto.valor)}</Td>
                      <Td className="text-xs text-zinc-500">{boleto.vencimento ? formatDate(boleto.vencimento) : "-"}</Td>
                      <Td className="text-right tabular-nums">{formatNumber(boleto.confianca_ocr, 2)}%</Td>
                      <Td>
                        <Badge variant={boleto.status === "CONFIRMADO" ? "success" : boleto.status === "ERRO" ? "error" : "warning"}>
                          {boleto.status}
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
