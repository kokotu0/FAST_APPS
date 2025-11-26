"""
DirectSend 메일 API 라우트
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.api.deps import CurrentUser
from app.services.directsend import (
    mail_service,
    MailRequest,
    MailReceiver,
    DirectSendResponse,
)

router = APIRouter(prefix="/directsend/mail", tags=["directsend-mail"])


class SendMailRequest(BaseModel):
    """메일 발송 요청 스키마"""
    subject: str
    body: str
    receivers: list[dict]  # [{name, email, note1?, ...}]
    sender_name: str | None = None


class SendMailResponse(BaseModel):
    """메일 발송 응답 스키마"""
    success: bool
    status: int
    message: str
    data: dict | None = None


@router.post("/send", response_model=SendMailResponse)
async def send_mail(
    request: SendMailRequest,
    current_user: CurrentUser,
) -> SendMailResponse:
    """
    메일 발송
    
    - 로그인한 사용자만 사용 가능
    - DirectSend API를 통해 메일 발송
    """
    if not mail_service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DirectSend mail service is not configured",
        )
    
    # 수신자 변환
    try:
        receivers = [
            MailReceiver(
                name=r.get("name", ""),
                email=r.get("email", ""),
                note1=r.get("note1", ""),
                note2=r.get("note2", ""),
                note3=r.get("note3", ""),
                note4=r.get("note4", ""),
                note5=r.get("note5", ""),
            )
            for r in request.receivers
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid receiver format: {str(e)}",
        )
    
    mail_request = MailRequest(
        subject=request.subject,
        body=request.body,
        receivers=receivers,
        sender_name=request.sender_name,
    )
    
    response = await mail_service.send_mail(mail_request)
    
    return SendMailResponse(
        success=response.status == 0,
        status=response.status,
        message=response.msg,
        data=response.data,
    )


@router.get("/status")
async def get_mail_service_status(
    current_user: CurrentUser,
) -> dict:
    """
    메일 서비스 상태 확인
    """
    return {
        "configured": mail_service.is_configured,
        "service": "DirectSend Mail",
    }

