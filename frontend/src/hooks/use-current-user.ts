"use client"

import { useQuery } from "@tanstack/react-query"
import { hasAuthTokens } from "@/lib/auth-storage"
import { authService } from "@/services/auth.service"
import { empresasService } from "@/services/empresas.service"
import type { AuthUser } from "@/types"

export function useCurrentUser() {
  const userQuery = useQuery({
    queryKey: ["auth", "me"],
    queryFn: authService.me,
    enabled: hasAuthTokens(),
    retry: false,
  })

  const empresaQuery = useQuery({
    queryKey: ["empresas", userQuery.data?.company_id],
    queryFn: () => empresasService.get(userQuery.data?.company_id ?? ""),
    enabled: Boolean(userQuery.data?.company_id),
    retry: false,
  })

  const user: AuthUser | undefined = userQuery.data
    ? {
        ...userQuery.data,
        empresa: empresaQuery.data ?? null,
      }
    : undefined

  return {
    user,
    empresa: empresaQuery.data,
    isLoading: userQuery.isLoading || empresaQuery.isLoading,
    isError: userQuery.isError || empresaQuery.isError,
    error: userQuery.error ?? empresaQuery.error,
    refetch: userQuery.refetch,
  }
}
