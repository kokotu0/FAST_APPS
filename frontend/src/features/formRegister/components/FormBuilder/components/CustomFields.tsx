/**
 * 커스텀 필드 정의
 * 
 * RJSF에서 필드(Field)는 위젯(Widget)과 다릅니다:
 * - Widget: 입력 컴포넌트 자체 (텍스트 입력, 체크박스 등)
 * - Field: 라벨, 설명, 에러 메시지를 포함한 전체 필드 래퍼
 * 
 * 현재는 필요한 커스텀 필드가 없으므로 빈 상태로 유지합니다.
 * 필요시 여기에 추가하세요.
 */

import type { FieldProps } from "@rjsf/utils"

// 예시: 이미지 미리보기 필드
// export const ImagePreviewField = (props: FieldProps) => {
//   const { formData } = props
//   return (
//     <div>
//       {formData && <img src={formData} alt="preview" />}
//       {/* 기본 위젯 렌더링 */}
//     </div>
//   )
// }

export const customFields: Record<string, React.ComponentType<FieldProps>> = {
  // 필요시 추가
}

export default customFields

