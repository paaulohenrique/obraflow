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
  FileStack,
  ChevronRight,
  LogOut,
} from "lucide-react"
import { useLogout } from "@/hooks/use-logout"

const navItems = [
  { href: "/dashboard",  label: "Dashboard",    icon: LayoutDashboard },
  { href: "/clientes",   label: "Clientes",     icon: Users },
  { href: "/fiado",      label: "Fiado",        icon: HandCoins },
  { href: "/estoque",    label: "Estoque",      icon: Package },
  { href: "/financeiro", label: "Financeiro",   icon: Wallet },
  { href: "/boletos",    label: "Boletos",      icon: Landmark },
  { href: "/cobrancas",  label: "Cobranças",    icon: FileStack },
  { href: "/fiscal",     label: "Fiscal",       icon: FileText },
  { href: "/relatorios", label: "Relatórios",   icon: BarChart3 },
  { href: "/configuracoes", label: "Configurações", icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()
  const { user, empresa } = useCurrentUser()
  const logout = useLogout()
  const companyName = empresa?.nome_fantasia || empresa?.razao_social || "MP Construções"
  const userName = user?.name || "Usuário"
  const role = user?.role || "operador"

  return (
    <aside className="fixed inset-y-0 left-0 z-40 flex w-56 flex-col bg-zinc-950 border-r border-zinc-800">
      {/* Logo */}
      <div className="flex h-14 items-center gap-2.5 px-4 border-b border-zinc-800">
        <div className="flex size-7 items-center justify-center rounded-md bg-orange-500 shadow-sm flex-shrink-0">
          <span className="text-white font-bold text-xs">MP</span>
        </div>
        <div className="min-w-0">
          <p className="text-white text-sm font-semibold leading-tight truncate">ObraFlow</p>
          <p className="text-zinc-500 text-[10px] leading-tight truncate">{companyName}</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/")
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "group flex items-center gap-2.5 rounded-md px-3 h-9 text-sm font-medium transition-colors duration-100",
                active
                  ? "bg-orange-500/15 text-orange-400"
                  : "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/60"
              )}
            >
              <Icon
                className={cn(
                  "size-4 flex-shrink-0 transition-colors",
                  active ? "text-orange-400" : "text-zinc-500 group-hover:text-zinc-300"
                )}
              />
              <span className="flex-1 truncate">{label}</span>
              {active && (
                <ChevronRight className="size-3 text-orange-400/60 flex-shrink-0" />
              )}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-zinc-800 p-3">
        <div className="flex items-center gap-2.5 rounded-md px-2 py-2 transition-colors">
          <div className="size-7 rounded-full bg-orange-500 flex items-center justify-center flex-shrink-0">
            <span className="text-white text-xs font-semibold">{userName.charAt(0).toUpperCase()}</span>
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-zinc-200 text-xs font-medium truncate">{userName}</p>
            <p className="text-zinc-500 text-[10px] truncate">{role}</p>
          </div>
          <button
            type="button"
            onClick={logout}
            className="flex size-7 items-center justify-center rounded-md text-zinc-500 transition-colors hover:bg-zinc-800 hover:text-zinc-200"
            aria-label="Sair"
          >
            <LogOut className="size-3.5" />
          </button>
        </div>
      </div>
    </aside>
  )
}
