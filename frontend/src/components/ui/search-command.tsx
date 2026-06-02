"use client"

import { useEffect, useState } from "react"
import { Dialog, DialogContent, DialogOverlay, DialogPortal, DialogTitle } from "@radix-ui/react-dialog"
import { Command } from "cmdk"
import { useRouter } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import {
  Search,
  LayoutDashboard,
  Users,
  HandCoins,
  Package,
  Wallet,
  Landmark,
  FileText,
  Settings,
} from "lucide-react"
import { clientesService } from "@/services/clientes.service"
import { estoqueService } from "@/services/estoque.service"
import { formatCurrency } from "@/lib/utils"

interface SearchCommandProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const navItems = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Clientes", href: "/clientes", icon: Users },
  { label: "Fiado", href: "/fiado", icon: HandCoins },
  { label: "Estoque", href: "/estoque", icon: Package },
  { label: "Financeiro", href: "/financeiro", icon: Wallet },
  { label: "Boletos", href: "/boletos", icon: Landmark },
  { label: "Fiscal", href: "/fiscal", icon: FileText },
  { label: "Configurações", href: "/configuracoes", icon: Settings },
]

export function SearchCommand({ open, onOpenChange }: SearchCommandProps) {
  const router = useRouter()
  const [search, setSearch] = useState("")
  const enabled = open && search.trim().length >= 2

  const clientesQuery = useQuery({
    queryKey: ["clientes", "command", search],
    queryFn: () => clientesService.list({ search, page_size: 5 }),
    enabled,
  })

  const produtosQuery = useQuery({
    queryKey: ["estoque", "command", search],
    queryFn: () => estoqueService.list({ search, page_size: 5 }),
    enabled,
  })

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        onOpenChange(!open)
      }
    }
    document.addEventListener("keydown", down)
    return () => document.removeEventListener("keydown", down)
  }, [open, onOpenChange])

  const runCommand = (href: string) => {
    router.push(href)
    onOpenChange(false)
    setSearch("")
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogPortal>
        <DialogOverlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px] transition-all duration-100 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:animate-in data-[state=open]:fade-in-0" />
        <DialogContent
          className="fixed left-1/2 top-[20%] z-50 w-full max-w-lg -translate-x-1/2 overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-xl transition-all duration-100 focus:outline-none"
          aria-describedby={undefined}
        >
          <DialogTitle className="sr-only">Busca e comandos</DialogTitle>
          <Command className="flex max-h-[380px] flex-col overflow-y-auto">
            <div className="flex items-center gap-2 border-b border-zinc-100 px-3.5 py-3">
              <Search className="size-4 flex-shrink-0 text-zinc-400" />
              <Command.Input
                placeholder="Buscar no ObraFlow"
                value={search}
                onValueChange={setSearch}
                className="w-full bg-transparent text-sm text-zinc-800 placeholder-zinc-400 focus:outline-none"
              />
              <kbd className="rounded border border-zinc-200 bg-zinc-100 px-1.5 py-0.5 text-[10px] text-zinc-400 shadow-sm">
                ESC
              </kbd>
            </div>

            <Command.List className="overflow-y-auto p-1.5 select-none">
              <Command.Empty className="py-6 text-center text-xs text-zinc-400">
                Nenhum resultado encontrado.
              </Command.Empty>

              <Command.Group
                heading="Navegação"
                className="px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-zinc-400"
              >
                {navItems.map(({ label, href, icon: Icon }) => (
                  <Command.Item
                    key={href}
                    onSelect={() => runCommand(href)}
                    className="flex cursor-pointer items-center gap-2 rounded-md px-2.5 py-2 text-xs font-medium text-zinc-700 transition-colors hover:bg-zinc-50 hover:text-zinc-900 aria-selected:bg-zinc-100 aria-selected:text-zinc-950"
                  >
                    <Icon className="size-3.5 text-zinc-400" />
                    <span>Ir para {label}</span>
                  </Command.Item>
                ))}
              </Command.Group>

              {clientesQuery.data?.results.length ? (
                <Command.Group
                  heading="Clientes"
                  className="mt-1 px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-zinc-400"
                >
                  {clientesQuery.data.results.map((cliente) => (
                    <Command.Item
                      key={cliente.id}
                      onSelect={() => runCommand(`/clientes/${cliente.id}`)}
                      className="flex cursor-pointer items-center justify-between rounded-md px-2.5 py-2 text-xs font-medium text-zinc-700 transition-colors hover:bg-zinc-50 hover:text-zinc-900 aria-selected:bg-zinc-100 aria-selected:text-zinc-950"
                    >
                      <div className="flex min-w-0 items-center gap-2">
                        <Users className="size-3.5 flex-shrink-0 text-zinc-400" />
                        <span className="truncate">{cliente.nome}</span>
                      </div>
                      <span className="ml-3 flex-shrink-0 font-mono text-[10px] text-zinc-400">
                        {formatCurrency(cliente.saldo_devedor)}
                      </span>
                    </Command.Item>
                  ))}
                </Command.Group>
              ) : null}

              {produtosQuery.data?.results.length ? (
                <Command.Group
                  heading="Estoque"
                  className="mt-1 px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-zinc-400"
                >
                  {produtosQuery.data.results.map((produto) => (
                    <Command.Item
                      key={produto.id}
                      onSelect={() => runCommand(`/estoque/${produto.id}`)}
                      className="flex cursor-pointer items-center justify-between rounded-md px-2.5 py-2 text-xs font-medium text-zinc-700 transition-colors hover:bg-zinc-50 hover:text-zinc-900 aria-selected:bg-zinc-100 aria-selected:text-zinc-950"
                    >
                      <div className="flex min-w-0 items-center gap-2">
                        <Package className="size-3.5 flex-shrink-0 text-zinc-400" />
                        <span className="truncate">{produto.nome}</span>
                      </div>
                      <span className="ml-3 flex-shrink-0 font-mono text-[10px] text-zinc-400">
                        {produto.estoque_atual} {produto.unidade_sigla}
                      </span>
                    </Command.Item>
                  ))}
                </Command.Group>
              ) : null}
            </Command.List>
          </Command>
        </DialogContent>
      </DialogPortal>
    </Dialog>
  )
}
