import type { Cliente, ClientePayload, PaginatedResponse, PaginationParams } from "@/types"
import { api } from "./api"
import { toQueryString } from "./query-params"

export const clientesService = {
  async list(params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<Cliente>>(`/clientes/${toQueryString(params)}`)
    return response.data
  },

  async inadimplentes(params?: PaginationParams) {
    const response = await api.get<PaginatedResponse<Cliente>>(`/clientes/inadimplentes/${toQueryString(params)}`)
    return response.data
  },

  async get(id: string) {
    const response = await api.get<Cliente>(`/clientes/${id}/`)
    return response.data
  },

  async create(data: ClientePayload) {
    const response = await api.post<Cliente>("/clientes/", data)
    return response.data
  },

  async update(id: string, data: Partial<ClientePayload>) {
    const response = await api.patch<Cliente>(`/clientes/${id}/`, data)
    return response.data
  },
}
