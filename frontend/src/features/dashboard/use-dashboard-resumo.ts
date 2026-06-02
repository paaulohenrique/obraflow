"use client"

import { useQuery } from "@tanstack/react-query"
import { dashboardService } from "@/services/dashboard.service"

export function useDashboardResumo() {
  return useQuery({
    queryKey: ["dashboard", "resumo"],
    queryFn: dashboardService.resumo,
  })
}
