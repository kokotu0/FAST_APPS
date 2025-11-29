import { nanoid } from "nanoid"
import type {
  FormDefinition,
  SectionDefinition,
  FieldDefinition,
  FieldSchema,
  FieldUiSchema,
  SectionType,
  FieldSchemaType,
  FieldWidget,
  FieldFormat,
  ImageContent,
} from "./types"
import type { RJSFSchema, UiSchema } from "@rjsf/utils"

/**
 * JSONSchema + UISchema → FormDefinition 변환
 * 백엔드에서 가져온 스키마를 폼 빌더에서 사용할 수 있는 형태로 변환
 */
export function schemasToFormDefinition(
  jsonSchema: RJSFSchema,
  uiSchema: UiSchema
): FormDefinition {
  const formId = nanoid()
  const sections: SectionDefinition[] = []

  // ui:order 가져오기
  const uiOrder = (uiSchema["ui:order"] as string[]) || []
  const properties = (jsonSchema.properties || {}) as Record<string, unknown>

  // 순서대로 섹션 생성
  const sectionNames = uiOrder.length > 0 ? uiOrder : Object.keys(properties)

  for (const sectionName of sectionNames) {
    const sectionSchema = properties[sectionName] as Record<string, unknown>
    if (!sectionSchema) continue

    const sectionUi = (uiSchema[sectionName] || {}) as Record<string, unknown>
    const sectionOptions = (sectionUi["ui:options"] || {}) as Record<string, unknown>

    // 섹션 타입 결정
    const sectionType = determineSectionType(sectionOptions)
    
    const section = createSectionFromSchema(
      sectionName,
      sectionSchema,
      sectionUi,
      sectionType
    )
    
    sections.push(section)
  }

  return {
    id: formId,
    sections,
  }
}

/**
 * 섹션 타입 결정
 */
function determineSectionType(options: Record<string, unknown>): SectionType {
  if (options.sectionType === "image") return "image"
  if (options.sectionType === "description") return "description"
  return "fields"
}

/**
 * 스키마에서 섹션 생성
 */
function createSectionFromSchema(
  name: string,
  schema: Record<string, unknown>,
  ui: Record<string, unknown>,
  type: SectionType
): SectionDefinition {
  const options = (ui["ui:options"] || {}) as Record<string, unknown>
  
  const section: SectionDefinition = {
    id: nanoid(),
    name,
    title: (schema.title as string) || name,
    description: (schema.description as string) || "",
    type,
    fields: [],
    ui: {
      grid: (options.grid as number) || 1,
      backgroundColor: options.backgroundColor as string | undefined,
      headerImage: options.headerImage as string | undefined,
    },
  }

  // 타입별 처리
  if (type === "image") {
    const content: ImageContent = {}
    if (options.imageSrc) {
      // URL인지 base64인지 확인
      const src = options.imageSrc as string
      if (src.startsWith("data:")) {
        content.file = src
      } else {
        content.url = src
      }
      content.alt = (options.imageAlt as string) || ""
    }
    section.content = content
  } else if (type === "description") {
    section.description = (options.descriptionText as string) || ""
    section.title = (options.descriptionTitle as string) || section.title
  } else {
    // fields 타입: 필드 추출
    const fieldOrder = (ui["ui:order"] as string[]) || []
    const fieldProperties = (schema.properties || {}) as Record<string, unknown>
    const required = (schema.required || []) as string[]

    const fieldNames = fieldOrder.length > 0 ? fieldOrder : Object.keys(fieldProperties)

    for (const fieldName of fieldNames) {
      const fieldSchema = fieldProperties[fieldName] as Record<string, unknown>
      if (!fieldSchema) continue

      const fieldUi = (ui[fieldName] || {}) as Record<string, unknown>
      const isRequired = required.includes(fieldName)

      const field = createFieldFromSchema(fieldName, fieldSchema, fieldUi, isRequired)
      section.fields.push(field)
    }
  }

  return section
}

/**
 * 스키마에서 필드 생성
 */
function createFieldFromSchema(
  name: string,
  schema: Record<string, unknown>,
  ui: Record<string, unknown>,
  required: boolean
): FieldDefinition {
  const fieldSchema = extractFieldSchema(schema)
  const fieldUi = extractFieldUiSchema(ui)

  return {
    id: nanoid(),
    name,
    required,
    schema: fieldSchema,
    ui: fieldUi,
  }
}

/**
 * JSON Schema에서 FieldSchema 추출
 */
function extractFieldSchema(schema: Record<string, unknown>): FieldSchema {
  const type = (schema.type as FieldSchemaType) || "string"
  
  const fieldSchema: FieldSchema = {
    type,
    title: (schema.title as string) || "",
    description: schema.description as string | undefined,
    default: schema.default,
  }

  // string 관련
  if (type === "string") {
    if (schema.minLength !== undefined) fieldSchema.minLength = schema.minLength as number
    if (schema.maxLength !== undefined) fieldSchema.maxLength = schema.maxLength as number
    if (schema.pattern) fieldSchema.pattern = schema.pattern as string
    if (schema.format) fieldSchema.format = schema.format as FieldFormat
  }

  // number/integer 관련
  if (type === "number" || type === "integer") {
    if (schema.minimum !== undefined) fieldSchema.minimum = schema.minimum as number
    if (schema.maximum !== undefined) fieldSchema.maximum = schema.maximum as number
  }

  // enum 처리
  if (schema.enum) {
    fieldSchema.enum = schema.enum as (string | number)[]
  }

  // oneOf → enum + enumNames 변환
  if (schema.oneOf && Array.isArray(schema.oneOf)) {
    const oneOf = schema.oneOf as Array<{ const?: unknown; title?: string }>
    fieldSchema.enum = oneOf.map(item => item.const as string | number)
    fieldSchema.enumNames = oneOf.map(item => item.title || String(item.const))
  }

  // array 처리
  if (type === "array") {
    const items = schema.items as Record<string, unknown> | undefined
    if (items) {
      fieldSchema.items = {
        type: (items.type as FieldSchemaType) || "string",
        enum: items.enum as (string | number)[] | undefined,
      }
    }
    if (schema.uniqueItems) {
      fieldSchema.uniqueItems = true
    }
  }

  return fieldSchema
}

/**
 * UI Schema에서 FieldUiSchema 추출
 */
function extractFieldUiSchema(ui: Record<string, unknown>): FieldUiSchema {
  const fieldUi: FieldUiSchema = {}

  if (ui["ui:widget"]) {
    fieldUi.widget = ui["ui:widget"] as FieldWidget
  }

  if (ui["ui:placeholder"]) {
    fieldUi.placeholder = ui["ui:placeholder"] as string
  }

  if (ui["ui:disabled"]) {
    fieldUi.disabled = true
  }

  if (ui["ui:readonly"]) {
    fieldUi.readonly = true
  }

  if (ui["ui:autofocus"]) {
    fieldUi.autofocus = true
  }

  if (ui["ui:options"]) {
    fieldUi.options = ui["ui:options"] as Record<string, unknown>
  }

  if (ui["classNames"]) {
    fieldUi.classNames = ui["classNames"] as string
  }

  return fieldUi
}

export default schemasToFormDefinition

