import type {
  BoletoOCR,
  BoletoOCRDetail,
  BoletoDashboard,
  ConfirmarBoletoPayload,
  HistoricoBoleto,
  PaginatedResponse,
  PaginationParams,
} from "@/types"
import { api } from "./api"
import { toQueryString } from "./query-params"

export const boletosService = {
  async list(params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<BoletoOCR>>(`/boletos/${toQueryString(params)}`)
    return response.data
  },

  async getBoleto(id: string) {
    const response = await api.get<BoletoOCRDetail>(`/boletos/${id}/`)
    return response.data
  },

  async uploadBoleto(file: File, observacao = "", idempotencyKey = "") {
    const formData = new FormData()
    formData.append("arquivo", file)
    if (observacao) {
      formData.append("observacao", observacao)
    }
    if (idempotencyKey) {
      formData.append("idempotency_key", idempotencyKey)
    }

    const response = await api.post<BoletoOCRDetail>("/boletos/upload/", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    })
    return response.data
  },

  async confirmarBoleto(id: string, payload: ConfirmarBoletoPayload) {
    const response = await api.post<BoletoOCRDetail>(`/boletos/${id}/confirmar/`, payload)
    return response.data
  },

  async rejeitarBoleto(id: string, motivo: string) {
    const response = await api.post<BoletoOCRDetail>(`/boletos/${id}/rejeitar/`, { motivo })
    return response.data
  },

  async reprocessarBoleto(id: string, idempotencyKey = "") {
    const payload = idempotencyKey ? { idempotency_key: idempotencyKey } : {}
    const response = await api.post<BoletoOCRDetail>(`/boletos/${id}/reprocessar/`, payload)
    return response.data
  },

  async baixarBoleto(id: string) {
    const response = await api.get<Blob>(`/boletos/${id}/download/`, {
      responseType: "blob",
    })
    return response.data
  },

  async getHistoricoBoleto(id: string, params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<HistoricoBoleto>>(
      `/boletos/${id}/historico/${toQueryString(params)}`
    )
    return response.data
  },

  async getDashboardBoletos() {
    const response = await api.get<BoletoDashboard>("/boletos/dashboard/")
    return response.data
  },
}
