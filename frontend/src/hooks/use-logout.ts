"use client"

import { useRouter } from "next/navigation"
import { queryClient } from "@/lib/query-client"
import { authService } from "@/services/auth.service"

export function useLogout() {
  const router = useRouter()

  return () => {
    authService.logout()
    queryClient.clear()
    router.replace("/login")
  }
}
