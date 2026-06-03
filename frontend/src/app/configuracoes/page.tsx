"use client"

import Link from "next/link"
import { Building2, FileCog, Lock, Mail, MessageCircle, Shield, User, Wallet } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Shell } from "@/components/layout/shell"
import { Topbar } from "@/components/layout/topbar"
import { formatDocument, formatPhone } from "@/lib/utils"
import { useCurrentUser } from "@/hooks/use-current-user"

export default function ConfiguracoesPage() {
  const { user, empresa, isLoading } = useCurrentUser()

  return (
    <Shell>
      <Topbar title="Configurações" subtitle="Conta, empresa e segurança" />

      <main className="flex-1 p-4 md:p-6">
        <div className="max-w-3xl space-y-5">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Building2 className="size-4 text-orange-500" />
                <h3 className="text-sm font-semibold text-zinc-900">Empresa</h3>
              </div>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              {isLoading ? (
                <Skeleton className="h-24 w-full" />
              ) : (
                <>
                  <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                    <Info label="Razão Social" value={empresa?.razao_social} />
                    <Info label="Nome Fantasia" value={empresa?.nome_fantasia} />
                    <Info label="CNPJ" value={empresa?.cnpj ? formatDocument(empresa.cnpj) : undefined} />
                    <Info label="Telefone" value={empresa?.telefone ? formatPhone(empresa.telefone) : undefined} />
                    <Info label="Email" value={empresa?.email} />
                    <Info label="Plano" value={empresa?.plano} />
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileCog className="size-4 text-orange-500" />
                <h3 className="text-sm font-semibold text-zinc-900">Fiscal</h3>
              </div>
              <Link href="/configuracoes/fiscal">
                <Button size="sm" variant="outline">Abrir</Button>
              </Link>
            </CardHeader>
            <CardContent className="text-sm text-zinc-600">
              Base cadastral para futura emissão de NF-e modelo 55.
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <MessageCircle className="size-4 text-orange-500" />
                <h3 className="text-sm font-semibold text-zinc-900">Cobranças</h3>
              </div>
              <Link href="/configuracoes/cobrancas">
                <Button size="sm" variant="outline">Abrir</Button>
              </Link>
            </CardHeader>
            <CardContent className="text-sm text-zinc-600">
              Regras de automação WhatsApp para contas fiado.
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Wallet className="size-4 text-orange-500" />
                <h3 className="text-sm font-semibold text-zinc-900">Financeiro</h3>
              </div>
              <Link href="/configuracoes/financeiro">
                <Button size="sm" variant="outline">Abrir</Button>
              </Link>
            </CardHeader>
            <CardContent className="text-sm text-zinc-600">
              Contas usadas automaticamente no PDV.
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <User className="size-4 text-orange-500" />
                <h3 className="text-sm font-semibold text-zinc-900">Usuário Atual</h3>
              </div>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <Skeleton className="h-20 w-full" />
              ) : (
                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                  <Info label="Nome" value={user?.name} />
                  <Info label="Email" value={user?.email} icon={<Mail className="size-3.5" />} />
                  <Info label="Role" value={user?.role} icon={<Shield className="size-3.5" />} />
                  <Info label="Status" value={user?.is_active ? "Ativo" : "Inativo"} icon={<Lock className="size-3.5" />} />
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </main>
    </Shell>
  )
}

function Info({ label, value, icon }: { label: string; value?: string | null; icon?: React.ReactNode }) {
  return (
    <div className="rounded-md border border-zinc-100 bg-zinc-50 px-3 py-2">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">{label}</p>
      <div className="mt-1 flex items-center gap-1.5 text-sm font-medium text-zinc-800">
        {icon}
        <span>{value || "-"}</span>
      </div>
    </div>
  )
}
