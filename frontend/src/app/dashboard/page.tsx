import { Shell } from "@/components/layout/shell"
import { Topbar } from "@/components/layout/topbar"
import { DashboardMetrics } from "@/features/dashboard/dashboard-metrics"
import { FluxoCaixaChart } from "@/features/dashboard/fluxo-caixa-chart"
import { AlertasPanel } from "@/features/dashboard/alertas-panel"
import { DevedoresRecentes } from "@/features/dashboard/devedores-recentes"
import type { Metadata } from "next"

export const metadata: Metadata = { title: "Dashboard" }

export default function DashboardPage() {
  return (
    <Shell>
      <Topbar
        title="Dashboard"
        subtitle="Visão geral da operação"
      />

      <main className="flex-1 p-6 space-y-5">
        {/* KPIs */}
        <DashboardMetrics />

        {/* Gráfico + Devedores */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <div className="lg:col-span-2">
            <FluxoCaixaChart />
          </div>
          <DevedoresRecentes />
        </div>

        {/* Alertas */}
        <AlertasPanel />
      </main>
    </Shell>
  )
}
