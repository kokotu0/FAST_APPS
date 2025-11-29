import { useMutation } from "@tanstack/react-query"
import { DirectsendMailService } from "@/client"
import type { SendEmailParams, FormSurveyEmailParams } from "../types"
import { getFormSurveyTemplate } from "../templates"

/**
 * 이메일 발송 훅
 */
export function useMailSend() {
  // 단일 이메일 발송
  const sendEmailMutation = useMutation({
    mutationFn: async (params: SendEmailParams) => {
      const recipients = Array.isArray(params.to) ? params.to : [params.to]
      
      return await DirectsendMailService.sendMail({
        requestBody: {
          subject: params.subject,
          body: params.body,
          receivers: recipients.map(email => ({ email })),
        },
      })
    },
  })

  // 폼 설문조사 이메일 발송 (단일)
  const sendFormSurveyEmailMutation = useMutation({
    mutationFn: async (params: FormSurveyEmailParams) => {
      const { subject, body } = getFormSurveyTemplate(params)
      
      return await DirectsendMailService.sendMail({
        requestBody: {
          subject,
          body,
          receivers: [{ email: params.receiverEmail, name: params.receiverName }],
        },
      })
    },
  })

  // 폼 설문조사 이메일 일괄 발송
  const sendFormSurveyEmailsBatchMutation = useMutation({
    mutationFn: async (paramsList: FormSurveyEmailParams[]) => {
      // 각 수신자에게 개별 이메일 전송 (개인화된 URL 때문에)
      const results = await Promise.allSettled(
        paramsList.map(async (params) => {
          const { subject, body } = getFormSurveyTemplate(params)
          
          return await DirectsendMailService.sendMail({
            requestBody: {
              subject,
              body,
              receivers: [{ email: params.receiverEmail, name: params.receiverName }],
            },
          })
        })
      )

      const succeeded = results.filter(r => r.status === 'fulfilled').length
      const failed = results.filter(r => r.status === 'rejected').length
      
      return { 
        total: paramsList.length,
        succeeded, 
        failed,
        results,
      }
    },
  })

  return {
    // 기본 이메일 발송
    sendEmail: sendEmailMutation.mutateAsync,
    sendEmailMutation,
    isSending: sendEmailMutation.isPending,
    
    // 폼 설문조사 이메일 발송
    sendFormSurveyEmail: sendFormSurveyEmailMutation.mutateAsync,
    sendFormSurveyEmailMutation,
    isSendingFormSurvey: sendFormSurveyEmailMutation.isPending,
    
    // 폼 설문조사 이메일 일괄 발송
    sendFormSurveyEmailsBatch: sendFormSurveyEmailsBatchMutation.mutateAsync,
    sendFormSurveyEmailsBatchMutation,
    isSendingBatch: sendFormSurveyEmailsBatchMutation.isPending,
  }
}

