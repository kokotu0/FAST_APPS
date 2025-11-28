import type { RJSFSchema } from "@rjsf/utils"

/**
 * FormBuilder 타입 정의
 * 
 * 구조:
 * FormDefinition
 *   └── SectionDefinition[] (1:N)
 *         └── FieldDefinition[] (1:N)
 * 
 * Section 하위에 Section 없음 (중첩 X)
 * jsonSchema + uiSchema를 동시에 정의
 */

// ============ Field 관련 ============

/** 필드 스키마 타입 */
export type FieldSchemaType = 
  | "string" 
  | "number" 
  | "integer" 
  | "boolean" 
  | "array"

/** 필드 포맷 (string 타입용) */
export type FieldFormat = 
  | "date" 
  | "date-time" 
  | "email" 
  | "uri" 
  | "password"
  | "data-url"

/** 필드 위젯 타입 */
export type FieldWidget = 
  | "text"
  | "textarea"
  | "select"
  | "radio"
  | "checkboxes"
  | "checkbox"
  | "date"
  | "datetime"
  | "password"
  | "hidden"
  | "phone"    // 커스텀: 핸드폰 번호
  | "updown"   // 커스텀: 증감 버튼
  | "range"    // 슬라이더

/** 필드의 JSON Schema 부분 */
export interface FieldSchema {
  type: FieldSchemaType
  title: string
  description?: string
  default?: unknown
  // string
  minLength?: number
  maxLength?: number
  pattern?: string
  format?: FieldFormat
  // number/integer
  minimum?: number
  maximum?: number
  // enum (select, radio, checkboxes)
  enum?: (string | number)[]
  enumNames?: string[]  // 표시용 이름 (oneOf로 변환됨)
  // array
  items?: {
    type: FieldSchemaType
    enum?: (string | number)[]
    enumNames?: string[]
  }
  uniqueItems?: boolean
}

/** 필드의 UI Schema 부분 */
export interface FieldUiSchema {
  widget?: FieldWidget
  placeholder?: string
  disabled?: boolean
  readonly?: boolean
  autofocus?: boolean
  options?: Record<string, unknown>
  classNames?: string
}

/** 필드 정의 (Schema + UI 통합) */
export interface FieldDefinition {
  id: string
  name: string  // 필드명 (영문, JSON key)
  required: boolean
  schema: FieldSchema
  ui: FieldUiSchema
}

// ============ Section 관련 ============

/** 섹션 타입 */
export type SectionType = 
  | "fields"      // 필드 목록 (기본)
  | "image"       // 이미지
  | "description" // 설명 텍스트
  | "file"        // 파일 다운로드

/** 이미지 컨텐츠 */
export interface ImageContent {
  url?: string           // URL 입력
  file?: string          // Base64 데이터 (로컬 업로드)
  alt?: string           // 대체 텍스트
  width?: number | string
  height?: number | string
}

/** 설명 컨텐츠 */
export interface DescriptionContent {
  text: string           // 마크다운 또는 HTML
  format?: "text" | "markdown" | "html"
}

/** 파일 컨텐츠 */
export interface FileContent {
  url?: string
  file?: string          // Base64 데이터
  fileName?: string
  fileSize?: number
}

/** 섹션 컨텐츠 (타입별) */
export type SectionContent = ImageContent | DescriptionContent | FileContent

/** 섹션 UI 옵션 */
export interface SectionUiSchema {
  /** 그리드 열 수 (1 = 세로, 2 = 2열, 3 = 3열...) */
  grid?: number
  /** 접기 가능 여부 */
  collapsible?: boolean
  /** 기본 접힘 상태 */
  collapsed?: boolean
  classNames?: string
  /** 배경색 */
  backgroundColor?: string
  /** 헤더 이미지 URL */
  headerImage?: string
  /** 패딩 */
  padding?: number
}

/** 섹션 정의 */
export interface SectionDefinition {
  id: string
  name: string  // 섹션명 (영문, JSON key)
  title: string
  description?: string
  type: SectionType       // 섹션 타입
  fields: FieldDefinition[] // type이 "fields"일 때만 사용
  content?: SectionContent  // type이 "image", "description", "file"일 때 사용
  ui: SectionUiSchema
}

// ============ Form 전체 ============

/** 폼 정의 (최상위) */
export interface FormDefinition {
  id: string
  sections: SectionDefinition[]
}

// ============ 변환 결과 ============

/** JSON Schema (rjsf 호환) */
export interface JsonSchema {
  $id?: string
  type: "object"
  title?: string
  description?: string
  properties: Record<string, unknown>
  required?: string[]
}

/** UI Schema (rjsf 호환) */
export interface UiSchema {
  "ui:order"?: string[]
  [key: string]: unknown
}

/** 최종 변환 결과 */
export interface FormSchemas {
  jsonSchema: RJSFSchema
  uiSchema: UiSchema
}

// ============ Hook 반환 타입 ============

export interface UseFormBuilderReturn {
  /** 현재 폼 정의 */
  form: FormDefinition
  
  // Section CRUD
  addSection: (section?: Partial<SectionDefinition>) => SectionDefinition
  updateSection: (sectionId: string, updates: Partial<SectionDefinition>) => void
  removeSection: (sectionId: string) => void
  moveSection: (sectionId: string, direction: "up" | "down") => void
  reorderSection: (activeId: string, overId: string) => void
  
  // Field CRUD
  addField: (sectionId: string, field?: Partial<FieldDefinition>) => FieldDefinition
  updateField: (sectionId: string, fieldId: string, updates: Partial<FieldDefinition>) => void
  removeField: (sectionId: string, fieldId: string) => void
  moveField: (sectionId: string, fieldId: string, direction: "up" | "down") => void
  reorderField: (sectionId: string, activeId: string, overId: string) => void
  
  // 변환
  toSchemas: () => FormSchemas
  
  // 유틸
  getSection: (sectionId: string) => SectionDefinition | undefined
  getField: (sectionId: string, fieldId: string) => FieldDefinition | undefined
  reset: () => void
  loadForm: (form: FormDefinition) => void
}

// ============ Component Props ============

export interface FormBuilderProps {
  /** JSON Schema 변경 콜백 */
  onSchemaChange?: (schema: RJSFSchema) => void
  /** UI Schema 변경 콜백 */
  onUiSchemaChange?: (uiSchema: UiSchema) => void
  /** 전체 스키마 변경 콜백 (deprecated, onSchemaChange/onUiSchemaChange 사용 권장) */
  onChange?: (schemas: FormSchemas) => void
  /** 초기 폼 데이터 */
  initialForm?: FormDefinition
  /** 선택된 필드 ID (폼 미리보기에서 클릭 시) */
  selectedFieldId?: string | null
  /** 필드 선택 콜백 */
  onFieldSelect?: (fieldId: string | null) => void
}

/** 필드 타입 옵션 (UI 선택용) */
export interface FieldTypeOption {
  value: string
  label: string
  schemaType: FieldSchemaType
  format?: FieldFormat
  widget?: FieldWidget
  isArray?: boolean
}
