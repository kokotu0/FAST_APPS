"""
DirectSend API Service Layer
메일 및 SMS 발송 서비스
"""

import httpx
from typing import Any
from pydantic import BaseModel, EmailStr

from app.core.config import settings


class MailReceiver(BaseModel):
    """메일 수신자 정보"""
    name: str
    email: EmailStr
    note1: str = ""
    note2: str = ""
    note3: str = ""
    note4: str = ""
    note5: str = ""


class SMSReceiver(BaseModel):
    """SMS 수신자 정보"""
    name: str
    mobile: str
    note1: str = ""
    note2: str = ""
    note3: str = ""
    note4: str = ""
    note5: str = ""


class MailRequest(BaseModel):
    """메일 발송 요청"""
    subject: str
    body: str
    receivers: list[MailReceiver]
    sender_name: str | None = None


class SMSRequest(BaseModel):
    """SMS 발송 요청"""
    title: str  # MMS/LMS 제목 (최대 40byte)
    message: str  # 메시지 내용 (최대 2000byte)
    receivers: list[SMSReceiver]


class DirectSendResponse(BaseModel):
    """DirectSend API 응답"""
    status: int
    msg: str
    data: dict[str, Any] | None = None


class DirectSendMailService:
    """DirectSend 메일 발송 서비스"""
    
    BASE_URL = "https://directsend.co.kr/index.php/api_v2/mail_change_word"
    
    def __init__(self):
        self.username = settings.DIRECTSEND_USERNAME
        self.api_key = settings.DIRECTSEND_API_KEY
        self.sender_email = settings.DIRECTSEND_SENDER_EMAIL
        self.sender_name = settings.DIRECTSEND_SENDER_NAME
    
    @property
    def is_configured(self) -> bool:
        """DirectSend 설정이 완료되었는지 확인"""
        return bool(
            self.username and 
            self.api_key and 
            self.sender_email
        )
    
    async def send_mail(self, request: MailRequest) -> DirectSendResponse:
        """
        메일 발송
        
        Args:
            request: 메일 발송 요청 정보
            
        Returns:
            DirectSendResponse: API 응답
        """
        if not self.is_configured:
            return DirectSendResponse(
                status=-1,
                msg="DirectSend is not configured"
            )
        
        # 수신자 데이터 포맷
        receivers_data = [
            {
                "name": r.name,
                "email": r.email,
                "note1": r.note1,
                "note2": r.note2,
                "note3": r.note3,
                "note4": r.note4,
                "note5": r.note5,
            }
            for r in request.receivers
        ]
        
        payload = {
            "username": self.username,
            "key": self.api_key,
            "sender": self.sender_email,
            "sender_name": request.sender_name or self.sender_name,
            "subject": request.subject,
            "body": request.body,
            "receiver": receivers_data,
            "body_tag": "Y",  # HTML 사용
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.BASE_URL,
                    json=payload,
                    timeout=30.0
                )
                result = response.json()
                
                return DirectSendResponse(
                    status=result.get("status", -1),
                    msg=result.get("msg", "Unknown error"),
                    data=result
                )
        except httpx.RequestError as e:
            return DirectSendResponse(
                status=-1,
                msg=f"Request failed: {str(e)}"
            )
        except Exception as e:
            return DirectSendResponse(
                status=-1,
                msg=f"Unexpected error: {str(e)}"
            )


class DirectSendSMSService:
    """DirectSend SMS 발송 서비스"""
    
    BASE_URL = "https://directsend.co.kr/index.php/api_v2/sms_change_word"
    
    def __init__(self):
        self.username = settings.DIRECTSEND_USERNAME
        self.api_key = settings.DIRECTSEND_API_KEY
        self.sender_phone = settings.DIRECTSEND_SENDER_PHONE
    
    @property
    def is_configured(self) -> bool:
        """DirectSend 설정이 완료되었는지 확인"""
        return bool(
            self.username and 
            self.api_key and 
            self.sender_phone
        )
    
    async def send_sms(self, request: SMSRequest) -> DirectSendResponse:
        """
        SMS 발송
        
        Args:
            request: SMS 발송 요청 정보
            
        Returns:
            DirectSendResponse: API 응답
        """
        if not self.is_configured:
            return DirectSendResponse(
                status=-1,
                msg="DirectSend SMS is not configured"
            )
        
        # 수신자 데이터 포맷
        receivers_data = [
            {
                "name": r.name,
                "mobile": r.mobile,
                "note1": r.note1,
                "note2": r.note2,
                "note3": r.note3,
                "note4": r.note4,
                "note5": r.note5,
            }
            for r in request.receivers
        ]
        
        payload = {
            "username": self.username,
            "key": self.api_key,
            "sender": self.sender_phone,
            "title": request.title,
            "message": request.message,
            "receiver": receivers_data,
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.BASE_URL,
                    json=payload,
                    timeout=30.0
                )
                result = response.json()
                
                return DirectSendResponse(
                    status=result.get("status", -1),
                    msg=result.get("msg", "Unknown error"),
                    data=result
                )
        except httpx.RequestError as e:
            return DirectSendResponse(
                status=-1,
                msg=f"Request failed: {str(e)}"
            )
        except Exception as e:
            return DirectSendResponse(
                status=-1,
                msg=f"Unexpected error: {str(e)}"
            )


# 싱글톤 인스턴스
mail_service = DirectSendMailService()
sms_service = DirectSendSMSService()

