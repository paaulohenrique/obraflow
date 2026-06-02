"use client"

import { useEffect, useState } from "react"
import { usePathname, useRouter } from "next/navigation"
import { SearchCommand } from "@/components/ui/search-command"

function isEditableTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) return false
  const tag = target.tagName.toLowerCase()
  return tag === "input" || tag === "textarea" || tag === "select" || target.isContentEditable
}

export function GlobalShortcuts() {
  const router = useRouter()
  const pathname = usePathname()
  const [commandOpen, setCommandOpen] = useState(false)

  useEffect(() => {
    const openCommand = () => setCommandOpen(true)
    window.addEventListener("obraflow:open-command", openCommand)
    return () => window.removeEventListener("obraflow:open-command", openCommand)
  }, [])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const key = event.key.toLowerCase()
      const editable = isEditableTarget(event.target)

      if ((event.ctrlKey || event.metaKey) && key === "k") {
        event.preventDefault()
        setCommandOpen(true)
        return
      }

      if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return

      if (event.key === "F2") {
        event.preventDefault()
        if (pathname?.startsWith("/fiado/")) {
          window.dispatchEvent(new Event("obraflow:open-product-search"))
          return
        }
        setCommandOpen(true)
        return
      }

      if (editable) return

      if (event.key === "F3") {
        event.preventDefault()
        router.push("/clientes")
        return
      }

      if (event.key === "F4") {
        event.preventDefault()
        router.push("/fiado")
      }
    }

    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [pathname, router])

  return <SearchCommand open={commandOpen} onOpenChange={setCommandOpen} />
}
