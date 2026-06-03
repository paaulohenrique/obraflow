import type {
  CobrancaConta,
  CobrancaPreview,
  ConfiguracaoCobranca,
  DashboardCobranca,
  EnviarCobrancaPayload,
  EnviarLoteCobrancaPayload,
  NotificacaoCobranca,
  PaginatedResponse,
  PaginationParams,
  ResultadoLoteCobranca,
} from "@/types"
import { api } from "./api"
import { toQueryString } from "./query-params"

export const cobrancasService = {
  async list(params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<CobrancaConta>>(
      `/cobrancas/${toQueryString(params)}`
    )
    return response.data
  },

  async dashboard(params?: PaginationParams) {
    const response = await api.get<DashboardCobranca>(
      `/cobrancas/dashboard/${toQueryString(params)}`
    )
    return response.data
  },

  async preview(payload: EnviarCobrancaPayload) {
    const response = await api.post<CobrancaPreview>("/cobrancas/preview/", payload)
    return response.data
  },

  async enviar(payload: EnviarCobrancaPayload) {
    const response = await api.post<NotificacaoCobranca>("/cobrancas/enviar/", payload)
    return response.data
  },

  async enviarLote(payload: EnviarLoteCobrancaPayload) {
    const response = await api.post<ResultadoLoteCobranca>("/cobrancas/lote/enviar/", payload)
    return response.data
  },

  async historicoCliente(clienteId: string, params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<NotificacaoCobranca>>(
      `/cobrancas/historico-cliente/${toQueryString({ cliente: clienteId, page_size: 20, ...params })}`
    )
    return response.data
  },

  async configuracao() {
    const response = await api.get<ConfiguracaoCobranca>("/cobrancas/configuracao/")
    return response.data
  },

  async atualizarConfiguracao(payload: Partial<ConfiguracaoCobranca>) {
    const response = await api.patch<ConfiguracaoCobranca>("/cobrancas/configuracao/", payload)
    return response.data
  },
}
