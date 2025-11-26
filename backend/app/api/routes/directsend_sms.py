"""
DirectSend SMS API 라우트
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.services.directsend import (
    sms_service,
    SMSRequest,
    SMSReceiver,
    DirectSendResponse,
)

router = APIRouter(prefix="/directsend/sms", tags=["directsend-sms"])


class SendSMSRequest(BaseModel):
    """SMS 발송 요청 스키마"""
    title: str  # MMS/LMS 제목 (최대 40byte)
    message: str  # 메시지 내용 (최대 2000byte)
    receivers: list[dict]  # [{name, mobile, note1?, ...}]


class SendSMSResponse(BaseModel):
    """SMS 발송 응답 스키마"""
    success: bool
    status: int
    message: str
    data: dict | None = None


@router.post("/send", response_model=SendSMSResponse)
async def send_sms(
    request: SendSMSRequest,
    current_user: CurrentUser,
) -> SendSMSResponse:
    """
    SMS 발송
    
    - 로그인한 사용자만 사용 가능
    - DirectSend API를 통해 SMS 발송
    """
    if not sms_service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DirectSend SMS service is not configured",
        )
    
    # 수신자 변환
    try:
        receivers = [
            SMSReceiver(
                name=r.get("name", ""),
                mobile=r.get("mobile", ""),
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
    
    sms_request = SMSRequest(
        title=request.title,
        message=request.message,
        receivers=receivers,
    )
    
    response = await sms_service.send_sms(sms_request)
    
    return SendSMSResponse(
        success=response.status == 0,
        status=response.status,
        message=response.msg,
        data=response.data,
    )


@router.get("/status")
async def get_sms_service_status(
    current_user: CurrentUser,
) -> dict:
    """
    SMS 서비스 상태 확인
    """
    return {
        "configured": sms_service.is_configured,
        "service": "DirectSend SMS",
    }

