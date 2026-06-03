import { Shell } from "@/components/layout/shell"
import { Topbar } from "@/components/layout/topbar"
import { DashboardMetrics } from "@/features/dashboard/dashboard-metrics"
import { FluxoCaixaChart } from "@/features/dashboard/fluxo-caixa-chart"
import { AtencaoPanel } from "@/features/dashboard/atencao-panel"
import { DevedoresRecentes } from "@/features/dashboard/devedores-recentes"
import type { Metadata } from "next"

export const metadata: Metadata = { title: "Dashboard" }

export default function DashboardPage() {
  return (
    <Shell>
      <Topbar
        title="Painel do Dono"
        subtitle="Faturamento, crédito, financeiro e estoque em uma visão operacional"
      />

      <main className="flex-1 space-y-6 p-4 md:p-6">
        <DashboardMetrics />

        <AtencaoPanel />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <div className="lg:col-span-2">
            <FluxoCaixaChart />
          </div>
          <DevedoresRecentes />
        </div>
      </main>
    </Shell>
  )
}
