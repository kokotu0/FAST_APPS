import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { FormRegisterService } from "@/client"

import type {
  FormRegisterGetFormListResponse,
  FormRegisterCreateFormData,
  FormRegisterUpdateFormData,
  FormRegisterGetFormResponse,
  FormRegisterCreateFormResponse,
  FormRegisterUpdateFormResponse,
  FormRegisterDeleteFormResponse,
} from "@/client"

// 타입 re-export
export type {
  FormRegisterGetFormListResponse,
  FormRegisterGetFormResponse,
  FormRegisterCreateFormResponse,
  FormRegisterUpdateFormResponse,
  FormRegisterDeleteFormResponse,
}

// 배포 관련 타입
export interface FormPublishItem {
  idx: number
  form_idx: number
  receiver: string
  receiver_name: string | null
  token: string
  expired_at: string
  // 이메일 전송 관련
  is_email_sent: boolean
  email_sent_at: string | null
  email_sent_count: number
  // 응답 관련
  is_submitted: boolean
  submitted_at: string | null
  responseSchema: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface FormPublishListResponse {
  items: FormPublishItem[]
  total: number
  page: number
  page_size: number
  has_next: boolean
  has_prev: boolean
}

export interface PublicFormData {
  title: string
  description: string | null
  JSONSchema: Record<string, unknown>
  UISchema: Record<string, unknown>
  Theme: string
  receiver_name: string | null
  is_submitted: boolean
  expired_at: string
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

  // Form 단일 조회 (uuid 기반)
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

  // ============ 배포 관련 ============

  // 배포 목록 조회 (uuid 기반) - SDK 사용
  const usePublishList = (formUuid: string | undefined, page = 1, pageSize = 10) => {
    return useQuery({
      queryKey: ["publishes", formUuid, page, pageSize],
      queryFn: () => FormRegisterService.getFormPublishes({ formUuid: formUuid!, page, pageSize }),
      enabled: !!formUuid && formUuid !== "new",
    })
  }

  // 배포 생성 (uuid 기반) - SDK 사용
  const createPublishMutation = useMutation({
    mutationFn: ({ formUuid, data }: { formUuid: string; data: { receiver: string; receiver_name?: string; expired_days?: number } }) => {
      return FormRegisterService.createFormPublish({
        formUuid,
        requestBody: data,
      })
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["publishes", variables.formUuid] })
    },
  })

  // 배포 일괄 생성 (uuid 기반) - SDK 사용
  const createPublishBatchMutation = useMutation({
    mutationFn: ({ formUuid, data }: { formUuid: string; data: { receivers: Array<{ receiver: string; receiver_name?: string }>; expired_days?: number } }) => {
      return FormRegisterService.createFormPublishBatch({
        formUuid,
        requestBody: data,
      })
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["publishes", variables.formUuid] })
    },
  })

  // 배포 삭제 (uuid 기반) - SDK 사용
  const deletePublishMutation = useMutation({
    mutationFn: ({ formUuid, publishIdx }: { formUuid: string; publishIdx: number }) => {
      return FormRegisterService.deleteFormPublish({
        formUuid,
        publishIdx,
      })
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["publishes", variables.formUuid] })
    },
  })

  return {
    useFormList,
    useFormDetail,
    createMutation,
    updateMutation,
    deleteMutation,
    // 배포 관련
    usePublishList,
    createPublishMutation,
    createPublishBatchMutation,
    deletePublishMutation,
  }
}

export default useFormRegister
