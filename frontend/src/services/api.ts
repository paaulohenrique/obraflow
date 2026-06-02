import axios, { AxiosError, AxiosHeaders, type InternalAxiosRequestConfig } from "axios"
import {
  clearAuthTokens,
  getAccessToken,
  getRefreshToken,
  isJwtExpired,
  setAuthTokens,
} from "@/lib/auth-storage"
import type { ApiError } from "@/types"

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"
const TIMEOUT_MS = 15000

interface RetryableRequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean
}

interface RefreshResponse {
  access: string
  refresh?: string
}

export class ObraFlowApiError extends Error implements ApiError {
  status: number
  errors?: Record<string, string[] | string>
  requestId?: string

  constructor(error: ApiError) {
    super(error.message)
    this.name = "ObraFlowApiError"
    this.status = error.status
    this.errors = error.errors
    this.requestId = error.requestId
  }
}

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: TIMEOUT_MS,
  headers: {
    Accept: "application/json",
    "Content-Type": "application/json",
  },
})

const refreshApi = axios.create({
  baseURL: BASE_URL,
  timeout: TIMEOUT_MS,
  headers: {
    Accept: "application/json",
    "Content-Type": "application/json",
  },
})

let refreshPromise: Promise<string | null> | null = null

function createRequestId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID()
  }

  return `req_${Date.now()}_${Math.random().toString(16).slice(2)}`
}

function isAuthUrl(url?: string) {
  return Boolean(url?.includes("/auth/token/"))
}

function redirectToLogin() {
  if (typeof window === "undefined") return
  window.dispatchEvent(new CustomEvent("obraflow:auth-expired"))
  if (!window.location.pathname.startsWith("/login")) {
    window.location.assign("/login")
  }
}

async function refreshAccessToken() {
  const refresh = getRefreshToken()

  if (!refresh || isJwtExpired(refresh, 0)) {
    clearAuthTokens()
    return null
  }

  if (!refreshPromise) {
    refreshPromise = refreshApi
      .post<RefreshResponse>("/auth/token/refresh/", { refresh })
      .then((response) => {
        setAuthTokens(response.data)
        return response.data.access
      })
      .catch(() => {
        clearAuthTokens()
        return null
      })
      .finally(() => {
        refreshPromise = null
      })
  }

  return refreshPromise
}

function extractMessage(data: unknown, fallback: string) {
  if (!data || typeof data !== "object") return fallback
  const body = data as Record<string, unknown>

  if (typeof body.detail === "string") return body.detail
  if (typeof body.message === "string") return body.message
  if (Array.isArray(body.non_field_errors) && typeof body.non_field_errors[0] === "string") {
    return body.non_field_errors[0]
  }

  // Backend retorna erros de campo em detail como objeto: {"campo": ["msg"]}
  if (body.detail && typeof body.detail === "object" && !Array.isArray(body.detail)) {
    const fieldErrors = body.detail as Record<string, string | string[]>
    const firstEntry = Object.entries(fieldErrors)[0]
    if (firstEntry) {
      const [, messages] = firstEntry
      return Array.isArray(messages) ? messages[0] : String(messages)
    }
  }

  return fallback
}

function extractFieldErrors(data: unknown) {
  if (!data || typeof data !== "object" || Array.isArray(data)) return undefined

  const body = data as Record<string, unknown>
  const rawDetail = body.detail
  if (rawDetail && typeof rawDetail === "object" && !Array.isArray(rawDetail)) {
    return rawDetail as Record<string, string[] | string>
  }

  const fieldErrors = Object.entries(body).reduce<Record<string, string[] | string>>((acc, [key, value]) => {
    if (key === "detail" || key === "message") return acc
    if (typeof value === "string" || Array.isArray(value)) {
      acc[key] = value as string | string[]
    }
    return acc
  }, {})

  return Object.keys(fieldErrors).length > 0 ? fieldErrors : undefined
}

export function normalizeApiError(error: unknown): ObraFlowApiError {
  if (error instanceof ObraFlowApiError) return error

  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<Record<string, unknown>>
    const status = axiosError.response?.status ?? 0
    const requestId =
      axiosError.response?.headers?.["x-request-id"] ??
      axiosError.response?.headers?.["X-Request-ID"]

    const fallback =
      status === 0
        ? "Não foi possível conectar ao servidor."
        : status === 401
          ? "Sessão expirada. Faça login novamente."
          : status === 403
            ? "Você não tem permissão para acessar este recurso."
            : status === 404
              ? "Registro não encontrado."
              : status >= 500
                ? "O servidor não conseguiu concluir a operação agora."
                : "Não foi possível concluir a operação."

    return new ObraFlowApiError({
      status,
      message: extractMessage(axiosError.response?.data, fallback),
      errors: extractFieldErrors(axiosError.response?.data),
      requestId: typeof requestId === "string" ? requestId : undefined,
    })
  }

  return new ObraFlowApiError({
    status: 0,
    message: "Não foi possível concluir a operação.",
  })
}

export function getErrorMessage(error: unknown) {
  return normalizeApiError(error).message
}

api.interceptors.request.use(async (config) => {
  const headers = AxiosHeaders.from(config.headers)
  if (!headers.get("Accept")) {
    headers.set("Accept", "application/json")
  }
  headers.set("X-Request-ID", createRequestId())

  let access = getAccessToken()
  if (access && isJwtExpired(access) && !isAuthUrl(config.url)) {
    access = await refreshAccessToken()
  }

  if (access && !isAuthUrl(config.url)) {
    headers.set("Authorization", `Bearer ${access}`)
  }

  config.headers = headers
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as RetryableRequestConfig | undefined
    const status = error.response?.status

    if (status === 401 && original && !original._retry && !isAuthUrl(original.url)) {
      original._retry = true
      const access = await refreshAccessToken()

      if (access) {
        const headers = AxiosHeaders.from(original.headers)
        headers.set("Authorization", `Bearer ${access}`)
        original.headers = headers
        return api(original)
      }
    }

    if (status === 401 && !isAuthUrl(original?.url)) {
      clearAuthTokens()
      redirectToLogin()
    }

    return Promise.reject(normalizeApiError(error))
  }
)
