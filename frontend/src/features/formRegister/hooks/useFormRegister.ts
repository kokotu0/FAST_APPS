import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import {
  FormRegisterService,
  type FormRegisterGetFormListResponse,
  type FormRegisterCreateFormData,
  type FormRegisterUpdateFormData,
  type FormRegisterGetFormResponse,
  type FormRegisterCreateFormResponse,
  type FormRegisterUpdateFormResponse,
  type FormRegisterDeleteFormResponse,
} from "@/client"

// 타입 re-export
export type {
  FormRegisterGetFormListResponse,
  FormRegisterGetFormResponse,
  FormRegisterCreateFormResponse,
  FormRegisterUpdateFormResponse,
  FormRegisterDeleteFormResponse,
}

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

  // Form 단일 조회 (uuid)
  const useFormDetail = (formUuid: string | undefined) => {
    return useQuery({
      queryKey: ["form", formUuid],
      queryFn: () => FormRegisterService.getForm({ formUuid: formUuid! }),
      enabled: !!formUuid && formUuid !== "new",
    })
  }

  // Form 생성
  const createMutation = useMutation({
    mutationFn: (data: FormRegisterCreateFormData["requestBody"]) =>
      FormRegisterService.createForm({ requestBody: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["forms"] })
    },
  })

  // Form 수정
  const updateMutation = useMutation({
    mutationFn: ({ formUuid, data }: { formUuid: string; data: FormRegisterUpdateFormData["requestBody"] }) =>
      FormRegisterService.updateForm({ formUuid, requestBody: data }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["forms"] })
      queryClient.invalidateQueries({ queryKey: ["form", variables.formUuid] })
    },
  })

  // Form 삭제
  const deleteMutation = useMutation({
    mutationFn: (formUuid: string) =>
      FormRegisterService.deleteForm({ formUuid }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["forms"] })
    },
  })

  return {
    useFormList,
    useFormDetail,
    createMutation,
    updateMutation,
    deleteMutation,
  }
}

export default useFormRegister
