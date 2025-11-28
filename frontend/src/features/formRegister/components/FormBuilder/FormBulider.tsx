import { useEffect, useRef } from "react"
import { Box, Button, Paper, Typography } from "@mui/material"
import { Add as AddIcon } from "@mui/icons-material"
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core"
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable"
import { useFormBuilder } from "./useFormBuilder"
import { SortableSectionEditor } from "./components"
import type { FormBuilderProps } from "./types"

/**
 * FormBuilder 메인 컴포넌트
 * 
 * 구조:
 * - SortableSectionEditor[]: 섹션 목록 (드래그 가능)
 *   - SortableFieldEditor[]: 필드 목록 (드래그 가능)
 */
const FormBuilder = ({ 
  onChange,
  onSchemaChange,
  onUiSchemaChange,
  initialForm,
  selectedFieldId,
  onFieldSelect,
}: FormBuilderProps) => {
  const builder = useFormBuilder(initialForm)
  
  // 콜백을 ref로 관리하여 의존성 문제 방지
  const onChangeRef = useRef(onChange)
  const onSchemaChangeRef = useRef(onSchemaChange)
  const onUiSchemaChangeRef = useRef(onUiSchemaChange)
  
  onChangeRef.current = onChange
  onSchemaChangeRef.current = onSchemaChange
  onUiSchemaChangeRef.current = onUiSchemaChange

  // 스키마 변경 시 콜백 호출
  useEffect(() => {
    const schemas = builder.toSchemas()
    onChangeRef.current?.(schemas)
    onSchemaChangeRef.current?.(schemas.jsonSchema)
    onUiSchemaChangeRef.current?.(schemas.uiSchema)
  }, [builder.form])

  // 섹션 드래그 센서
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  // 섹션 드래그 종료 핸들러
  const handleSectionDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (over && active.id !== over.id) {
      builder.reorderSection(active.id as string, over.id as string)
    }
  }

  // 선택된 필드 찾기 (name 또는 id로)
  const findSelectedField = (fieldIdentifier: string): { sectionId: string; fieldId: string } | null => {
    for (const section of builder.form.sections) {
      // name으로 찾기
      const fieldByName = section.fields.find(f => f.name === fieldIdentifier)
      if (fieldByName) return { sectionId: section.id, fieldId: fieldByName.id }
      
      // id로 찾기
      const fieldById = section.fields.find(f => f.id === fieldIdentifier)
      if (fieldById) return { sectionId: section.id, fieldId: fieldById.id }
    }
    return null
  }

  // selectedFieldId에서 실제 field id 찾기
  const selectedInfo = selectedFieldId ? findSelectedField(selectedFieldId) : null
  const actualSelectedId = selectedInfo?.fieldId || null

  return (
    <Box>
      {/* 섹션 목록 */}
      {builder.form.sections.length === 0 ? (
        <Paper variant="outlined" sx={{ p: 4, textAlign: "center", mb: 2 }}>
          <Typography color="text.secondary" mb={2}>
            섹션이 없습니다. 섹션을 추가해주세요.
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => builder.addSection()}
          >
            섹션 추가
          </Button>
        </Paper>
      ) : (
        <>
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleSectionDragEnd}
          >
            <SortableContext
              items={builder.form.sections.map((s) => s.id)}
              strategy={verticalListSortingStrategy}
            >
              {builder.form.sections.map((section, index) => (
                <SortableSectionEditor
                  key={section.id}
                  section={section}
                  isFirst={index === 0}
                  isLast={index === builder.form.sections.length - 1}
                  selectedFieldId={actualSelectedId}
                  onFieldSelect={onFieldSelect}
                  onUpdate={builder.updateSection}
                  onRemove={builder.removeSection}
                  onMove={builder.moveSection}
                  onAddField={builder.addField}
                  onUpdateField={builder.updateField}
                  onRemoveField={builder.removeField}
                  onMoveField={builder.moveField}
                  onReorderField={builder.reorderField}
                />
              ))}
            </SortableContext>
          </DndContext>

          <Button
            variant="outlined"
            startIcon={<AddIcon />}
            onClick={() => builder.addSection()}
            fullWidth
          >
            섹션 추가
          </Button>
        </>
      )}
    </Box>
  )
}

export { FormBuilder }
