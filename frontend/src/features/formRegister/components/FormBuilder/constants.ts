import type { FieldSchemaType, FieldWidget, FieldFormat } from "./types"

/**
 * 사용자 친화적 필드 타입
 */
export interface UserFieldType {
  value: string
  label: string
  schemaType: FieldSchemaType
  format?: FieldFormat
  widget?: FieldWidget
  needsEnum?: boolean
  needsFormat?: boolean
  description?: string
}

export const USER_FIELD_TYPES: UserFieldType[] = [
  { 
    value: "text", 
    label: "텍스트", 
    schemaType: "string", 
    needsFormat: true,
    description: "일반 텍스트 입력",
  },
  { 
    value: "number", 
    label: "숫자", 
    schemaType: "number",
    description: "소수점 포함 숫자",
  },
  { 
    value: "select", 
    label: "선택", 
    schemaType: "string", 
    widget: "select", 
    needsEnum: true,
    description: "드롭다운 또는 라디오",
  },
  { 
    value: "multiselect", 
    label: "다중 선택", 
    schemaType: "array", 
    widget: "checkboxes", 
    needsEnum: true,
    description: "체크박스 그룹",
  },
  { 
    value: "checkbox", 
    label: "체크박스", 
    schemaType: "boolean", 
    widget: "checkbox",
    description: "예/아니오",
  },
  { 
    value: "file", 
    label: "파일", 
    schemaType: "string", 
    format: "data-url",
    description: "파일 업로드",
  },
]

/**
 * 텍스트 포맷 옵션
 */
export interface TextFormatOption {
  value: string
  label: string
  format?: FieldFormat
  widget?: FieldWidget
  pattern?: string
  placeholder?: string
}

export const TEXT_FORMAT_OPTIONS: TextFormatOption[] = [
  { value: "default", label: "일반" },
  { value: "textarea", label: "여러 줄", widget: "textarea" },
  { value: "email", label: "이메일", format: "email", placeholder: "example@email.com" },
  { value: "uri", label: "URL", format: "uri", placeholder: "https://" },
  { value: "date", label: "날짜", format: "date" },
  { value: "datetime", label: "날짜+시간", format: "date-time" },
  { value: "phone", label: "핸드폰 번호", widget: "phone" },
  { value: "password", label: "비밀번호", format: "password" },
]

/**
 * 선택 타입 표시 방식
 */
export const SELECT_DISPLAY_OPTIONS: { value: FieldWidget; label: string }[] = [
  { value: "select", label: "드롭다운" },
  { value: "radio", label: "라디오 버튼" },
]

export const MULTISELECT_DISPLAY_OPTIONS: { value: FieldWidget; label: string }[] = [
  { value: "checkboxes", label: "체크박스 그룹" },
  { value: "select", label: "다중 선택 드롭다운" },
]

/**
 * 숫자 형식 옵션
 */
export const NUMBER_FORMAT_OPTIONS: { value: string; label: string; schemaType: FieldSchemaType }[] = [
  { value: "number", label: "소수점 허용", schemaType: "number" },
  { value: "integer", label: "정수만", schemaType: "integer" },
]

/**
 * 숫자 위젯 옵션
 */
export const NUMBER_WIDGET_OPTIONS: { value: string; label: string; widget?: FieldWidget }[] = [
  { value: "default", label: "입력 필드" },
  { value: "range", label: "슬라이더" },
  { value: "updown", label: "증감 버튼" },
]

/**
 * 섹션 배경색 옵션
 */
export const SECTION_BG_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "없음" },
  { value: "#f5f5f5", label: "회색" },
  { value: "#e3f2fd", label: "파랑" },
  { value: "#e8f5e9", label: "녹색" },
  { value: "#fff3e0", label: "주황" },
  { value: "#fce4ec", label: "분홍" },
  { value: "#f3e5f5", label: "보라" },
  { value: "#fffde7", label: "노랑" },
]

// ============ 레거시 호환 ============

import type { FieldTypeOption } from "./types"

/** @deprecated USER_FIELD_TYPES 사용 */
export const FIELD_TYPE_OPTIONS: FieldTypeOption[] = []

/** @deprecated */
export const SELECT_UI_OPTIONS = SELECT_DISPLAY_OPTIONS

/** @deprecated */
export const MULTISELECT_UI_OPTIONS = MULTISELECT_DISPLAY_OPTIONS
