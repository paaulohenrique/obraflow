"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { useCurrentUser } from "@/hooks/use-current-user"
import {
  LayoutDashboard,
  Users,
  HandCoins,
  Package,
  Wallet,
  FileText,
  BarChart3,
  Settings,
  Landmark,
  ChevronRight,
  ChevronLeft,
  LogOut,
  ShoppingCart,
  ShoppingBag,
} from "lucide-react"
import { useLogout } from "@/hooks/use-logout"

interface SidebarProps {
  collapsed: boolean
  onCollapsedChange: (collapsed: boolean) => void
}

const menuGroups = [
  {
    title: "Operação",
    items: [
      { href: "/clientes", label: "Clientes", icon: Users },
      { href: "/pdv", label: "PDV", icon: ShoppingCart },
      { href: "/vendas", label: "Vendas", icon: ShoppingBag },
      { href: "/fiado", label: "Fiado", icon: HandCoins },
      { href: "/estoque", label: "Estoque", icon: Package }
    ]
  },
  {
    title: "Financeiro",
    items: [
      { href: "/financeiro", label: "Financeiro", icon: Wallet },
      { href: "/boletos", label: "Boletos", icon: Landmark }
    ]
  },
  {
    title: "Fiscal",
    items: [
      { href: "/fiscal", label: "NF-e Entrada", icon: FileText },
      { href: "/configuracoes/fiscal", label: "Fiscal", icon: Settings }
    ]
  },
  {
    title: "Gestão",
    items: [
      { href: "/dashboard", label: "Painel do Dono", icon: LayoutDashboard },
      { href: "/relatorios", label: "Relatórios", icon: BarChart3 }
    ]
  },
  {
    title: "",
    items: [
      { href: "/configuracoes", label: "Configurações", icon: Settings }
    ]
  }
]

const mobileItems = [
  { href: "/dashboard", label: "Painel", icon: LayoutDashboard },
  { href: "/pdv", label: "PDV", icon: ShoppingCart },
  { href: "/clientes", label: "Clientes", icon: Users },
  { href: "/estoque", label: "Estoque", icon: Package },
  { href: "/relatorios", label: "Relatórios", icon: BarChart3 },
]

export function Sidebar({ collapsed, onCollapsedChange }: SidebarProps) {
  const pathname = usePathname()
  const { user, empresa } = useCurrentUser()
  const logout = useLogout()
  const companyName = empresa?.nome_fantasia || empresa?.razao_social || "MP Construções"
  const userName = user?.name || "Usuário"
  const role = user?.role || "operador"

  return (
    <>
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 hidden flex-col border-r border-zinc-200 bg-white transition-[width] duration-200 lg:flex",
          collapsed ? "w-20" : "w-64"
        )}
      >
        <div className={cn("flex h-16 items-center border-b border-zinc-100 px-4", collapsed ? "justify-center" : "gap-3")}>
          <div className="flex size-9 flex-shrink-0 items-center justify-center rounded-lg bg-zinc-950 shadow-sm">
            <span className="text-xs font-bold text-orange-400">MP</span>
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold leading-tight text-zinc-950">ObraFlow</p>
              <p className="truncate text-[11px] leading-tight text-zinc-500">{companyName}</p>
            </div>
          )}
        </div>

        <nav className={cn("flex-1 overflow-y-auto py-4", collapsed ? "px-2" : "px-3")}>
          <div className="space-y-5">
            {menuGroups.map((group, idx) => (
              <div key={`${group.title}-${idx}`} className="space-y-1.5">
                {group.title && !collapsed && (
                  <p className="px-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-zinc-400">
                    {group.title}
                  </p>
                )}
                <div className="space-y-1">
                  {group.items.map(({ href, label, icon: Icon }) => {
                    const active = pathname === href || pathname.startsWith(href + "/")
                    return (
                      <Link
                        key={href}
                        href={href}
                        title={collapsed ? label : undefined}
                        className={cn(
                          "group relative flex h-9 items-center gap-2.5 rounded-md text-xs font-semibold transition-colors duration-150",
                          collapsed ? "justify-center px-0" : "px-3",
                          active
                            ? "bg-zinc-950 text-white"
                            : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-950"
                        )}
                      >
                        {active && !collapsed && (
                          <span className="absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-orange-500" />
                        )}
                        <Icon
                          className={cn(
                            "size-4 flex-shrink-0 transition-colors",
                            active ? "text-orange-400" : "text-zinc-400 group-hover:text-zinc-700"
                          )}
                        />
                        {!collapsed && (
                          <>
                            <span className="flex-1 truncate">{label}</span>
                            {active && (
                              <ChevronRight className="size-3 text-orange-400/80 flex-shrink-0" />
                            )}
                          </>
                        )}
                      </Link>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        </nav>

        <div className="border-t border-zinc-100 p-3">
          <button
            type="button"
            onClick={() => onCollapsedChange(!collapsed)}
            className={cn(
              "mb-3 flex h-8 w-full items-center rounded-md border border-zinc-200 bg-white text-xs font-medium text-zinc-500 transition-colors hover:border-zinc-300 hover:text-zinc-900",
              collapsed ? "justify-center" : "justify-between px-2.5"
            )}
            aria-label={collapsed ? "Expandir sidebar" : "Recolher sidebar"}
          >
            {!collapsed && <span>Recolher</span>}
            {collapsed ? <ChevronRight className="size-3.5" /> : <ChevronLeft className="size-3.5" />}
          </button>

          <div className={cn("flex items-center rounded-md", collapsed ? "justify-center" : "gap-2.5 px-2 py-2")}>
            <div className="flex size-8 flex-shrink-0 items-center justify-center rounded-lg bg-orange-500">
              <span className="text-xs font-semibold text-white">{userName.charAt(0).toUpperCase()}</span>
            </div>
            {!collapsed && (
              <>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-semibold text-zinc-900">{userName}</p>
                  <p className="truncate text-[10px] capitalize text-zinc-500">{role}</p>
                </div>
                <button
                  type="button"
                  onClick={logout}
                  className="flex size-7 items-center justify-center rounded-md text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-800"
                  aria-label="Sair"
                >
                  <LogOut className="size-3.5" />
                </button>
              </>
            )}
          </div>
        </div>
      </aside>

      <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-zinc-200 bg-white/95 px-2 pb-[max(env(safe-area-inset-bottom),0.5rem)] pt-2 backdrop-blur lg:hidden">
        <div className="grid grid-cols-5 gap-1">
          {mobileItems.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(href + "/")
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex flex-col items-center justify-center gap-1 rounded-md px-1 py-1.5 text-[10px] font-semibold transition-colors",
                  active ? "bg-zinc-950 text-white" : "text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900"
                )}
              >
                <Icon
                  className={cn(
                    "size-4",
                    active ? "text-orange-400" : "text-zinc-400"
                  )}
                />
                <span className="max-w-full truncate">{label}</span>
              </Link>
            )
          })}
        </div>
      </nav>
    </>
  )
}
