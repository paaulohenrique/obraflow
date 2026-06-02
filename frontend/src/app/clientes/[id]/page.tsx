"use client"

import Link from "next/link"
import { useParams, useRouter } from "next/navigation"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft, CreditCard, Edit3, ExternalLink, FileDown, HandCoins, User, XCircle } from "lucide-react"
import { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, Tbody, Td, Th, Thead, Tr } from "@/components/ui/table"
import { Shell } from "@/components/layout/shell"
import { Topbar } from "@/components/layout/topbar"
import { ClienteFormDialog } from "@/features/clientes/cliente-form-dialog"
import { formatCurrency, formatDate, formatDocument, formatPhone, initials } from "@/lib/utils"
import { toNumber } from "@/lib/format"
import { useApiToast } from "@/hooks/use-api-toast"
import { clientesService } from "@/services/clientes.service"
import { fiadoService } from "@/services/fiado.service"

export default function ClienteDetalhePage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const queryClient = useQueryClient()
  const toast = useApiToast()
  const [editOpen, setEditOpen] = useState(false)

  const clienteQuery = useQuery({
    queryKey: ["clientes", id],
    queryFn: () => clientesService.get(id),
  })

  const contaAbertaQuery = useQuery({
    queryKey: ["fiado", "cliente", id, "aberta"],
    queryFn: () => fiadoService.getContaAbertaByCliente(id),
    enabled: Boolean(clienteQuery.data),
  })

  const historicoFiadoQuery = useQuery({
    queryKey: ["fiado", "cliente", id, "fechadas"],
    queryFn: () => fiadoService.getHistoricoFiadoCliente(id, { page_size: 20 }),
    enabled: Boolean(clienteQuery.data),
  })

  const abrirFiadoMutation = useMutation({
    mutationFn: () => fiadoService.abrirOuRecuperarContaFiado(id),
    onSuccess: (conta) => {
      queryClient.invalidateQueries({ queryKey: ["fiado"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
      router.push(`/fiado/${conta.id}`)
    },
    onError: (error) => toast.error(error),
  })

  const baixarPdfMutation = useMutation({
    mutationFn: (contaId: string) => fiadoService.baixarPdfContaFiado(contaId),
    onError: (error) => toast.error(error),
  })

  const cliente = clienteQuery.data

  if (clienteQuery.isLoading) {
    return (
      <Shell>
        <Topbar title="Cliente" />
        <main className="flex-1 space-y-5 p-6">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-80 w-full" />
        </main>
      </Shell>
    )
  }

  if (!cliente) {
    return (
      <Shell>
        <Topbar title="Cliente não encontrado" />
        <main className="flex flex-1 flex-col items-center justify-center gap-3 p-6">
          <XCircle className="size-12 text-zinc-300" />
          <p className="text-sm text-zinc-500">Este cliente não existe ou foi removido.</p>
          <Link href="/clientes">
            <Button variant="outline" size="sm" icon={<ArrowLeft className="size-3.5" />}>
              Voltar
            </Button>
          </Link>
        </main>
      </Shell>
    )
  }

  const saldo = toNumber(cliente.saldo_devedor)
  const limite = toNumber(cliente.limite_credito)
  const limiteDisponivel = toNumber(cliente.credito_disponivel)
  const usagePercent = limite > 0 ? (saldo / limite) * 100 : 0
  const contaAberta = contaAbertaQuery.data
  const contasFechadas = historicoFiadoQuery.data?.results ?? []

  return (
    <Shell>
      <Topbar
        title={cliente.nome}
        subtitle={`Ficha cadastral · ${formatDocument(cliente.cpf_cnpj)}`}
        actions={
          <>
            <Link href="/clientes">
              <Button variant="ghost" size="sm" icon={<ArrowLeft className="size-3.5" />}>
                Voltar
              </Button>
            </Link>
            <Button
              size="sm"
              icon={<HandCoins className="size-3.5" />}
              loading={abrirFiadoMutation.isPending}
              disabled={cliente.bloqueado || !cliente.is_active || abrirFiadoMutation.isPending}
              onClick={() => abrirFiadoMutation.mutate()}
            >
              Abrir Fiado
            </Button>
            <Button size="sm" icon={<Edit3 className="size-3.5" />} onClick={() => setEditOpen(true)}>
              Editar
            </Button>
          </>
        }
      />

      <ClienteFormDialog open={editOpen} onOpenChange={setEditOpen} cliente={cliente} />

      <main className="flex-1 space-y-5 p-6">
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
          <Card>
            <CardContent className="space-y-4 py-5">
              <div className="flex items-center gap-3">
                <div className="flex size-11 flex-shrink-0 items-center justify-center rounded-full bg-orange-100">
                  <span className="text-sm font-bold text-orange-700">{initials(cliente.nome)}</span>
                </div>
                <div>
                  <p className="text-sm font-bold leading-tight text-zinc-900">{cliente.nome}</p>
                  <p className="mt-1 text-xs text-zinc-400">{cliente.tipo_pessoa === "PF" ? "Pessoa Física" : "Pessoa Jurídica"}</p>
                </div>
              </div>

              <div className="space-y-2 border-t border-zinc-100 pt-3 text-xs text-zinc-600">
                <div className="flex justify-between gap-3">
                  <span>Documento</span>
                  <span className="font-medium text-zinc-800">{formatDocument(cliente.cpf_cnpj)}</span>
                </div>
                <div className="flex justify-between gap-3">
                  <span>Telefone</span>
                  <span className="font-medium text-zinc-800">{cliente.telefone ? formatPhone(cliente.telefone) : "-"}</span>
                </div>
                <div className="flex justify-between gap-3">
                  <span>Email</span>
                  <span className="truncate font-medium text-zinc-800">{cliente.email || "-"}</span>
                </div>
                <div className="flex justify-between gap-3">
                  <span>Situação</span>
                  <Badge variant={cliente.bloqueado ? "error" : cliente.is_active ? "success" : "outline"}>
                    {cliente.bloqueado ? "Bloqueado" : cliente.is_active ? "Ativo" : "Inativo"}
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardContent className="space-y-4 py-5">
              <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <div>
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Limite de Crédito</span>
                  <p className="mt-1 text-2xl font-bold tabular-nums text-zinc-900">{formatCurrency(cliente.limite_credito)}</p>
                </div>
                <div>
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Saldo Devedor</span>
                  <p className="mt-1 text-2xl font-bold tabular-nums text-red-600">{formatCurrency(cliente.saldo_devedor)}</p>
                </div>
                <div>
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Crédito Disponível</span>
                  <p className="mt-1 text-2xl font-bold tabular-nums text-green-600">{formatCurrency(limiteDisponivel)}</p>
                </div>
              </div>

              <div className="border-t border-zinc-100 pt-4">
                <div className="mb-2 flex justify-between text-xs text-zinc-500">
                  <span>Uso do limite</span>
                  <span className="font-semibold text-zinc-800">{usagePercent.toFixed(0)}%</span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-zinc-100">
                  <div
                    className={`h-full rounded-full transition-all duration-300 ${
                      usagePercent > 80 ? "bg-red-500" : usagePercent > 50 ? "bg-yellow-500" : "bg-green-500"
                    }`}
                    style={{ width: `${Math.min(usagePercent, 100)}%` }}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          <Card>
            <CardHeader className="flex items-center justify-between pb-3">
              <div className="flex items-center gap-2">
                <CreditCard className="size-4 text-zinc-400" />
                <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-900">Fiados do cliente</h3>
              </div>
              <Badge variant="outline">{(contaAberta ? 1 : 0) + (historicoFiadoQuery.data?.count ?? 0)}</Badge>
            </CardHeader>
            <CardContent className="space-y-5">
              <div>
                <div className="mb-2 flex items-center justify-between gap-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Conta aberta</p>
                  {!contaAberta && (
                    <Button
                      size="xs"
                      icon={<HandCoins className="size-3.5" />}
                      loading={abrirFiadoMutation.isPending}
                      disabled={cliente.bloqueado || !cliente.is_active || abrirFiadoMutation.isPending}
                      onClick={() => abrirFiadoMutation.mutate()}
                    >
                      Abrir nova
                    </Button>
                  )}
                </div>
                {contaAbertaQuery.isLoading ? (
                  <Skeleton className="h-20 w-full" />
                ) : contaAberta ? (
                  <div className="rounded-md border border-orange-200 bg-orange-50 px-3 py-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <Badge variant="warning">ABERTA</Badge>
                        <p className="mt-2 text-sm font-semibold text-zinc-900">Fiado #{contaAberta.id.slice(0, 8)}</p>
                        <p className="mt-0.5 text-xs text-zinc-500">Aberta em {formatDate(contaAberta.data_abertura)}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-zinc-500">Restante</p>
                        <p className="text-sm font-bold tabular-nums text-red-600">{formatCurrency(contaAberta.valor_restante)}</p>
                        <p className="mt-1 text-xs text-zinc-500">Total {formatCurrency(contaAberta.valor_total)}</p>
                      </div>
                    </div>
                    <Link href={`/fiado/${contaAberta.id}`}>
                      <Button className="mt-3 w-full" size="sm" icon={<ExternalLink className="size-3.5" />}>
                        Ir para conta
                      </Button>
                    </Link>
                  </div>
                ) : (
                  <div className="rounded-md border border-dashed border-zinc-200 px-3 py-4 text-xs text-zinc-500">
                    Nenhuma conta aberta. Contas fechadas permanecem abaixo no histórico.
                  </div>
                )}
              </div>

              <div>
                <div className="mb-2 flex items-center justify-between gap-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Histórico de contas fechadas</p>
                  <Badge variant="outline">{historicoFiadoQuery.data?.count ?? 0}</Badge>
                </div>
                {historicoFiadoQuery.isLoading ? (
                  <div className="space-y-2">
                  {Array.from({ length: 4 }).map((_, index) => (
                    <Skeleton key={index} className="h-10 w-full" />
                  ))}
                </div>
                ) : contasFechadas.length === 0 ? (
                  <div className="rounded-md border border-dashed border-zinc-200 px-3 py-4 text-center text-xs text-zinc-400">
                    Nenhuma conta fechada para este cliente.
                  </div>
              ) : (
                <Table>
                  <Thead>
                    <tr>
                      <Th>Conta</Th>
                      <Th className="text-right">Total</Th>
                      <Th className="text-right">Pago</Th>
                      <Th>Status</Th>
                      <Th />
                    </tr>
                  </Thead>
                  <Tbody>
                    {contasFechadas.map((conta) => (
                      <Tr key={conta.id} clickable>
                        <Td>
                          <Link href={`/fiado/${conta.id}`} className="font-semibold text-zinc-800 hover:text-orange-600">
                            #{conta.id.slice(0, 8)}
                          </Link>
                          <p className="mt-0.5 text-[11px] text-zinc-400">
                            {formatDate(conta.data_fechamento ?? conta.data_abertura)}
                          </p>
                        </Td>
                        <Td className="text-right tabular-nums">{formatCurrency(conta.valor_total)}</Td>
                        <Td className="text-right font-semibold tabular-nums text-green-600">{formatCurrency(conta.valor_pago)}</Td>
                        <Td>
                          <Badge variant="success">FECHADA</Badge>
                        </Td>
                        <Td>
                          <div className="flex justify-end gap-1">
                            <Link href={`/fiado/${conta.id}`}>
                              <Button variant="ghost" size="xs" icon={<ExternalLink className="size-3.5" />} />
                            </Link>
                            <Button
                              variant="ghost"
                              size="xs"
                              icon={<FileDown className="size-3.5" />}
                              loading={baixarPdfMutation.isPending}
                              onClick={() => baixarPdfMutation.mutate(conta.id)}
                            />
                          </div>
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex items-center gap-2 pb-3">
              <User className="size-4 text-zinc-400" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-900">Cadastro</h3>
            </CardHeader>
            <CardContent className="space-y-2 text-xs text-zinc-600">
              <div className="flex justify-between gap-3">
                <span>Cidade</span>
                <span className="font-medium text-zinc-800">{cliente.cidade || "-"} {cliente.estado ? `/${cliente.estado}` : ""}</span>
              </div>
              <div className="flex justify-between gap-3">
                <span>Cadastrado em</span>
                <span className="font-medium text-zinc-800">{formatDate(cliente.created_at)}</span>
              </div>
              <div className="flex justify-between gap-3">
                <span>Último pagamento</span>
                <span className="font-medium text-zinc-800">
                  {cliente.data_ultimo_pagamento ? formatDate(cliente.data_ultimo_pagamento) : "-"}
                </span>
              </div>
              {cliente.observacao && (
                <p className="rounded-md border border-zinc-100 bg-zinc-50 px-3 py-2 text-zinc-500">{cliente.observacao}</p>
              )}
            </CardContent>
          </Card>
        </div>
      </main>
    </Shell>
  )
}
