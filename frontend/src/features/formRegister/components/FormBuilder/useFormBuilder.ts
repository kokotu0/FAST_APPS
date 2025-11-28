import { useState, useCallback } from "react"
import { nanoid } from "nanoid"
import type {
  FormDefinition,
  SectionDefinition,
  FieldDefinition,
  FormSchemas,
  UseFormBuilderReturn,
} from "./types"

// ============ 기본값 생성 ============

const createDefaultSection = (partial?: Partial<SectionDefinition>): SectionDefinition => ({
  id: nanoid(),
  name: nanoid(),  // uuid로 자동 생성
  title: "새 섹션",
  description: "",
  type: "fields",  // 기본값: 필드 목록
  fields: [],
  ui: { grid: 1 },
  ...partial,
})

const createDefaultField = (partial?: Partial<FieldDefinition>): FieldDefinition => ({
  id: nanoid(),
  name: nanoid(),  // uuid로 자동 생성
  required: false,
  schema: {
    type: "string",
    title: "새 필드",
  },
  ui: {},
  ...partial,
})

const createDefaultForm = (): FormDefinition => ({
  id: nanoid(),
  sections: [],
})

// ============ 변환 헬퍼 ============

function buildFieldSchema(field: FieldDefinition): Record<string, unknown> {
  const schema: Record<string, unknown> = {
    type: field.schema.type,
    title: field.schema.title,
  }

  if (field.schema.description) {
    schema.description = field.schema.description
  }

  if (field.schema.default !== undefined) {
    schema.default = field.schema.default
  }

  // string 관련
  if (field.schema.type === "string") {
    if (field.schema.minLength) schema.minLength = field.schema.minLength
    if (field.schema.maxLength) schema.maxLength = field.schema.maxLength
    if (field.schema.pattern) schema.pattern = field.schema.pattern
    if (field.schema.format) schema.format = field.schema.format
  }

  // number/integer 관련
  if (field.schema.type === "number" || field.schema.type === "integer") {
    if (field.schema.minimum !== undefined) schema.minimum = field.schema.minimum
    if (field.schema.maximum !== undefined) schema.maximum = field.schema.maximum
  }

  // enum (select, radio)
  if (field.schema.enum && field.schema.enum.length > 0) {
    if (field.schema.enumNames && field.schema.enumNames.length === field.schema.enum.length) {
      // oneOf 형태로 변환 (표시 이름 포함)
      schema.oneOf = field.schema.enum.map((value, i) => ({
        const: value,
        title: field.schema.enumNames![i],
      }))
    } else {
      schema.enum = field.schema.enum
    }
  }

  // array (checkboxes, multi-select)
  if (field.schema.type === "array") {
    const items = field.schema.items || { type: "string" }
    // items.enum이 있고 비어있지 않을 때만 설정
    if (items.enum && items.enum.length > 0) {
      schema.items = { type: items.type || "string", enum: items.enum }
    } else {
      schema.items = { type: items.type || "string" }
    }
    if (field.schema.uniqueItems) {
      schema.uniqueItems = true
    }
  }

  return schema
}

function buildFieldUiSchema(field: FieldDefinition): Record<string, unknown> {
  const ui: Record<string, unknown> = {}

  if (field.ui.widget) {
    ui["ui:widget"] = field.ui.widget
  }

  if (field.ui.placeholder) {
    ui["ui:placeholder"] = field.ui.placeholder
  }

  if (field.ui.disabled) {
    ui["ui:disabled"] = true
  }

  if (field.ui.readonly) {
    ui["ui:readonly"] = true
  }

  if (field.ui.autofocus) {
    ui["ui:autofocus"] = true
  }

  if (field.ui.options && Object.keys(field.ui.options).length > 0) {
    ui["ui:options"] = field.ui.options
  }

  if (field.ui.classNames) {
    ui["classNames"] = field.ui.classNames
  }

  return ui
}

// ============ Hook ============

export const useFormBuilder = (initialForm?: FormDefinition): UseFormBuilderReturn => {
  const [form, setForm] = useState<FormDefinition>(initialForm ?? createDefaultForm())

  // ============ Section CRUD ============

  const addSection = useCallback((partial?: Partial<SectionDefinition>) => {
    const newSection = createDefaultSection(partial)
    setForm((prev) => ({
      ...prev,
      sections: [...prev.sections, newSection],
    }))
    return newSection
  }, [])

  const updateSection = useCallback((sectionId: string, updates: Partial<SectionDefinition>) => {
    setForm((prev) => ({
      ...prev,
      sections: prev.sections.map((section) => {
        if (section.id !== sectionId) return section
        
        // 타입 변경 시 처리
        if (updates.type && updates.type !== section.type) {
          // fields → image/description: 필드 초기화
          if (updates.type !== "fields") {
            return { ...section, ...updates, fields: [] }
          }
          // image/description → fields: 컨텐츠 초기화
          return { ...section, ...updates, content: undefined }
        }
        
        return { ...section, ...updates }
      }),
    }))
  }, [])

  const removeSection = useCallback((sectionId: string) => {
    setForm((prev) => ({
      ...prev,
      sections: prev.sections.filter((section) => section.id !== sectionId),
    }))
  }, [])

  const moveSection = useCallback((sectionId: string, direction: "up" | "down") => {
    setForm((prev) => {
      const index = prev.sections.findIndex((s) => s.id === sectionId)
      if (index === -1) return prev

      const newIndex = direction === "up" ? index - 1 : index + 1
      if (newIndex < 0 || newIndex >= prev.sections.length) return prev

      const newSections = [...prev.sections]
      const temp = newSections[index]
      newSections[index] = newSections[newIndex]
      newSections[newIndex] = temp

      return { ...prev, sections: newSections }
    })
  }, [])

  // ============ Field CRUD ============

  const addField = useCallback((sectionId: string, partial?: Partial<FieldDefinition>) => {
    const newField = createDefaultField(partial)
    setForm((prev) => ({
      ...prev,
      sections: prev.sections.map((section) =>
        section.id === sectionId
          ? { ...section, fields: [...section.fields, newField] }
          : section
      ),
    }))
    return newField
  }, [])

  const updateField = useCallback(
    (sectionId: string, fieldId: string, updates: Partial<FieldDefinition>) => {
      setForm((prev) => ({
        ...prev,
        sections: prev.sections.map((section) =>
          section.id === sectionId
            ? {
                ...section,
                fields: section.fields.map((field) =>
                  field.id === fieldId ? { ...field, ...updates } : field
                ),
              }
            : section
        ),
      }))
    },
    []
  )

  const removeField = useCallback((sectionId: string, fieldId: string) => {
    setForm((prev) => ({
      ...prev,
      sections: prev.sections.map((section) =>
        section.id === sectionId
          ? { ...section, fields: section.fields.filter((f) => f.id !== fieldId) }
          : section
      ),
    }))
  }, [])

  const moveField = useCallback((sectionId: string, fieldId: string, direction: "up" | "down") => {
    setForm((prev) => ({
      ...prev,
      sections: prev.sections.map((section) => {
        if (section.id !== sectionId) return section

        const index = section.fields.findIndex((f) => f.id === fieldId)
        if (index === -1) return section

        const newIndex = direction === "up" ? index - 1 : index + 1
        if (newIndex < 0 || newIndex >= section.fields.length) return section

        const newFields = [...section.fields]
        const temp = newFields[index]
        newFields[index] = newFields[newIndex]
        newFields[newIndex] = temp

        return { ...section, fields: newFields }
      }),
    }))
  }, [])

  // ============ Drag & Drop Reorder ============

  const reorderSection = useCallback((activeId: string, overId: string) => {
    setForm((prev) => {
      const oldIndex = prev.sections.findIndex((s) => s.id === activeId)
      const newIndex = prev.sections.findIndex((s) => s.id === overId)
      if (oldIndex === -1 || newIndex === -1 || oldIndex === newIndex) return prev

      const newSections = [...prev.sections]
      const [removed] = newSections.splice(oldIndex, 1)
      newSections.splice(newIndex, 0, removed)

      return { ...prev, sections: newSections }
    })
  }, [])

  const reorderField = useCallback((sectionId: string, activeId: string, overId: string) => {
    setForm((prev) => ({
      ...prev,
      sections: prev.sections.map((section) => {
        if (section.id !== sectionId) return section

        const oldIndex = section.fields.findIndex((f) => f.id === activeId)
        const newIndex = section.fields.findIndex((f) => f.id === overId)
        if (oldIndex === -1 || newIndex === -1 || oldIndex === newIndex) return section

        const newFields = [...section.fields]
        const [removed] = newFields.splice(oldIndex, 1)
        newFields.splice(newIndex, 0, removed)

        return { ...section, fields: newFields }
      }),
    }))
  }, [])

  // ============ 유틸 ============

  const getSection = useCallback(
    (sectionId: string) => form.sections.find((s) => s.id === sectionId),
    [form.sections]
  )

  const getField = useCallback(
    (sectionId: string, fieldId: string) => {
      const section = form.sections.find((s) => s.id === sectionId)
      return section?.fields.find((f) => f.id === fieldId)
    },
    [form.sections]
  )

  const reset = useCallback(() => {
    setForm(createDefaultForm())
  }, [])

  const loadForm = useCallback((newForm: FormDefinition) => {
    setForm(newForm)
  }, [])

  // ============ JSON Schema 변환 ============

  const toSchemas = useCallback((): FormSchemas => {
    const properties: Record<string, object> = {}
    const uiSchema: FormSchemas["uiSchema"] = {
      "ui:order": [] as string[],
    }

    for (const section of form.sections) {
      const sectionOptions: Record<string, unknown> = {}
      
      // 공통 UI 옵션
      if (section.ui.grid && section.ui.grid > 1) {
        sectionOptions.grid = section.ui.grid
      }
      if (section.ui.backgroundColor) {
        sectionOptions.backgroundColor = section.ui.backgroundColor
      }

      // 섹션 타입별 처리
      if (section.type === "image") {
        // 이미지 섹션 (이미지 유무와 관계없이 항상 sectionType 설정)
        const imageContent = section.content as { url?: string; file?: string; alt?: string } | undefined
        const imageSrc = imageContent?.url || imageContent?.file
        
        sectionOptions.sectionType = "image"
        if (imageSrc) {
          sectionOptions.imageSrc = imageSrc
          sectionOptions.imageAlt = imageContent?.alt || ""
        }

        // 빈 object로 표시 (필드 없음)
        properties[section.name] = {
          type: "object",
          properties: {},
        }

        uiSchema[section.name] = {
          "ui:options": sectionOptions,
        }
      } else if (section.type === "description") {
        // 설명 섹션 (설명 유무와 관계없이 항상 sectionType 설정)
        sectionOptions.sectionType = "description"
        sectionOptions.descriptionText = section.description || ""
        sectionOptions.descriptionTitle = section.title || ""

        // 빈 object로 표시 (필드 없음)
        properties[section.name] = {
          type: "object",
          properties: {},
        }

        uiSchema[section.name] = {
          "ui:options": sectionOptions,
        }
      } else {
        // 필드 섹션 (기본)
        const sectionProperties: Record<string, object> = {}
        const sectionRequired: string[] = []
        const sectionUiSchema: Record<string, unknown> = {}
        const fieldOrder: string[] = []

        for (const field of section.fields) {
          // Field -> JSON Schema
          const fieldSchema = buildFieldSchema(field)
          sectionProperties[field.name] = fieldSchema

          if (field.required) {
            sectionRequired.push(field.name)
          }

          // Field -> UI Schema
          const fieldUi = buildFieldUiSchema(field)
          if (Object.keys(fieldUi).length > 0) {
            sectionUiSchema[field.name] = fieldUi
          }

          fieldOrder.push(field.name)
        }

        // Section -> JSON Schema
        properties[section.name] = {
          type: "object",
          title: section.title,
          description: section.description,
          properties: sectionProperties,
          required: sectionRequired.length > 0 ? sectionRequired : undefined,
        }

        // 헤더 이미지 (필드 섹션만)
        if (section.ui.headerImage) {
          sectionOptions.headerImage = section.ui.headerImage
        }

        uiSchema[section.name] = {
          ...sectionUiSchema,
          "ui:order": fieldOrder,
          ...(Object.keys(sectionOptions).length > 0 && {
            "ui:options": sectionOptions,
          }),
        }
      }

      ;(uiSchema["ui:order"] as string[]).push(section.name)
    }

    const jsonSchema: FormSchemas["jsonSchema"] = {
      type: "object",
      properties,
      required: [],
    }

    return { jsonSchema, uiSchema }
  }, [form])

  return {
    form,
    // Section
    addSection,
    updateSection,
    removeSection,
    moveSection,
    reorderSection,
    // Field
    addField,
    updateField,
    removeField,
    moveField,
    reorderField,
    // 변환
    toSchemas,
    // 유틸
    getSection,
    getField,
    reset,
    loadForm,
  }
}

export default useFormBuilder
