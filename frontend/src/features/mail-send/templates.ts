import type { FormSurveyEmailParams } from "./types"

/**
 * 폼 설문조사 이메일 템플릿 생성
 */
export function getFormSurveyTemplate(params: FormSurveyEmailParams): { subject: string; body: string } {
  const {
    receiverName,
    formTitle,
    formDescription,
    formUrl,
    expiredAt,
    senderName = "관리자",
  } = params

  const subject = `[설문 요청] ${formTitle}`

  const body = `
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${formTitle}</title>
  <style>
    body {
      font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      line-height: 1.6;
      color: #333;
      margin: 0;
      padding: 0;
      background-color: #f5f5f5;
    }
    .container {
      max-width: 600px;
      margin: 0 auto;
      padding: 40px 20px;
    }
    .card {
      background: white;
      border-radius: 12px;
      padding: 32px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    }
    .header {
      text-align: center;
      margin-bottom: 24px;
    }
    .title {
      font-size: 24px;
      font-weight: 700;
      color: #1976d2;
      margin: 0 0 8px 0;
    }
    .description {
      color: #666;
      font-size: 14px;
      margin: 0;
    }
    .greeting {
      margin-bottom: 20px;
    }
    .content {
      background: #f8f9fa;
      border-radius: 8px;
      padding: 20px;
      margin: 20px 0;
    }
    .info-row {
      display: flex;
      margin-bottom: 8px;
    }
    .info-label {
      font-weight: 600;
      width: 80px;
      color: #666;
    }
    .info-value {
      flex: 1;
    }
    .button-container {
      text-align: center;
      margin: 32px 0;
    }
    .button {
      display: inline-block;
      background: #1976d2;
      color: white !important;
      text-decoration: none;
      padding: 14px 32px;
      border-radius: 8px;
      font-weight: 600;
      font-size: 16px;
    }
    .button:hover {
      background: #1565c0;
    }
    .footer {
      text-align: center;
      color: #999;
      font-size: 12px;
      margin-top: 24px;
      padding-top: 24px;
      border-top: 1px solid #eee;
    }
    .warning {
      background: #fff3e0;
      border-left: 4px solid #ff9800;
      padding: 12px 16px;
      border-radius: 4px;
      margin-top: 20px;
      font-size: 13px;
      color: #e65100;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <div class="header">
        <h1 class="title">${formTitle}</h1>
        ${formDescription ? `<p class="description">${formDescription}</p>` : ""}
      </div>
      
      <div class="greeting">
        <p>${receiverName ? `<strong>${receiverName}</strong>님, 안녕하세요.` : "안녕하세요."}</p>
        <p>아래 설문에 참여해 주시기 바랍니다.</p>
      </div>
      
      <div class="content">
        <div class="info-row">
          <span class="info-label">설문명</span>
          <span class="info-value">${formTitle}</span>
        </div>
        <div class="info-row">
          <span class="info-label">마감일</span>
          <span class="info-value">${new Date(expiredAt).toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' })}</span>
        </div>
      </div>
      
      <div class="button-container">
        <a href="${formUrl}" class="button" target="_blank">설문 참여하기</a>
      </div>
      
      <div class="warning">
        ⚠️ 마감일 이후에는 응답하실 수 없습니다. 마감일 전까지 응답을 수정할 수 있습니다.
      </div>
      
      <div class="footer">
        <p>본 메일은 발신 전용입니다.</p>
        <p>문의사항이 있으시면 담당자에게 연락해 주세요.</p>
        <p style="margin-top: 12px;">- ${senderName} 드림</p>
      </div>
    </div>
  </div>
</body>
</html>
`

  return { subject, body }
}

/**
 * 기본 이메일 템플릿 모음
 */
export const EmailTemplates = {
  formSurvey: getFormSurveyTemplate,
}

