"use client"

import { getErrorMessage } from "@/services/api"
import { useToast } from "@/context/toast-context"

export function useApiToast() {
  const { toast } = useToast()

  return {
    success: toast.success,
    error(error: unknown, title = "Operação não concluída") {
      toast.error(title, getErrorMessage(error))
    },
    info: toast.info,
  }
}
