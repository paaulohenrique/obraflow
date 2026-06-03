import type {
  CancelarContaPagarPayload,
  CancelarLancamentoPayload,
  CategoriaFinanceira,
  ConfiguracaoFinanceiraOperacional,
  ConfiguracaoFinanceiraOperacionalPayload,
  ContaFinanceira,
  ContaPagar,
  CriarContaPagarPayload,
  CriarLancamentoPayload,
  DashboardFinanceiro,
  LancamentoFinanceiro,
  PagarContaPagarPayload,
  PaginatedResponse,
  PaginationParams,
} from "@/types"
import { api } from "./api"
import { toQueryString } from "./query-params"

export const financeiroService = {
  async dashboard() {
    const response = await api.get<DashboardFinanceiro>("/financeiro/dashboard/")
    return response.data
  },

  async configuracaoOperacional() {
    const response = await api.get<ConfiguracaoFinanceiraOperacional>(
      "/financeiro/configuracao-operacional/"
    )
    return response.data
  },

  async atualizarConfiguracaoOperacional(payload: ConfiguracaoFinanceiraOperacionalPayload) {
    const response = await api.patch<ConfiguracaoFinanceiraOperacional>(
      "/financeiro/configuracao-operacional/atualizar/",
      payload
    )
    return response.data
  },

  // ─── Contas a Pagar ───────────────────────────────────────────────────────

  async contasPagar(params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<ContaPagar>>(
      `/financeiro/contas-pagar/${toQueryString(params)}`
    )
    return response.data
  },

  async getContaPagar(id: string) {
    const response = await api.get<ContaPagar>(`/financeiro/contas-pagar/${id}/`)
    return response.data
  },

  async criarContaPagar(payload: CriarContaPagarPayload) {
    const response = await api.post<ContaPagar>("/financeiro/contas-pagar/", payload)
    return response.data
  },

  async pagarContaPagar(id: string, payload: PagarContaPagarPayload) {
    const response = await api.post<ContaPagar>(
      `/financeiro/contas-pagar/${id}/pagar/`,
      payload
    )
    return response.data
  },

  async cancelarContaPagar(id: string, payload: CancelarContaPagarPayload) {
    const response = await api.post<ContaPagar>(
      `/financeiro/contas-pagar/${id}/cancelar/`,
      payload
    )
    return response.data
  },

  // ─── Lançamentos ──────────────────────────────────────────────────────────

  async lancamentos(params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<LancamentoFinanceiro>>(
      `/financeiro/lancamentos/${toQueryString(params)}`
    )
    return response.data
  },

  async criarLancamento(payload: CriarLancamentoPayload) {
    const response = await api.post<LancamentoFinanceiro>(
      "/financeiro/lancamentos/",
      payload
    )
    return response.data
  },

  async cancelarLancamento(id: string, payload: CancelarLancamentoPayload) {
    const response = await api.post<LancamentoFinanceiro>(
      `/financeiro/lancamentos/${id}/cancelar/`,
      payload
    )
    return response.data
  },

  // ─── Categorias ───────────────────────────────────────────────────────────

  async categorias(params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<CategoriaFinanceira>>(
      `/financeiro/categorias/${toQueryString(params)}`
    )
    return response.data
  },

  // ─── Contas Financeiras ───────────────────────────────────────────────────

  async contasFinanceiras(params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<ContaFinanceira>>(
      `/financeiro/contas-financeiras/${toQueryString(params)}`
    )
    return response.data
  },
}
