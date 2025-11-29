export interface EmailTemplate {
  subject: string
  body: string  // HTML 템플릿
}

export interface SendEmailParams {
  to: string | string[]
  subject: string
  body: string
  // DirectSend API 옵션
  sender?: string
  senderName?: string
}

export interface FormSurveyEmailParams {
  receiverEmail: string
  receiverName?: string
  formTitle: string
  formDescription?: string
  formUrl: string
  expiredAt: string
  senderName?: string
}

