import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { FormRegisterService, type FormRegisterRequest, type ApiError } from "@/client"
import { handleError } from "@/utils"

/**
 * Form 등록 관련 훅
 */
export const useFormRegister = () => {
  const queryClient = useQueryClient()

  // Form 목록 조회
  const useFormList = (page = 1, pageSize = 10) => {
    return useQuery({
      queryKey: ["forms", page, pageSize],
      queryFn: () => FormRegisterService.getFormList({ page, pageSize }),
    })
  }

  // Form 단일 조회
  const useFormDetail = (formId: number) => {
    return useQuery({
      queryKey: ["form", formId],
      queryFn: () => FormRegisterService.getFormWithWrapper({ formId }),
      enabled: !!formId,
    })
  }

  // Form 등록
  const registerMutation = useMutation({
    mutationFn: (data: FormRegisterRequest) =>
      FormRegisterService.registerForm({ requestBody: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["forms"] })
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
  })

  return {
    useFormList,
    useFormDetail,
    registerMutation,
  }
}

export default useFormRegister

