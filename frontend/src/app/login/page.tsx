import type { Metadata } from "next"
import { Suspense } from "react"
import { LoginForm } from "@/features/auth/login-form"

export const metadata: Metadata = { title: "Login" }

export default function LoginPage() {
  return (
    <main className="min-h-screen bg-zinc-950 text-white">
      <div className="grid min-h-screen grid-cols-1 lg:grid-cols-[1fr_460px]">
        <section className="hidden bg-[radial-gradient(circle_at_20%_20%,rgba(249,115,22,0.22),transparent_32%),linear-gradient(135deg,#09090b_0%,#18181b_52%,#2a1208_100%)] lg:block">
          <div className="flex h-full flex-col justify-between p-10">
            <div className="flex items-center gap-3">
              <div className="flex size-9 items-center justify-center rounded-md bg-orange-500 text-sm font-bold">
                MP
              </div>
              <div>
                <p className="text-sm font-semibold leading-tight">MP Construções</p>
                <p className="text-xs text-zinc-400">ObraFlow ERP</p>
              </div>
            </div>

            <div className="max-w-xl pb-10">
              <p className="text-4xl font-semibold leading-tight tracking-normal">
                Operação conectada ao backend real.
              </p>
              <p className="mt-4 max-w-md text-sm leading-6 text-zinc-300">
                Clientes, estoque, financeiro e fiado em uma rotina única para a loja.
              </p>
            </div>
          </div>
        </section>

        <section className="flex min-h-screen items-center justify-center bg-white px-6 text-zinc-950">
          <div className="w-full max-w-sm">
            <div className="mb-8 lg:hidden">
              <div className="flex items-center gap-3">
                <div className="flex size-9 items-center justify-center rounded-md bg-orange-500 text-sm font-bold text-white">
                  MP
                </div>
                <div>
                  <p className="text-sm font-semibold leading-tight">MP Construções</p>
                  <p className="text-xs text-zinc-500">ObraFlow ERP</p>
                </div>
              </div>
            </div>

            <div className="mb-6">
              <h1 className="text-xl font-semibold tracking-normal text-zinc-950">Acessar conta</h1>
              <p className="mt-1 text-sm text-zinc-500">Use suas credenciais cadastradas no backend.</p>
            </div>

            <Suspense fallback={<div className="h-52 rounded-lg border border-zinc-100 bg-zinc-50" />}>
              <LoginForm />
            </Suspense>
          </div>
        </section>
      </div>
    </main>
  )
}
