import { useState } from "react"
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
import {
  Box,
  Button,
  IconButton,
  TextField,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Stack,
  Divider,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
} from "@mui/material"
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  KeyboardArrowUp as UpIcon,
  KeyboardArrowDown as DownIcon,
  ExpandMore as ExpandMoreIcon,
  DragIndicator as DragIcon,
  Image as ImageIcon,
  Settings as SettingsIcon,
} from "@mui/icons-material"
import type { SectionDefinition, FieldDefinition, SectionType, ImageContent } from "../types"
import { SortableFieldEditor } from "./SortableFieldEditor"
import { ImageModal } from "./ImageModal"

// 섹션 타입 옵션
const SECTION_TYPE_OPTIONS: { value: SectionType; label: string }[] = [
  { value: "fields", label: "📋 필드" },
  { value: "image", label: "🖼️ 이미지" },
  { value: "description", label: "📝 설명" },
]

export interface SectionEditorProps {
  section: SectionDefinition
  isFirst: boolean
  isLast: boolean
  selectedFieldId?: string | null
  onFieldSelect?: (fieldId: string | null) => void
  onUpdate: (sectionId: string, updates: Partial<SectionDefinition>) => void
  onRemove: (sectionId: string) => void
  onMove: (sectionId: string, direction: "up" | "down") => void
  onAddField: (sectionId: string) => void
  onUpdateField: (sectionId: string, fieldId: string, updates: Partial<FieldDefinition>) => void
  onRemoveField: (sectionId: string, fieldId: string) => void
  onMoveField: (sectionId: string, fieldId: string, direction: "up" | "down") => void
  onReorderField: (sectionId: string, activeId: string, overId: string) => void
  dragHandleProps?: Record<string, unknown>
}

export const SectionEditor = ({
  section,
  isFirst,
  isLast,
  selectedFieldId,
  onFieldSelect,
  onUpdate,
  onRemove,
  onMove,
  onAddField,
  onUpdateField,
  onRemoveField,
  onMoveField,
  onReorderField,
  dragHandleProps,
}: SectionEditorProps) => {
  const [imageModalOpen, setImageModalOpen] = useState(false)

  // 필드 드래그 센서
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  const handleFieldDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (over && active.id !== over.id) {
      onReorderField(section.id, active.id as string, over.id as string)
    }
  }

  // 섹션 타입별 라벨
  const typeLabel = SECTION_TYPE_OPTIONS.find(t => t.value === section.type)?.label || "📋 필드"

  // 이미지 컨텐츠
  const imageContent = section.content as ImageContent | undefined
  const imageSrc = imageContent?.url || imageContent?.file

  return (
    <>
      <Accordion defaultExpanded sx={{ mb: 1 }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Stack direction="row" spacing={1} alignItems="center" flex={1} mr={1}>
            {/* 드래그 핸들 */}
            <Box
              {...dragHandleProps}
              sx={{ cursor: "grab", display: "flex" }}
              onClick={(e) => e.stopPropagation()}
            >
              <DragIcon sx={{ color: "text.secondary" }} />
            </Box>
            <Chip label={typeLabel} size="small" variant="outlined" />
            <Typography fontWeight={500}>{section.title}</Typography>
            {section.type === "fields" && (
              <Chip label={`${section.fields.length}개`} size="small" />
            )}
            <Box flex={1} />
            
            {/* 위/아래 버튼 */}
            <IconButton
              component="span"
              size="small"
              disabled={isFirst}
              onClick={(e) => {
                e.stopPropagation()
                onMove(section.id, "up")
              }}
            >
              <UpIcon fontSize="small" />
            </IconButton>
            <IconButton
              component="span"
              size="small"
              disabled={isLast}
              onClick={(e) => {
                e.stopPropagation()
                onMove(section.id, "down")
              }}
            >
              <DownIcon fontSize="small" />
            </IconButton>
            <IconButton
              component="span"
              size="small"
              color="error"
              onClick={(e) => {
                e.stopPropagation()
                onRemove(section.id)
              }}
            >
              <DeleteIcon fontSize="small" />
            </IconButton>
          </Stack>
        </AccordionSummary>

        <AccordionDetails>
          {/* 섹션명 (hidden) */}
          <input type="hidden" value={section.name} />
          
          {/* 섹션 기본 설정 */}
          <Stack direction="row" spacing={1} mb={2} flexWrap="wrap">
            <FormControl size="small" sx={{ minWidth: 100 }}>
              <InputLabel>타입</InputLabel>
              <Select
                value={section.type}
                label="타입"
                onChange={(e) => onUpdate(section.id, { type: e.target.value as SectionType })}
              >
                {SECTION_TYPE_OPTIONS.map(opt => (
                  <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                ))}
              </Select>
            </FormControl>
            
            {/* 필드/설명 섹션만 제목 표시 */}
            {section.type !== "image" && (
              <TextField
                key={`title-${section.id}`}
                size="small"
                label="제목"
                defaultValue={section.title}
                onBlur={(e) => onUpdate(section.id, { title: e.target.value })}
                sx={{ flex: 1, minWidth: 150 }}
              />
            )}
            
            {/* 필드 섹션: 그리드 */}
            {section.type === "fields" && (
              <FormControl size="small" sx={{ minWidth: 80 }}>
                <InputLabel>그리드</InputLabel>
                <Select
                  value={section.ui.grid || 1}
                  label="그리드"
                  onChange={(e) =>
                    onUpdate(section.id, {
                      ui: { ...section.ui, grid: Number(e.target.value) },
                    })
                  }
                >
                  <MenuItem value={1}>1열</MenuItem>
                  <MenuItem value={2}>2열</MenuItem>
                  <MenuItem value={3}>3열</MenuItem>
                  <MenuItem value={4}>4열</MenuItem>
                </Select>
              </FormControl>
            )}
            
            {/* 이미지 섹션: 크기 (그리드) */}
            {section.type === "image" && (
              <FormControl size="small" sx={{ minWidth: 100 }}>
                <InputLabel>크기</InputLabel>
                <Select
                  value={section.ui.grid || 1}
                  label="크기"
                  onChange={(e) =>
                    onUpdate(section.id, {
                      ui: { ...section.ui, grid: Number(e.target.value) },
                    })
                  }
                >
                  <MenuItem value={1}>전체</MenuItem>
                  <MenuItem value={2}>1/2</MenuItem>
                  <MenuItem value={3}>1/3</MenuItem>
                  <MenuItem value={4}>1/4</MenuItem>
                </Select>
              </FormControl>
            )}
            
            <FormControl size="small" sx={{ minWidth: 80 }}>
              <InputLabel>배경</InputLabel>
              <Select
                value={section.ui.backgroundColor || ""}
                label="배경"
                onChange={(e) =>
                  onUpdate(section.id, {
                    ui: { ...section.ui, backgroundColor: e.target.value || undefined },
                  })
                }
              >
                <MenuItem value="">없음</MenuItem>
                <MenuItem value="#f5f5f5">회색</MenuItem>
                <MenuItem value="#e3f2fd">파랑</MenuItem>
                <MenuItem value="#e8f5e9">녹색</MenuItem>
                <MenuItem value="#fff3e0">주황</MenuItem>
                <MenuItem value="#fce4ec">분홍</MenuItem>
              </Select>
            </FormControl>
          </Stack>

          {/* 필드 섹션: 간단한 설명 */}
          {section.type === "fields" && (
            <TextField
              key={`desc-${section.id}`}
              size="small"
              label="섹션 설명"
              fullWidth
              defaultValue={section.description || ""}
              onBlur={(e) => onUpdate(section.id, { description: e.target.value })}
              sx={{ mb: 2 }}
            />
          )}

          {/* 설명 섹션: 멀티라인 설명 */}
          {section.type === "description" && (
            <TextField
              key={`desc-ml-${section.id}`}
              size="small"
              label="설명 내용"
              fullWidth
              multiline
              minRows={4}
              defaultValue={section.description || ""}
              onBlur={(e) => onUpdate(section.id, { description: e.target.value })}
              sx={{ mb: 2 }}
              placeholder="설명을 입력하세요..."
            />
          )}

          {section.type !== "image" && <Divider sx={{ mb: 2 }} />}

          {/* 섹션 타입별 컨텐츠 */}
          {section.type === "fields" && (
            <>
              {/* 필드 목록 */}
              <Box 
                sx={{ 
                  maxHeight: 600, 
                  overflow: "auto", 
                  mb: 1,
                  bgcolor: "grey.50",
                  borderRadius: 1,
                  p: section.fields.length > 0 ? 1 : 0,
                }}
              >
                {section.fields.length === 0 ? (
                  <Typography color="text.secondary" textAlign="center" py={3}>
                    아직 필드가 없습니다
                  </Typography>
                ) : (
                  <DndContext
                    sensors={sensors}
                    collisionDetection={closestCenter}
                    onDragEnd={handleFieldDragEnd}
                  >
                    <SortableContext
                      items={section.fields.map((f) => f.id)}
                      strategy={verticalListSortingStrategy}
                    >
                      {section.fields.map((field, index) => (
                        <SortableFieldEditor
                          key={field.id}
                          field={field}
                          sectionId={section.id}
                          isFirst={index === 0}
                          isLast={index === section.fields.length - 1}
                          isSelected={selectedFieldId === field.id}
                          onSelect={() => onFieldSelect?.(field.id)}
                          onUpdate={onUpdateField}
                          onRemove={onRemoveField}
                          onMove={onMoveField}
                        />
                      ))}
                    </SortableContext>
                  </DndContext>
                )}
              </Box>
              <Button
                size="small"
                startIcon={<AddIcon />}
                onClick={() => onAddField(section.id)}
                fullWidth
              >
                필드 추가
              </Button>
            </>
          )}

          {section.type === "image" && (
            <Box>
              {imageSrc ? (
                <Box sx={{ textAlign: "center" }}>
                  <Box
                    component="img"
                    src={imageSrc}
                    alt={imageContent?.alt || ""}
                    sx={{
                      maxWidth: "100%",
                      maxHeight: 200,
                      objectFit: "contain",
                      borderRadius: 1,
                      border: "1px solid",
                      borderColor: "divider",
                    }}
                  />
                  <Box sx={{ mt: 1 }}>
                    <Button
                      size="small"
                      startIcon={<SettingsIcon />}
                      onClick={() => setImageModalOpen(true)}
                    >
                      변경
                    </Button>
                  </Box>
                </Box>
              ) : (
                <Button
                  variant="outlined"
                  startIcon={<ImageIcon />}
                  onClick={() => setImageModalOpen(true)}
                  fullWidth
                  sx={{ py: 3 }}
                >
                  이미지 추가
                </Button>
              )}
            </Box>
          )}

          {/* 설명 섹션은 위 설명 필드로 처리되므로 추가 UI 없음 */}
        </AccordionDetails>
      </Accordion>

      {/* 이미지 모달 */}
      <ImageModal
        open={imageModalOpen}
        onClose={() => setImageModalOpen(false)}
        onSave={(content) => onUpdate(section.id, { content })}
        initialContent={imageContent}
      />
    </>
  )
}
