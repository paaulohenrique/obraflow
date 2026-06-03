"use client"

import { Search, Building2, LogOut } from "lucide-react"
import { cn } from "@/lib/utils"
import { useCurrentUser } from "@/hooks/use-current-user"
import { useLogout } from "@/hooks/use-logout"
import { Badge } from "@/components/ui/badge"

interface TopbarProps {
  title?: string
  subtitle?: string
  actions?: React.ReactNode
}

export function Topbar({ title, subtitle, actions }: TopbarProps) {
  const { user, empresa } = useCurrentUser()
  const logout = useLogout()
  const companyName = empresa?.nome_fantasia || empresa?.razao_social || "MP Construções"
  const role = user?.role || "operador"

  return (
    <header className="sticky top-0 z-30 flex min-h-16 items-center gap-3 border-b border-zinc-200/80 bg-white/95 px-4 backdrop-blur md:px-6">
      <div className="min-w-0 flex-1">
        {title && (
          <div>
            <h1 className="truncate text-base font-semibold leading-tight text-zinc-950">{title}</h1>
            {subtitle && <p className="mt-0.5 truncate text-xs leading-tight text-zinc-500">{subtitle}</p>}
          </div>
        )}
      </div>

      <button
        onClick={() => window.dispatchEvent(new Event("obraflow:open-command"))}
        className={cn(
          "hidden h-8 w-56 cursor-pointer items-center gap-2 rounded-md border border-zinc-200 bg-zinc-50 px-3 text-sm text-zinc-400 transition-colors hover:border-zinc-300 hover:bg-white md:flex"
        )}
      >
        <Search className="size-3.5 flex-shrink-0" />
        <span className="flex-1 text-left text-xs">Buscar...</span>
        <kbd className="text-[10px] font-medium bg-zinc-200 text-zinc-500 px-1.5 py-0.5 rounded">Ctrl K</kbd>
      </button>

      {/* Empresa atual */}
      <div className="hidden lg:flex items-center gap-1.5 h-8 px-3 rounded-md border border-zinc-200 text-xs font-medium text-zinc-700">
        <Building2 className="size-3.5 text-zinc-400" />
        <span className="max-w-36 truncate">{companyName}</span>
      </div>

      {actions && <div className="flex items-center gap-2">{actions}</div>}

      {user && (
        <div className="hidden min-w-0 items-center gap-2 border-l border-zinc-200 pl-3 md:flex">
          <div className="min-w-0 text-right">
            <p className="truncate text-xs font-semibold leading-tight text-zinc-900">{user.name}</p>
            <p className="truncate text-[10px] leading-tight text-zinc-500">{user.email}</p>
          </div>
          <Badge variant="outline" className="hidden capitalize xl:inline-flex">
            {role}
          </Badge>
        </div>
      )}

      <button
        type="button"
        onClick={logout}
        className="hidden size-8 items-center justify-center rounded-md border border-zinc-200 text-zinc-500 transition-colors hover:bg-zinc-50 hover:text-zinc-900 md:flex"
        aria-label="Sair"
      >
        <LogOut className="size-4" />
      </button>
    </header>
  )
}
