export const ACCESS_TOKEN_COOKIE = "obraflow_access_token"
export const REFRESH_TOKEN_COOKIE = "obraflow_refresh_token"

interface JwtPayload {
  exp?: number
  [key: string]: unknown
}

function isBrowser() {
  return typeof document !== "undefined"
}

function secureCookieSuffix() {
  if (typeof window === "undefined") return ""
  return window.location.protocol === "https:" ? "; Secure" : ""
}

export function getCookie(name: string) {
  if (!isBrowser()) return null
  const value = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`))
    ?.split("=")[1]

  return value ? decodeURIComponent(value) : null
}

export function setCookie(name: string, value: string, maxAgeSeconds: number) {
  if (!isBrowser()) return
  document.cookie = [
    `${name}=${encodeURIComponent(value)}`,
    "Path=/",
    "SameSite=Lax",
    `Max-Age=${maxAgeSeconds}`,
    secureCookieSuffix(),
  ].join("; ")
}

export function deleteCookie(name: string) {
  if (!isBrowser()) return
  document.cookie = `${name}=; Path=/; SameSite=Lax; Max-Age=0${secureCookieSuffix()}`
}

export function getAccessToken() {
  return getCookie(ACCESS_TOKEN_COOKIE)
}

export function getRefreshToken() {
  return getCookie(REFRESH_TOKEN_COOKIE)
}

export function setAccessToken(token: string) {
  setCookie(ACCESS_TOKEN_COOKIE, token, 60 * 60 * 24)
}

export function setRefreshToken(token: string) {
  setCookie(REFRESH_TOKEN_COOKIE, token, 60 * 60 * 24 * 14)
}

export function setAuthTokens(tokens: { access: string; refresh?: string }) {
  setAccessToken(tokens.access)
  if (tokens.refresh) setRefreshToken(tokens.refresh)
}

export function clearAuthTokens() {
  deleteCookie(ACCESS_TOKEN_COOKIE)
  deleteCookie(REFRESH_TOKEN_COOKIE)
}

export function hasAuthTokens() {
  return Boolean(getAccessToken() || getRefreshToken())
}

export function decodeJwtPayload(token: string): JwtPayload | null {
  try {
    const payload = token.split(".")[1]
    if (!payload) return null
    const base64 = payload.replace(/-/g, "+").replace(/_/g, "/")
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=")
    return JSON.parse(atob(padded)) as JwtPayload
  } catch {
    return null
  }
}

export function isJwtExpired(token: string, skewSeconds = 30) {
  const payload = decodeJwtPayload(token)
  if (!payload?.exp) return false
  return payload.exp <= Math.floor(Date.now() / 1000) + skewSeconds
}
