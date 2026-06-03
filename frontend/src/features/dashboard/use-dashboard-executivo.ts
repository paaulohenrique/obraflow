"use client"

import { useQuery } from "@tanstack/react-query"
import { relatoriosService } from "@/services/relatorios.service"

export function useDashboardExecutivo() {
  return useQuery({
    queryKey: ["relatorios", "dashboard-executivo"],
    queryFn: relatoriosService.dashboardExecutivo,
  })
}
