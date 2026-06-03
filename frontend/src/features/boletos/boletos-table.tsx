"use client"

import {
  FileText,
  Download,
  Eye,
  RefreshCw,
  Link2
} from "lucide-react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { EmptyState } from "@/components/ui/empty-state"
import { Table, Tbody, Td, Th, Thead, Tr } from "@/components/ui/table"
import { useApiToast } from "@/hooks/use-api-toast"
import { boletosService } from "@/services/boletos.service"
import { formatCurrency, formatDate, cn } from "@/lib/utils"
import { formatNumber } from "@/lib/format"
import type { BoletoOCR } from "@/types"

interface BoletosTableProps {
  boletos: BoletoOCR[]
  onSelect: (id: string) => void
  onAddClick: () => void
}

export function BoletosTable({ boletos, onSelect, onAddClick }: BoletosTableProps) {
  const queryClient = useQueryClient()
  const toast = useApiToast()

  // Quick reprocess mutation
  const reprocessMutation = useMutation({
    mutationFn: (id: string) => boletosService.reprocessarBoleto(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["boletos"] })
      toast.success("Leitura OCR reiniciada")
    },
    onError: (error) => {
      toast.error(error, "Erro ao reprocessar OCR")
    }
  })

  // Quick download helper
  const downloadBoleto = async (id: string, name: string) => {
    try {
      const blob = await boletosService.baixarBoleto(id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = name || `boleto-${id}.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (error) {
      toast.error(error, "Erro ao baixar arquivo")
    }
  }

  // Row prefetch on mouse enter
  const handlePrefetch = (id: string) => {
    queryClient.prefetchQuery({
      queryKey: ["boletos", "detail", id],
      queryFn: () => boletosService.getBoleto(id),
      staleTime: 30_000,
    })
    queryClient.prefetchQuery({
      queryKey: ["boletos", "historico", id],
      queryFn: () => boletosService.getHistoricoBoleto(id, { page_size: 20 }),
      staleTime: 30_000,
    })
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "CONFIRMADO":
        return <Badge variant="success">CONFIRMADO</Badge>
      case "REJEITADO":
        return <Badge variant="error">REJEITADO</Badge>
      case "ERRO":
        return <Badge variant="error">ERRO</Badge>
      case "AGUARDANDO_REVISAO":
        return <Badge variant="warning">REVISAR</Badge>
      case "PROCESSANDO":
        return <Badge variant="info">PROCESSANDO</Badge>
      case "ENVIADO":
      default:
        return <Badge variant="outline">ENVIADO</Badge>
    }
  }

  if (boletos.length === 0) {
    return (
      <EmptyState
        icon={<FileText className="size-5" />}
        title="Nenhum boleto enviado ainda"
        description="Envie uma foto ou PDF de boleto para leitura automática e geração de conta a pagar no financeiro."
        actionLabel="Adicionar boleto"
        onAction={onAddClick}
        className="rounded-lg border border-dashed border-zinc-200 bg-white"
      />
    )
  }

  return (
    <div className="overflow-hidden rounded-lg border border-zinc-200/80 bg-white shadow-[0_1px_2px_rgba(24,24,27,0.04)]">
      <Table>
        <Thead>
          <tr>
            <Th>Arquivo</Th>
            <Th>Beneficiário</Th>
            <Th>Banco</Th>
            <Th className="text-right">Valor</Th>
            <Th>Vencimento</Th>
            <Th className="text-right">Confiança OCR</Th>
            <Th>Conta a Pagar</Th>
            <Th>Status</Th>
            <Th className="text-right">Ações</Th>
          </tr>
        </Thead>
        <Tbody>
          {boletos.map((boleto) => {
            const canReprocess = boleto.status === "ERRO" || boleto.status === "AGUARDANDO_REVISAO"
            const ocrConf = Number(boleto.confianca_ocr ?? 0)

            return (
              <Tr
                key={boleto.id}
                onMouseEnter={() => handlePrefetch(boleto.id)}
                className="hover:bg-zinc-50/50 transition-colors"
              >
                {/* Nome do arquivo */}
                <Td className="max-w-[180px] truncate font-medium text-zinc-900">
                  <div className="flex items-center gap-2">
                    <FileText className="size-3.5 flex-shrink-0 text-zinc-400" />
                    <span className="truncate" title={boleto.arquivo_nome_original}>
                      {boleto.arquivo_nome_original}
                    </span>
                  </div>
                </Td>

                {/* Beneficiário */}
                <Td className="max-w-[180px] truncate">
                  <span className="text-zinc-800" title={boleto.fornecedor_nome_final}>
                    {boleto.fornecedor_nome_final || "-"}
                  </span>
                </Td>

                {/* Banco */}
                <Td className="max-w-[120px] truncate">
                  {boleto.banco_nome ? (
                    <span className="text-zinc-600" title={boleto.banco_nome}>
                      {boleto.banco_nome}
                    </span>
                  ) : boleto.banco_codigo ? (
                    <span className="text-zinc-500 font-mono">Cod: {boleto.banco_codigo}</span>
                  ) : (
                    "-"
                  )}
                </Td>

                {/* Valor */}
                <Td className="text-right font-medium tabular-nums text-zinc-900">
                  {boleto.valor ? formatCurrency(boleto.valor) : "-"}
                </Td>

                {/* Vencimento */}
                <Td className="text-xs text-zinc-500 tabular-nums">
                  {boleto.vencimento ? formatDate(boleto.vencimento) : "-"}
                </Td>

                {/* Confiança OCR */}
                <Td className="text-right font-medium tabular-nums">
                  {boleto.confianca_ocr !== null ? (
                    <div className="inline-flex items-center gap-1.5 justify-end">
                      <span className={cn(
                        "text-xs font-semibold",
                        ocrConf > 85 ? "text-green-600" :
                        ocrConf > 60 ? "text-yellow-600" : "text-red-500"
                      )}>
                        {formatNumber(boleto.confianca_ocr, 1)}%
                      </span>
                    </div>
                  ) : (
                    "-"
                  )}
                </Td>

                {/* Vínculo de conta a pagar */}
                <Td>
                  {boleto.conta_pagar ? (
                    <div className="flex items-center gap-1 text-[11px] text-zinc-400">
                      <Link2 className="size-3 text-green-500" />
                      <span className="font-mono text-zinc-600">Sim</span>
                    </div>
                  ) : (
                    <span className="text-zinc-400">-</span>
                  )}
                </Td>

                {/* Status */}
                <Td>{getStatusBadge(boleto.status)}</Td>

                {/* Ações */}
                <Td className="text-right">
                  <div className="inline-flex items-center gap-1">
                    <Button
                      type="button"
                      variant="outline"
                      size="xs"
                      onClick={() => onSelect(boleto.id)}
                      className={cn(
                        "font-medium",
                        boleto.status === "AGUARDANDO_REVISAO" 
                          ? "border-orange-200 text-orange-600 bg-orange-50/50 hover:bg-orange-50 hover:text-orange-700"
                          : ""
                      )}
                      icon={<Eye className="size-3" />}
                    >
                      {boleto.status === "AGUARDANDO_REVISAO" ? "Revisar" : "Detalhar"}
                    </Button>
                    
                    {canReprocess && (
                      <Button
                        type="button"
                        variant="outline"
                        size="xs"
                        loading={reprocessMutation.isPending}
                        onClick={() => reprocessMutation.mutate(boleto.id)}
                        className="p-1.5 text-zinc-500 hover:text-zinc-700"
                        title="Reprocessar OCR"
                      >
                        <RefreshCw className="size-3" />
                      </Button>
                    )}

                    <Button
                      type="button"
                      variant="outline"
                      size="xs"
                      onClick={() => downloadBoleto(boleto.id, boleto.arquivo_nome_original)}
                      className="p-1.5 text-zinc-500 hover:text-zinc-700"
                      title="Baixar arquivo original"
                    >
                      <Download className="size-3" />
                    </Button>
                  </div>
                </Td>
              </Tr>
            )
          })}
        </Tbody>
      </Table>
    </div>
  )
}
