"use client"

import * as Dialog from "@radix-ui/react-dialog"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  AlertTriangle,
  CalendarClock,
  CreditCard,
  Edit3,
  ExternalLink,
  FileDown,
  HandCoins,
  List,
  Phone,
  X,
} from "lucide-react"
import { useRouter } from "next/navigation"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useApiToast } from "@/hooks/use-api-toast"
import { fiadoService } from "@/services/fiado.service"
import { cn, formatCurrency, formatDate, formatDocument, formatPhone, initials } from "@/lib/utils"
import { toNumber } from "@/lib/format"
import type { Cliente } from "@/types"

interface ClienteActionDrawerProps {
  cliente: Cliente | null
  onClose: () => void
  onEdit: (cliente: Cliente) => void
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

  if (!cliente) return null

  const contaAberta = contaAbertaQuery.data
  const contasFechadas = historicoFiadoQuery.data?.results ?? []
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

  return (
    <Dialog.Root open={open} onOpenChange={(v) => { if (!v) onClose() }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/30 backdrop-blur-[1px] data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0" />
        <Dialog.Content
          className={cn(
            "fixed right-0 top-0 z-50 flex h-full w-full max-w-sm flex-col bg-white shadow-2xl",
            "data-[state=open]:animate-in data-[state=closed]:animate-out",
            "data-[state=open]:slide-in-from-right data-[state=closed]:slide-out-to-right",
            "duration-200"
          )}
          aria-describedby={undefined}
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-zinc-100 px-5 py-4">
            <Dialog.Title className="text-sm font-semibold text-zinc-900">
              Ficha do Cliente
            </Dialog.Title>
            <Dialog.Close asChild>
              <button
                className="rounded-md p-1 text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-700"
                aria-label="Fechar"
              >
                <X className="size-4" />
              </button>
            </Dialog.Close>
          </div>

          {/* Corpo com scroll */}
          <div className="flex-1 overflow-y-auto">
            {/* Identidade */}
            <div className="border-b border-zinc-100 px-5 py-5">
              <div className="flex items-start gap-3">
                <div className="flex size-12 flex-shrink-0 items-center justify-center rounded-full bg-orange-100">
                  <span className="text-base font-bold text-orange-700">{initials(cliente.nome)}</span>
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-bold text-zinc-900">{cliente.nome}</p>
                  <p className="mt-0.5 text-xs text-zinc-400">
                    {cliente.tipo_pessoa === "PF" ? "Pessoa Física" : "Pessoa Jurídica"}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    <Badge variant={bloqueado ? "error" : cliente.is_active ? "success" : "outline"}>
                      {bloqueado ? "Bloqueado" : cliente.is_active ? "Ativo" : "Inativo"}
                    </Badge>
                    {saldo > 0 && (
                      <Badge variant="warning">Devedor</Badge>
                    )}
                  </div>
                </div>
              </div>

              <div className="mt-4 space-y-2 text-xs text-zinc-600">
                <div className="flex items-center gap-2">
                  <CreditCard className="size-3.5 flex-shrink-0 text-zinc-400" />
                  <span className="font-mono">{formatDocument(cliente.cpf_cnpj)}</span>
                </div>
                {cliente.telefone && (
                  <div className="flex items-center gap-2">
                    <Phone className="size-3.5 flex-shrink-0 text-zinc-400" />
                    <span>{formatPhone(cliente.telefone)}</span>
                  </div>
                )}
                {cliente.whatsapp && cliente.whatsapp !== cliente.telefone && (
                  <div className="flex items-center gap-2">
                    <Phone className="size-3.5 flex-shrink-0 text-zinc-400" />
                    <span>{formatPhone(cliente.whatsapp)} (WhatsApp)</span>
                  </div>
                )}
              </div>
            </div>

            {/* Financeiro */}
            <div className="border-b border-zinc-100 px-5 py-4">
              <p className="mb-3 text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
                Crédito
              </p>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <p className="text-[10px] text-zinc-400">Limite</p>
                  <p className="mt-0.5 text-base font-bold tabular-nums text-zinc-900">
                    {formatCurrency(cliente.limite_credito)}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] text-zinc-400">Saldo Devedor</p>
                  <p className={cn("mt-0.5 text-base font-bold tabular-nums", saldo > 0 ? "text-red-600" : "text-zinc-400")}>
                    {formatCurrency(cliente.saldo_devedor)}
                  </p>
                </div>
                <div className="col-span-2">
                  <p className="text-[10px] text-zinc-400">Crédito Disponível</p>
                  <p className="mt-0.5 text-sm font-semibold tabular-nums text-green-600">
                    {formatCurrency(creditoDisponivel)}
                  </p>
                  {limite > 0 && (
                    <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-zinc-100">
                      <div
                        className={cn(
                          "h-full rounded-full transition-all",
                          usagePct > 80 ? "bg-red-500" : usagePct > 50 ? "bg-yellow-500" : "bg-green-500"
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
              <div className="mx-5 mt-4 flex items-start gap-2 rounded-md border border-yellow-200 bg-yellow-50 px-3 py-2.5">
                <AlertTriangle className="mt-0.5 size-4 flex-shrink-0 text-yellow-600" />
                <p className="text-xs text-yellow-800">{fiadoTooltip}</p>
              </div>
            )}

            {/* Conta atual */}
            <div className="border-b border-zinc-100 px-5 py-4">
              <p className="mb-3 text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
                Conta atual
              </p>
              {contaAbertaQuery.isLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-16 w-full" />
                  <Skeleton className="h-8 w-full" />
                </div>
              ) : contaAberta ? (
                <div className="space-y-3 rounded-md border border-orange-200 bg-orange-50 px-3 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <Badge variant="warning">ABERTA</Badge>
                      <p className="mt-2 text-xs font-semibold text-zinc-900">Fiado #{contaAberta.id.slice(0, 8)}</p>
                      <p className="mt-0.5 text-[11px] text-zinc-500">Aberta em {formatDate(contaAberta.data_abertura)}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-zinc-500">Restante</p>
                      <p className="text-sm font-bold tabular-nums text-red-600">{formatCurrency(contaAberta.valor_restante)}</p>
                      <p className="mt-1 text-[11px] text-zinc-500">Total {formatCurrency(contaAberta.valor_total)}</p>
                    </div>
                  </div>
                  <Button
                    className="w-full"
                    size="sm"
                    icon={<ExternalLink className="size-3.5" />}
                    onClick={() => {
                      onClose()
                      router.push(`/fiado/${contaAberta.id}`)
                    }}
                  >
                    Ir para conta
                  </Button>
                </div>
              ) : (
                <div className="rounded-md border border-dashed border-zinc-200 px-3 py-3">
                  <p className="text-xs font-medium text-zinc-700">Nenhuma conta aberta.</p>
                  <p className="mt-1 text-[11px] leading-relaxed text-zinc-500">
                    Contas fechadas ficam salvas no histórico. Você pode abrir uma nova conta fiado para este cliente.
                  </p>
                  <Button
                    className="mt-3 w-full"
                    size="sm"
                    icon={<HandCoins className="size-3.5" />}
                    loading={abrirFiadoMutation.isPending}
                    disabled={fiadoBloqueado || abrirFiadoMutation.isPending}
                    onClick={() => abrirFiadoMutation.mutate()}
                  >
                    Abrir nova conta fiado
                  </Button>
                </div>
              )}
            </div>

            {/* Histórico */}
            <div className="border-b border-zinc-100 px-5 py-4">
              <div className="mb-3 flex items-center justify-between gap-3">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">
                  Histórico de fiados
                </p>
                <div className="flex items-center gap-1 text-[10px] text-zinc-400">
                  <CalendarClock className="size-3.5" />
                  {formatDate(ultimaMovimentacao)}
                </div>
              </div>

              {historicoFiadoQuery.isLoading ? (
                <div className="space-y-2">
                  {Array.from({ length: 3 }).map((_, index) => (
                    <Skeleton key={index} className="h-12 w-full" />
                  ))}
                </div>
              ) : contasFechadas.length === 0 ? (
                <div className="rounded-md border border-dashed border-zinc-200 px-3 py-3 text-xs text-zinc-400">
                  Nenhuma conta fechada para este cliente.
                </div>
              ) : (
                <div className="divide-y divide-zinc-100 rounded-md border border-zinc-100">
                  {contasFechadas.map((conta) => (
                    <div key={conta.id} className="px-3 py-2.5">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate text-xs font-semibold text-zinc-800">
                            Fiado #{conta.id.slice(0, 8)}
                          </p>
                          <p className="mt-0.5 text-[11px] text-zinc-400">
                            {formatDate(conta.data_fechamento ?? conta.data_abertura)}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-xs font-bold tabular-nums text-zinc-900">
                            {formatCurrency(conta.valor_total)}
                          </p>
                          <Badge variant="success" className="mt-1">FECHADA</Badge>
                        </div>
                      </div>
                      <div className="mt-2 grid grid-cols-2 gap-2">
                        <Button
                          variant="outline"
                          size="xs"
                          icon={<ExternalLink className="size-3.5" />}
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
                          icon={<FileDown className="size-3.5" />}
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
          <div className="border-t border-zinc-100 px-5 py-4 space-y-2">
            {/* Abrir Fiado — ação principal */}
            <Button
              className="w-full"
              size="sm"
              icon={<HandCoins className="size-3.5" />}
              loading={abrirFiadoMutation.isPending}
              disabled={fiadoBloqueado || abrirFiadoMutation.isPending}
              onClick={() => abrirFiadoMutation.mutate()}
            >
              {contaAberta ? "Ir para fiado aberto" : "Abrir nova conta"}
            </Button>

            <div className="grid grid-cols-3 gap-2">
              <Button
                variant="outline"
                size="sm"
                icon={<ExternalLink className="size-3.5" />}
                onClick={() => {
                  onClose()
                  router.push(`/clientes/${cliente.id}`)
                }}
              >
                Detalhes
              </Button>
              <Button
                variant="outline"
                size="sm"
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
