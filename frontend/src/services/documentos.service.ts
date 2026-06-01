import type { ApiDecimal, PaginatedResponse, PaginationParams } from "@/types"
import { api } from "./api"
import { toQueryString } from "./query-params"

export interface BoletoOCR {
  id: string
  arquivo_nome_original: string
  status: string
  fornecedor_nome_final: string
  banco_nome: string
  valor: ApiDecimal | null
  vencimento: string | null
  confianca_ocr: ApiDecimal | null
  erro_mensagem: string
  created_at: string
}

export interface DashboardBoletos {
  boletos_enviados_hoje: number
  boletos_processados_hoje: number
  pendentes_revisao: number
  ocrs_com_erro: number
  contas_pagar_geradas: number
  valor_total_identificado: ApiDecimal
  valor_total_confirmado: ApiDecimal
  taxa_sucesso_ocr: ApiDecimal
  confianca_media: ApiDecimal
  vencimentos_7_dias: number
  vencimentos_30_dias: number
}

export interface NotaEntrada {
  id: string
  status: string
  numero: string
  serie: string
  modelo: string
  data_emissao: string | null
  fornecedor_nome_final: string
  fornecedor_cnpj_xml: string
  valor_total: ApiDecimal
  itens_total: number
  itens_sem_produto: number
  created_at: string
}

export interface DashboardNotasEntrada {
  notas_importadas_hoje: number
  aguardando_revisao: number
  confirmadas_mes: number
  rejeitadas_mes: number
  valor_total_importado_mes: ApiDecimal
  valor_total_confirmado_mes: ApiDecimal
  movimentacoes_estoque_geradas_mes: number
  contas_pagar_criadas_mes: number
  fornecedores_novos_detectados: number
  itens_sem_produto_pendentes: number
}

export const boletosService = {
  async list(params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<BoletoOCR>>(`/boletos/${toQueryString(params)}`)
    return response.data
  },

  async dashboard() {
    const response = await api.get<DashboardBoletos>("/boletos/dashboard/")
    return response.data
  },
}

export const notasEntradaService = {
  async list(params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<NotaEntrada>>(`/notas-entrada/${toQueryString(params)}`)
    return response.data
  },

  async dashboard() {
    const response = await api.get<DashboardNotasEntrada>("/notas-entrada/dashboard/")
    return response.data
  },
}
