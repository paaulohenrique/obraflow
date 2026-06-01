"use client"

import { useState } from "react"
import { Bell, Search, Building2, ChevronDown, LogOut } from "lucide-react"
import { cn } from "@/lib/utils"
import { SearchCommand } from "@/components/ui/search-command"
import { useCurrentUser } from "@/hooks/use-current-user"
import { useLogout } from "@/hooks/use-logout"
import { Badge } from "@/components/ui/badge"

interface TopbarProps {
  title?: string
  subtitle?: string
  actions?: React.ReactNode
}

export function Topbar({ title, subtitle, actions }: TopbarProps) {
  const [commandOpen, setCommandOpen] = useState(false)
  const { user, empresa } = useCurrentUser()
  const logout = useLogout()
  const companyName = empresa?.nome_fantasia || empresa?.razao_social || "MP Construções"
  const role = user?.role || "operador"

  return (
    <header className="h-14 border-b border-zinc-200 bg-white flex items-center px-6 gap-4 sticky top-0 z-30">
      {/* Título da página */}
      <div className="flex-1 min-w-0">
        {title && (
          <div>
            <h1 className="text-base font-semibold text-zinc-900 leading-tight">{title}</h1>
            {subtitle && <p className="text-xs text-zinc-500 leading-tight">{subtitle}</p>}
          </div>
        )}
      </div>

      {/* Search global */}
      <button
        onClick={() => setCommandOpen(true)}
        className={cn(
          "hidden md:flex items-center gap-2 h-8 px-3 rounded-md border border-zinc-200",
          "bg-zinc-50 text-zinc-400 text-sm transition-colors hover:border-zinc-300",
          "w-52 cursor-pointer"
        )}
      >
        <Search className="size-3.5 flex-shrink-0" />
        <span className="flex-1 text-left text-xs">Buscar...</span>
        <kbd className="text-[10px] font-medium bg-zinc-200 text-zinc-500 px-1.5 py-0.5 rounded">⌘K</kbd>
      </button>

      <SearchCommand open={commandOpen} onOpenChange={setCommandOpen} />

      {/* Empresa atual */}
      <button className="hidden lg:flex items-center gap-1.5 h-8 px-3 rounded-md border border-zinc-200 text-xs font-medium text-zinc-700 hover:bg-zinc-50 transition-colors">
        <Building2 className="size-3.5 text-zinc-400" />
        <span>{companyName}</span>
        <ChevronDown className="size-3 text-zinc-400" />
      </button>

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

      {/* Notificações */}
      <button className="relative flex size-8 items-center justify-center rounded-md border border-zinc-200 text-zinc-500 hover:bg-zinc-50 transition-colors">
        <Bell className="size-4" />
        <span className="absolute top-1 right-1 size-1.5 rounded-full bg-orange-500" />
      </button>

      <button
        type="button"
        onClick={logout}
        className="flex size-8 items-center justify-center rounded-md border border-zinc-200 text-zinc-500 transition-colors hover:bg-zinc-50 hover:text-zinc-900"
        aria-label="Sair"
      >
        <LogOut className="size-4" />
      </button>

      {/* Ações da página */}
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </header>
  )
}
