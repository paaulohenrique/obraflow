import { NextResponse, type NextRequest } from "next/server"
import { ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE, isJwtExpired } from "@/lib/auth-storage"

const protectedRoutes = [
  "/dashboard",
  "/clientes",
  "/estoque",
  "/fiado",
  "/financeiro",
  "/boletos",
  "/cobrancas",
  "/fiscal",
  "/relatorios",
  "/configuracoes",
]

function isProtectedPath(pathname: string) {
  return protectedRoutes.some((route) => pathname === route || pathname.startsWith(`${route}/`))
}

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl
  const access = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value
  const refresh = request.cookies.get(REFRESH_TOKEN_COOKIE)?.value

  if (pathname === "/login" && (access || refresh)) {
    return NextResponse.redirect(new URL("/dashboard", request.url))
  }

  if (!isProtectedPath(pathname)) {
    return NextResponse.next()
  }

  const hasValidAccess = Boolean(access && !isJwtExpired(access, 0))
  const hasRefresh = Boolean(refresh && !isJwtExpired(refresh, 0))

  if (!hasValidAccess && !hasRefresh) {
    const loginUrl = new URL("/login", request.url)
    loginUrl.searchParams.set("next", pathname)
    return NextResponse.redirect(loginUrl)
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    "/login",
    "/dashboard/:path*",
    "/clientes/:path*",
    "/estoque/:path*",
    "/fiado/:path*",
    "/financeiro/:path*",
    "/boletos/:path*",
    "/cobrancas/:path*",
    "/fiscal/:path*",
    "/relatorios/:path*",
    "/configuracoes/:path*",
  ],
}
