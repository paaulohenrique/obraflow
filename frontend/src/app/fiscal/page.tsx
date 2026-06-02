"use client"

import { useQuery } from "@tanstack/react-query"
import { CheckCircle2, Eye, FileCode, History, PackageOpen, Plus, XCircle } from "lucide-react"
import { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { StatCard } from "@/components/ui/stat-card"
import { Table, Tbody, Td, Th, Thead, Tr } from "@/components/ui/table"
import { Shell } from "@/components/layout/shell"
import { Topbar } from "@/components/layout/topbar"
import { formatCurrency, formatDate, formatDocument } from "@/lib/utils"
import { statusLabel } from "@/lib/format"
import { notasEntradaService } from "@/services/notas-entrada.service"
import { NfeUploadModal } from "@/features/fiscal/nfe-upload-modal"
import { NotaReviewDrawer } from "@/features/fiscal/nota-review-drawer"

export default function FiscalPage() {
  const [selectedNotaId, setSelectedNotaId] = useState<string | null>(null)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [drawerIntent, setDrawerIntent] = useState<"review" | "history">("review")

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
      <Topbar
        title="Nota Fiscal de Entrada"
        subtitle="Importe XML de compra, revise os itens e lance no estoque."
        actions={
          <Button size="sm" icon={<Plus className="size-3.5" />} onClick={() => setUploadOpen(true)}>
            Adicionar NF-e
          </Button>
        }
      />

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
                    <Th>Conta a pagar</Th>
                    <Th>Status</Th>
                    <Th className="text-right">Ações</Th>
                  </tr>
                </Thead>
                <Tbody>
                  {notas.map((nota) => (
                    <Tr
                      key={nota.id}
                      clickable
                      onClick={() => {
                        setDrawerIntent("review")
                        setSelectedNotaId(nota.id)
                      }}
                      className="hover:bg-zinc-50/40 transition-colors"
                    >
                      <Td className="font-mono text-xs font-semibold text-zinc-700">{nota.numero || "-"}</Td>
                      <Td className="font-medium text-zinc-900">{nota.fornecedor_nome_final || "-"}</Td>
                      <Td className="font-mono text-xs text-zinc-500">{nota.fornecedor_cnpj_xml ? formatDocument(nota.fornecedor_cnpj_xml) : "-"}</Td>
                      <Td className="text-right tabular-nums font-semibold text-zinc-955">{formatCurrency(nota.valor_total)}</Td>
                      <Td className="text-xs text-zinc-500">{nota.data_emissao ? formatDate(nota.data_emissao) : "-"}</Td>
                      <Td className="text-right tabular-nums text-xs text-zinc-650">
                        {nota.itens_total}
                        {nota.itens_sem_produto > 0 && <span className="ml-1 text-red-600 font-bold">({nota.itens_sem_produto})</span>}
                      </Td>
                      <Td>
                        <Badge variant={nota.conta_pagar ? "success" : "outline"}>
                          {nota.conta_pagar ? "Criada" : "Não criada"}
                        </Badge>
                      </Td>
                      <Td>
                        <Badge variant={nota.status === "CONFIRMADA" ? "success" : nota.status === "REJEITADA" ? "error" : "warning"}>
                          {statusLabel(nota.status)}
                        </Badge>
                      </Td>
                      <Td className="text-right">
                        <div className="flex justify-end gap-1.5">
                          <Button
                            variant="ghost"
                            size="xs"
                            icon={<Eye className="size-3.5" />}
                            onClick={(event) => {
                              event.stopPropagation()
                              setDrawerIntent("review")
                              setSelectedNotaId(nota.id)
                            }}
                          >
                            Revisar
                          </Button>
                          {nota.status === "AGUARDANDO_REVISAO" && (
                            <>
                              <Button
                                variant="outline"
                                size="xs"
                                icon={<CheckCircle2 className="size-3.5" />}
                                onClick={(event) => {
                                  event.stopPropagation()
                                  setDrawerIntent("review")
                                  setSelectedNotaId(nota.id)
                                }}
                              >
                                Confirmar
                              </Button>
                              <Button
                                variant="outline"
                                size="xs"
                                icon={<XCircle className="size-3.5" />}
                                onClick={(event) => {
                                  event.stopPropagation()
                                  setDrawerIntent("review")
                                  setSelectedNotaId(nota.id)
                                }}
                              >
                                Rejeitar
                              </Button>
                            </>
                          )}
                          <Button
                            variant="ghost"
                            size="xs"
                            icon={<History className="size-3.5" />}
                            onClick={(event) => {
                              event.stopPropagation()
                              setDrawerIntent("history")
                              setSelectedNotaId(nota.id)
                            }}
                          />
                        </div>
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Mapeamento lateral de nota fiscal */}
        <NotaReviewDrawer
          notaId={selectedNotaId}
          initialHistoryOpen={drawerIntent === "history"}
          onClose={() => {
            setSelectedNotaId(null)
            dashboardQuery.refetch()
            notasQuery.refetch()
          }}
        />
        <NfeUploadModal
          open={uploadOpen}
          onOpenChange={setUploadOpen}
          onSuccess={(notaId) => {
            setDrawerIntent("review")
            setSelectedNotaId(notaId)
            dashboardQuery.refetch()
            notasQuery.refetch()
          }}
        />
      </main>
    </Shell>
  )
}
