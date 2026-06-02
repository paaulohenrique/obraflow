import { clearAuthTokens, setAuthTokens } from "@/lib/auth-storage"
import type { AuthTokens, User } from "@/types"
import { api } from "./api"

export interface LoginPayload {
  email: string
  password: string
}

export const authService = {
  async login(payload: LoginPayload) {
    const response = await api.post<AuthTokens>("/auth/token/", payload)
    setAuthTokens(response.data)
    return response.data
  },

  me: async () => {
    const response = await api.get<User>("/auth/me/")
    return response.data
  },

  logout() {
    clearAuthTokens()
  },
}
