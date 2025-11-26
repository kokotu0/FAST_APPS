/**
 * DirectSend API 서비스
 */

import { OpenAPI } from "@/client"

const BASE_URL = OpenAPI.BASE || ""

interface MailReceiver {
  name: string
  email: string
  note1?: string
  note2?: string
  note3?: string
  note4?: string
  note5?: string
}

interface SMSReceiver {
  name: string
  mobile: string
  note1?: string
  note2?: string
  note3?: string
  note4?: string
  note5?: string
}

interface SendMailRequest {
  subject: string
  body: string
  receivers: MailReceiver[]
  sender_name?: string
}

interface SendSMSRequest {
  title: string
  message: string
  receivers: SMSReceiver[]
}

interface DirectSendResponse {
  success: boolean
  status: number
  message: string
  data?: Record<string, unknown>
}

interface ServiceStatus {
  configured: boolean
  service: string
}

function getHeaders(): HeadersInit {
  // 로컬 스토리지에서 직접 토큰을 가져옴
  const token = localStorage.getItem("access_token")
  
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

export const DirectSendMailService = {
  /**
   * 메일 발송
   */
  async sendMail(data: SendMailRequest): Promise<DirectSendResponse> {
    const response = await fetch(`${BASE_URL}/api/v1/directsend/mail/send`, {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify(data),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || "Failed to send mail")
    }

    return response.json()
  },

  /**
   * 메일 서비스 상태 확인
   */
  async getStatus(): Promise<ServiceStatus> {
    const response = await fetch(`${BASE_URL}/api/v1/directsend/mail/status`, {
      method: "GET",
      headers: getHeaders(),
    })

    if (!response.ok) {
      throw new Error("Failed to get mail service status")
    }

    return response.json()
  },
}

export const DirectSendSMSService = {
  /**
   * SMS 발송
   */
  async sendSMS(data: SendSMSRequest): Promise<DirectSendResponse> {
    const response = await fetch(`${BASE_URL}/api/v1/directsend/sms/send`, {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify(data),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || "Failed to send SMS")
    }

    return response.json()
  },

  /**
   * SMS 서비스 상태 확인
   */
  async getStatus(): Promise<ServiceStatus> {
    const response = await fetch(`${BASE_URL}/api/v1/directsend/sms/status`, {
      method: "GET",
      headers: getHeaders(),
    })

    if (!response.ok) {
      throw new Error("Failed to get SMS service status")
    }

    return response.json()
  },
}

export type {
  MailReceiver,
  SMSReceiver,
  SendMailRequest,
  SendSMSRequest,
  DirectSendResponse,
  ServiceStatus,
}

