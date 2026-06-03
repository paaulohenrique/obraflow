"use client"

import * as Dialog from "@radix-ui/react-dialog"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  AlertTriangle,
  CalendarClock,
  Edit3,
  ExternalLink,
  FileDown,
  HandCoins,
  List,
  MessageSquare,
  Phone,
  X,
} from "lucide-react"
import { useRouter } from "next/navigation"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useApiToast } from "@/hooks/use-api-toast"
import { cobrancasService } from "@/services/cobrancas.service"
import { fiadoService } from "@/services/fiado.service"
import { cn, formatCurrency, formatDate, formatDatetime, formatDocument, formatPhone, initials } from "@/lib/utils"
import { toNumber } from "@/lib/format"
import type { Cliente } from "@/types"

interface ClienteActionDrawerProps {
  cliente: Cliente | null
  onClose: () => void
  onEdit: (cliente: Cliente) => void
}

function statusCobrancaVariant(status: string) {
  if (status === "LIDA") return "success" as const
  if (status === "FALHOU") return "error" as const
  if (status === "ENTREGUE") return "info" as const
  if (status === "ENVIADA") return "default" as const
  return "warning" as const
}

export function ClienteActionDrawer({ cliente, onClose, onEdit }: ClienteActionDrawerProps) {
  const router = useRouter()
  const queryClient = useQueryClient()
  const toast = useApiToast()

  const abrirFiadoMutation = useMutation({
    mutationFn: () => fiadoService.abrirOuRecuperarContaFiado(cliente!.id),
    onSuccess: (conta) => {
      queryClient.invalidateQueries({ queryKey: ["fiado"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
      onClose()
      router.push(`/fiado/${conta.id}`)
    },
    onError: (error) => toast.error(error),
  })

  const baixarPdfMutation = useMutation({
    mutationFn: (contaId: string) => fiadoService.baixarPdfContaFiado(contaId),
    onError: (error) => toast.error(error),
  })

  const open = Boolean(cliente)
  const clienteId = cliente?.id

  const contaAbertaQuery = useQuery({
    queryKey: ["fiado", "cliente", clienteId, "aberta"],
    queryFn: () => fiadoService.getContaAbertaByCliente(clienteId!),
    enabled: open && Boolean(clienteId),
  })

  const historicoFiadoQuery = useQuery({
    queryKey: ["fiado", "cliente", clienteId, "fechadas"],
    queryFn: () => fiadoService.getHistoricoFiadoCliente(clienteId!, { page_size: 10 }),
    enabled: open && Boolean(clienteId),
  })

  const historicoCobrancasQuery = useQuery({
    queryKey: ["cobrancas", "cliente", clienteId, "historico"],
    queryFn: () => cobrancasService.historicoCliente(clienteId!, { page_size: 8 }),
    enabled: open && Boolean(clienteId),
  })

  if (!cliente) return null

  const contaAberta = contaAbertaQuery.data
  const contasFechadas = historicoFiadoQuery.data?.results ?? []
  const historicoCobrancas = historicoCobrancasQuery.data?.results ?? []
  const ultimaMovimentacao = contaAberta?.updated_at ?? contasFechadas[0]?.updated_at ?? cliente.updated_at
  const saldo = toNumber(cliente.saldo_devedor)
  const limite = toNumber(cliente.limite_credito)
  const creditoDisponivel = toNumber(cliente.credito_disponivel)
  const usagePct = limite > 0 ? Math.min((saldo / limite) * 100, 100) : 0
  const bloqueado = cliente.bloqueado
  const inativo = !cliente.is_active

  const fiadoBloqueado = bloqueado || inativo
  const fiadoTooltip = bloqueado
    ? "Cliente bloqueado para compras fiado."
    : inativo
      ? "Cliente inativo."
      : null

  // Clean numbers for phone/whatsapp links
  const getCleanNumber = (phoneStr: string) => {
    return phoneStr.replace(/\D/g, "")
  }

  const phoneClean = cliente.telefone ? getCleanNumber(cliente.telefone) : ""
  const whatsappClean = cliente.whatsapp ? getCleanNumber(cliente.whatsapp) : ""

  return (
    <Dialog.Root open={open} onOpenChange={(v) => { if (!v) onClose() }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-zinc-950/20 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0" />
        <Dialog.Content
          className={cn(
            "fixed right-0 top-0 z-50 flex h-full w-full max-w-md flex-col bg-white shadow-2xl border-l border-zinc-200",
            "data-[state=open]:animate-in data-[state=closed]:animate-out",
            "data-[state=open]:slide-in-from-right data-[state=closed]:slide-out-to-right",
            "duration-200"
          )}
          aria-describedby={undefined}
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-zinc-100 px-6 py-4 bg-zinc-50/50">
            <div>
              <Dialog.Title className="text-sm font-semibold text-zinc-900">
                Ficha do Cliente
              </Dialog.Title>
              <p className="text-[10px] text-zinc-400 font-mono mt-0.5">ID: {cliente.id.slice(0, 8)}</p>
            </div>
            <Dialog.Close asChild>
              <button
                className="rounded-md p-1.5 text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-700"
                aria-label="Fechar"
              >
                <X className="size-4.5" />
              </button>
            </Dialog.Close>
          </div>

          {/* Corpo com scroll */}
          <div className="flex-1 overflow-y-auto">
            {/* Identidade Section */}
            <div className="border-b border-zinc-100 px-6 py-6">
              <div className="flex items-start gap-4">
                <div className="flex size-14 flex-shrink-0 items-center justify-center rounded-full bg-zinc-900 text-white shadow-sm font-semibold text-lg">
                  {initials(cliente.nome)}
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="truncate text-base font-bold text-zinc-950 tracking-tight">{cliente.nome}</h3>
                  <p className="mt-0.5 text-xs font-medium text-zinc-500">
                    {cliente.tipo_pessoa === "PF" ? "Pessoa Física (CPF)" : "Pessoa Jurídica (CNPJ)"}
                  </p>
                  <div className="mt-2.5 flex flex-wrap gap-1.5">
                    <Badge variant={bloqueado ? "error" : cliente.is_active ? "success" : "outline"}>
                      {bloqueado ? "BLOQUEADO" : cliente.is_active ? "ATIVO" : "INATIVO"}
                    </Badge>
                    {saldo > 0 && (
                      <Badge variant="warning" className="font-semibold">DEVEDOR</Badge>
                    )}
                  </div>
                </div>
              </div>

              {/* Dossier Document Info */}
              <div className="mt-5 rounded-lg border border-zinc-200 bg-zinc-50/50 p-3 space-y-2.5 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-zinc-400">Documento</span>
                  <span className="font-mono font-semibold text-zinc-800">{formatDocument(cliente.cpf_cnpj)}</span>
                </div>
                
                {(cliente.telefone || cliente.whatsapp) && (
                  <div className="border-t border-zinc-100 pt-2.5 flex flex-col gap-2">
                    {cliente.telefone && (
                      <div className="flex items-center justify-between">
                        <span className="text-zinc-400 flex items-center gap-1.5">
                          <Phone className="size-3 text-zinc-400" /> Telefone
                        </span>
                        <a href={`tel:${phoneClean}`} className="font-semibold text-zinc-700 hover:text-orange-500 transition-colors">
                          {formatPhone(cliente.telefone)}
                        </a>
                      </div>
                    )}
                    {cliente.whatsapp && (
                      <div className="flex items-center justify-between">
                        <span className="text-zinc-400 flex items-center gap-1.5">
                          <MessageSquare className="size-3 text-zinc-400" /> WhatsApp
                        </span>
                        <a 
                          href={`https://wa.me/55${whatsappClean}`} 
                          target="_blank" 
                          rel="noopener noreferrer" 
                          className="font-semibold text-zinc-700 hover:text-green-600 flex items-center gap-1 transition-colors"
                        >
                          {formatPhone(cliente.whatsapp)}
                          <ExternalLink className="size-2.5" />
                        </a>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Financeiro / Crédito Section */}
            <div className="border-b border-zinc-100 px-6 py-5">
              <p className="mb-4 text-[10px] font-bold uppercase tracking-wider text-zinc-400">
                Resumo de Crédito
              </p>
              
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="rounded-lg border border-zinc-100 p-3 bg-white">
                    <p className="text-[10px] text-zinc-400 font-medium">Limite Total</p>
                    <p className="mt-0.5 text-base font-bold tabular-nums text-zinc-950">
                      {formatCurrency(cliente.limite_credito)}
                    </p>
                  </div>
                  <div className="rounded-lg border border-zinc-200 p-3 bg-zinc-50/30">
                    <p className="text-[10px] text-zinc-400 font-medium">Saldo Devedor</p>
                    <p className={cn("mt-0.5 text-base font-bold tabular-nums", saldo > 0 ? "text-red-600" : "text-zinc-400")}>
                      {formatCurrency(cliente.saldo_devedor)}
                    </p>
                  </div>
                </div>

                <div className="rounded-lg border border-zinc-100 p-3 bg-white space-y-2">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-[10px] text-zinc-400 font-medium">Crédito Disponível</p>
                      <p className="mt-0.5 text-lg font-bold tabular-nums text-green-600">
                        {formatCurrency(creditoDisponivel)}
                      </p>
                    </div>
                    {limite > 0 && (
                      <span className="text-xs font-semibold bg-zinc-100 text-zinc-700 px-2 py-0.5 rounded">
                        {Math.round(usagePct)}% utilizado
                      </span>
                    )}
                  </div>
                  
                  {limite > 0 && (
                    <div className="relative h-2 w-full overflow-hidden rounded-full bg-zinc-100">
                      <div
                        className={cn(
                          "h-full rounded-full transition-all duration-500",
                          usagePct > 80 ? "bg-red-500" : usagePct > 50 ? "bg-yellow-500" : "bg-orange-500"
                        )}
                        style={{ width: `${usagePct}%` }}
                      />
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Aviso bloqueado */}
            {fiadoBloqueado && (
              <div className="mx-6 mt-4 flex items-start gap-2.5 rounded-lg border border-red-200 bg-red-50/50 px-3.5 py-3">
                <AlertTriangle className="mt-0.5 size-4 flex-shrink-0 text-red-600" />
                <p className="text-xs font-medium text-red-900 leading-normal">{fiadoTooltip}</p>
              </div>
            )}

            {/* Conta atual */}
            <div className="border-b border-zinc-100 px-6 py-5">
              <p className="mb-4 text-[10px] font-bold uppercase tracking-wider text-zinc-400">
                Conta Fiado Aberta
              </p>
              
              {contaAbertaQuery.isLoading ? (
                <div className="space-y-3">
                  <Skeleton className="h-16 w-full" />
                  <Skeleton className="h-9 w-full" />
                </div>
              ) : contaAberta ? (
                <div className="space-y-3 rounded-lg border border-orange-200 bg-orange-50/40 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <Badge variant="warning" className="font-semibold">ABERTA</Badge>
                      <p className="mt-2 text-xs font-bold text-zinc-900">Fiado #{contaAberta.id.slice(0, 8)}</p>
                      <p className="mt-0.5 text-[10px] text-zinc-500">Iniciada em {formatDate(contaAberta.data_abertura)}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-[10px] text-zinc-400 font-medium">Saldo Restante</p>
                      <p className="text-base font-extrabold tabular-nums text-red-600">{formatCurrency(contaAberta.valor_restante)}</p>
                      <p className="mt-0.5 text-[10px] text-zinc-400 font-mono">Total {formatCurrency(contaAberta.valor_total)}</p>
                    </div>
                  </div>
                  <Button
                    className="w-full bg-orange-500 hover:bg-orange-600 text-white font-bold"
                    size="sm"
                    icon={<ExternalLink className="size-3.5" />}
                    onClick={() => {
                      onClose()
                      router.push(`/fiado/${contaAberta.id}`)
                    }}
                  >
                    Gerenciar Fiado
                  </Button>
                </div>
              ) : (
                <div className="rounded-lg border border-dashed border-zinc-200 p-4 bg-zinc-50/30">
                  <p className="text-xs font-semibold text-zinc-700">Nenhuma conta aberta atualmente.</p>
                  <p className="mt-1 text-[11px] leading-relaxed text-zinc-500">
                    O cliente não possui pendências correntes ativas. Qualquer compra no fiado necessita iniciar uma nova fatura.
                  </p>
                  <Button
                    className="mt-3.5 w-full bg-orange-500 hover:bg-orange-600 text-white font-bold"
                    size="sm"
                    icon={<HandCoins className="size-3.5" />}
                    loading={abrirFiadoMutation.isPending}
                    disabled={fiadoBloqueado || abrirFiadoMutation.isPending}
                    onClick={() => abrirFiadoMutation.mutate()}
                  >
                    Iniciar Nova Conta Fiado
                  </Button>
                </div>
              )}
            </div>

            {/* Histórico de Fiados */}
            <div className="border-b border-zinc-100 px-6 py-5">
              <div className="mb-4 flex items-center justify-between gap-3">
                <p className="text-[10px] font-bold uppercase tracking-wider text-zinc-400">
                  Histórico de cobranças
                </p>
                <MessageSquare className="size-3.5 text-zinc-400" />
              </div>

              {historicoCobrancasQuery.isLoading ? (
                <div className="space-y-2.5">
                  {Array.from({ length: 3 }).map((_, index) => (
                    <Skeleton key={index} className="h-14 w-full" />
                  ))}
                </div>
              ) : historicoCobrancas.length === 0 ? (
                <div className="rounded-lg border border-dashed border-zinc-200 p-4 text-center text-xs text-zinc-500">
                  Nenhuma cobrança WhatsApp registrada.
                </div>
              ) : (
                <div className="space-y-2.5">
                  {historicoCobrancas.map((notificacao) => (
                    <div key={notificacao.id} className="rounded-lg border border-zinc-200 bg-white p-3">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="text-xs font-bold text-zinc-900">{notificacao.tipo}</p>
                          <p className="mt-0.5 text-[10px] text-zinc-400">{formatDatetime(notificacao.created_at)}</p>
                        </div>
                        <Badge variant={statusCobrancaVariant(notificacao.status)} className="text-[9px]">
                          {notificacao.status}
                        </Badge>
                      </div>
                      <p className="mt-2 line-clamp-2 text-[11px] leading-relaxed text-zinc-500">
                        {notificacao.mensagem || "-"}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="px-6 py-5">
              <div className="mb-4 flex items-center justify-between gap-3">
                <p className="text-[10px] font-bold uppercase tracking-wider text-zinc-400">
                  Contas Anteriores Quitadas
                </p>
                <div className="flex items-center gap-1 text-[10px] text-zinc-400 font-medium">
                  <CalendarClock className="size-3" />
                  Atividade: {formatDate(ultimaMovimentacao)}
                </div>
              </div>

              {historicoFiadoQuery.isLoading ? (
                <div className="space-y-2.5">
                  {Array.from({ length: 3 }).map((_, index) => (
                    <Skeleton key={index} className="h-14 w-full" />
                  ))}
                </div>
              ) : contasFechadas.length === 0 ? (
                <div className="rounded-lg border border-dashed border-zinc-200 p-4 text-center text-xs text-zinc-500">
                  Nenhuma conta finalizada registrada no histórico.
                </div>
              ) : (
                <div className="space-y-3">
                  {contasFechadas.map((conta) => (
                    <div key={conta.id} className="rounded-lg border border-zinc-200 p-3 bg-white hover:border-zinc-300 transition-colors">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-xs font-bold text-zinc-900">
                            Fiado #{conta.id.slice(0, 8)}
                          </p>
                          <p className="mt-0.5 text-[10px] text-zinc-400">
                            Pago em: {formatDate(conta.data_fechamento ?? conta.data_abertura)}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-xs font-bold tabular-nums text-zinc-950">
                            {formatCurrency(conta.valor_total)}
                          </p>
                          <Badge variant="success" className="mt-1 text-[9px] font-semibold py-0 px-1.5">QUITADA</Badge>
                        </div>
                      </div>
                      <div className="mt-3 grid grid-cols-2 gap-2 border-t border-zinc-100 pt-2.5">
                        <Button
                          variant="outline"
                          size="xs"
                          icon={<ExternalLink className="size-3" />}
                          onClick={() => {
                            onClose()
                            router.push(`/fiado/${conta.id}`)
                          }}
                        >
                          Ver
                        </Button>
                        <Button
                          variant="outline"
                          size="xs"
                          icon={<FileDown className="size-3" />}
                          loading={baixarPdfMutation.isPending}
                          onClick={() => baixarPdfMutation.mutate(conta.id)}
                        >
                          PDF
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Ações fixas no rodapé */}
          <div className="border-t border-zinc-200 px-6 py-4 space-y-2 bg-zinc-50/50">
            <Button
              className="w-full bg-orange-500 hover:bg-orange-600 text-white font-bold"
              size="sm"
              icon={<HandCoins className="size-3.5" />}
              loading={abrirFiadoMutation.isPending}
              disabled={fiadoBloqueado || abrirFiadoMutation.isPending}
              onClick={() => abrirFiadoMutation.mutate()}
            >
              {contaAberta ? "Ir Para Fiado Aberto" : "Abrir Nova Conta"}
            </Button>

            <div className="grid grid-cols-3 gap-2">
              <Button
                variant="outline"
                size="sm"
                className="text-xs font-semibold"
                icon={<ExternalLink className="size-3.5" />}
                onClick={() => {
                  onClose()
                  router.push(`/clientes/${cliente.id}`)
                }}
              >
                Ficha
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="text-xs font-semibold"
                icon={<Edit3 className="size-3.5" />}
                onClick={() => {
                  onClose()
                  onEdit(cliente)
                }}
              >
                Editar
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="text-xs font-semibold"
                icon={<List className="size-3.5" />}
                onClick={() => {
                  onClose()
                  router.push(`/fiado?cliente=${cliente.id}`)
                }}
              >
                Fiados
              </Button>
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
