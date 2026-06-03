"use client"

import { FileText, Loader2, AlertCircle, CheckCircle, DollarSign, Calendar } from "lucide-react"
import { StatCard } from "@/components/ui/stat-card"
import { formatCurrency } from "@/lib/utils"
import type { BoletoDashboard } from "@/types"

interface BoletosDashboardCardsProps {
  data?: BoletoDashboard
  isLoading: boolean
}

export function BoletosDashboardCards({ data, isLoading }: BoletosDashboardCardsProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-6">
        {Array.from({ length: 6 }).map((_, index) => (
          <StatCard key={index} label="" value="" loading />
        ))}
      </div>
    )
  }

  const pendentes = data?.pendentes_revisao ?? 0
  const comErro = data?.ocrs_com_erro ?? 0
  const confirmados = data?.contas_pagar_geradas ?? 0
  const valorConfirmado = Number(data?.valor_total_confirmado ?? 0)
  const vencendoSeteDias = data?.vencimentos_7_dias ?? 0

  // Se o backend não fornece um campo explícito de "processando", podemos estimar
  // ou simplesmente manter como 0 ou baseado em alguma conta lógica básica (ex: enviados hoje - processados hoje).
  // Vamos calcular: boletos_enviados_hoje - boletos_processados_hoje se positivo, senão 0.
  const processando = Math.max((data?.boletos_enviados_hoje ?? 0) - (data?.boletos_processados_hoje ?? 0), 0)

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-6">
      <StatCard
        label="Pendentes de Revisão"
        value={String(pendentes)}
        accent={pendentes > 0}
        icon={<FileText className="size-4" />}
      />
      <StatCard
        label="Processando OCR"
        value={String(processando)}
        icon={<Loader2 className={`size-4 ${processando > 0 ? 'animate-spin text-orange-500' : ''}`} />}
      />
      <StatCard
        label="Com Erro de OCR"
        value={String(comErro)}
        accent={comErro > 0}
        icon={<AlertCircle className="size-4" />}
      />
      <StatCard
        label="Confirmados"
        value={String(confirmados)}
        icon={<CheckCircle className="size-4" />}
      />
      <StatCard
        label="Valor Confirmado"
        value={formatCurrency(valorConfirmado)}
        icon={<DollarSign className="size-4" />}
      />
      <StatCard
        label="Vencimento < 7 dias"
        value={String(vencendoSeteDias)}
        accent={vencendoSeteDias > 0}
        icon={<Calendar className="size-4" />}
      />
    </div>
  )
}
