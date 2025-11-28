import { useState } from "react"
import {
  Box,
  Button,
  IconButton,
  TextField,
  Typography,
  Paper,
  Stack,
  FormControlLabel,
  Checkbox,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Collapse,
  Divider,
} from "@mui/material"
import {
  Delete as DeleteIcon,
  KeyboardArrowUp as UpIcon,
  KeyboardArrowDown as DownIcon,
  DragIndicator as DragIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
} from "@mui/icons-material"
import type { FieldDefinition, FieldSchemaType, FieldWidget, FieldFormat } from "../types"
import { 
  USER_FIELD_TYPES, 
  TEXT_FORMAT_OPTIONS, 
  SELECT_DISPLAY_OPTIONS, 
  MULTISELECT_DISPLAY_OPTIONS,
  NUMBER_FORMAT_OPTIONS,
  NUMBER_WIDGET_OPTIONS,
} from "../constants"

export interface FieldEditorProps {
  field: FieldDefinition
  sectionId: string
  isFirst: boolean
  isLast: boolean
  isSelected?: boolean
  onSelect?: () => void
  onUpdate: (sectionId: string, fieldId: string, updates: Partial<FieldDefinition>) => void
  onRemove: (sectionId: string, fieldId: string) => void
  onMove: (sectionId: string, fieldId: string, direction: "up" | "down") => void
  dragHandleProps?: Record<string, unknown>
}

export const FieldEditor = ({
  field,
  sectionId,
  isFirst,
  isLast,
  isSelected,
  onSelect,
  onUpdate,
  onRemove,
  onMove,
  dragHandleProps,
}: FieldEditorProps) => {
  const [expanded, setExpanded] = useState(true)
  const [enumInput, setEnumInput] = useState("")

  // 현재 필드 타입 찾기
  const getCurrentUserType = (): string => {
    if (field.schema.type === "boolean") return "checkbox"
    if (field.schema.type === "array") return "multiselect"
    if (field.schema.format === "data-url") return "file"
    if (field.ui.widget === "select" || field.ui.widget === "radio") return "select"
    if (field.schema.type === "number" || field.schema.type === "integer") return "number"
    return "text"
  }

  // 텍스트 포맷
  const getCurrentTextFormat = (): string => {
    if (field.ui.widget === "textarea") return "textarea"
    if (field.schema.format === "email") return "email"
    if (field.schema.format === "uri") return "uri"
    if (field.schema.format === "date") return "date"
    if (field.schema.format === "date-time") return "datetime"
    if (field.schema.format === "password") return "password"
    // 핸드폰 체크 (placeholder로 판단)
    if (field.ui.placeholder?.includes("010")) return "phone"
    return "default"
  }

  // 숫자 포맷 (정수/소수)
  const getCurrentNumberFormat = (): string => {
    return field.schema.type === "integer" ? "integer" : "number"
  }

  const currentUserType = getCurrentUserType()
  const currentTextFormat = getCurrentTextFormat()
  const currentNumberFormat = getCurrentNumberFormat()
  const currentTypeConfig = USER_FIELD_TYPES.find(t => t.value === currentUserType)

  // 필드 타입 변경
  const handleTypeChange = (typeValue: string) => {
    const typeConfig = USER_FIELD_TYPES.find(t => t.value === typeValue)
    if (!typeConfig) return

    const updates: Partial<FieldDefinition> = {
      schema: {
        ...field.schema,
        type: typeConfig.schemaType,
        format: typeConfig.format,
        pattern: undefined,
        enum: typeConfig.needsEnum ? (field.schema.enum || []) : undefined,
        items: typeConfig.schemaType === "array" 
          ? { type: "string" as FieldSchemaType, enum: field.schema.items?.enum || [] }
          : undefined,
        uniqueItems: typeConfig.schemaType === "array" ? true : undefined,
        minimum: undefined,
        maximum: undefined,
        minLength: undefined,
        maxLength: undefined,
      },
      ui: {
        ...field.ui,
        widget: typeConfig.widget,
        placeholder: undefined,
        options: typeConfig.value === "file" ? { filePreview: true } : undefined,
      },
    }
    onUpdate(sectionId, field.id, updates)
  }

  // 텍스트 포맷 변경
  const handleTextFormatChange = (formatValue: string) => {
    const formatConfig = TEXT_FORMAT_OPTIONS.find(f => f.value === formatValue)
    if (!formatConfig) return

    onUpdate(sectionId, field.id, {
      schema: {
        ...field.schema,
        format: formatConfig.format as FieldFormat | undefined,
        pattern: undefined,
      },
      ui: {
        ...field.ui,
        widget: formatConfig.widget,
        placeholder: formatConfig.placeholder || field.ui.placeholder,
      },
    })
  }

  // 숫자 포맷 변경 (정수/소수)
  const handleNumberFormatChange = (formatValue: string) => {
    const formatConfig = NUMBER_FORMAT_OPTIONS.find(f => f.value === formatValue)
    if (!formatConfig) return

    onUpdate(sectionId, field.id, {
      schema: { ...field.schema, type: formatConfig.schemaType },
    })
  }

  // 선택 표시 방식 변경
  const handleDisplayChange = (widget: FieldWidget) => {
    onUpdate(sectionId, field.id, {
      ui: { ...field.ui, widget },
    })
  }

  // Enum 관련
  const currentEnums = field.schema.type === "array" 
    ? field.schema.items?.enum 
    : field.schema.enum

  const handleAddEnum = () => {
    if (!enumInput.trim()) return
    const newEnum = [...(currentEnums || []), enumInput.trim()]

    if (field.schema.type === "array") {
      onUpdate(sectionId, field.id, {
        schema: {
          ...field.schema,
          items: { type: "string" as FieldSchemaType, enum: newEnum },
          uniqueItems: true,
        },
      })
    } else {
      onUpdate(sectionId, field.id, {
        schema: { ...field.schema, enum: newEnum },
      })
    }
    setEnumInput("")
  }

  const handleRemoveEnum = (index: number) => {
    if (!currentEnums) return
    const newEnum = currentEnums.filter((_, i) => i !== index)

    if (field.schema.type === "array") {
      onUpdate(sectionId, field.id, {
        schema: {
          ...field.schema,
          items: { type: "string" as FieldSchemaType, enum: newEnum },
        },
      })
    } else {
      onUpdate(sectionId, field.id, {
        schema: { ...field.schema, enum: newEnum },
      })
    }
  }

  // 타입 라벨
  const getTypeLabel = () => {
    const typeConfig = USER_FIELD_TYPES.find(t => t.value === currentUserType)
    if (!typeConfig) return currentUserType

    if (currentUserType === "text") {
      const formatConfig = TEXT_FORMAT_OPTIONS.find(f => f.value === currentTextFormat)
      if (formatConfig && formatConfig.value !== "default") {
        return `${typeConfig.label} (${formatConfig.label})`
      }
    }
    if (currentUserType === "number") {
      return currentNumberFormat === "integer" ? "숫자 (정수)" : "숫자"
    }
    return typeConfig.label
  }

  return (
    <Paper 
      variant="outlined" 
      sx={{ 
        mb: 1, 
        overflow: "hidden",
        borderColor: isSelected ? "primary.main" : undefined,
        borderWidth: isSelected ? 2 : 1,
        boxShadow: isSelected ? "0 0 0 3px rgba(25, 118, 210, 0.15)" : undefined,
        transition: "all 0.2s ease",
      }}
      onClick={onSelect}
    >
      {/* 헤더 */}
      <Stack
        direction="row"
        spacing={1}
        alignItems="center"
        sx={{ 
          p: 1, 
          bgcolor: isSelected ? "primary.50" : (expanded ? "grey.50" : "transparent"), 
          cursor: "pointer",
        }}
        onClick={(e) => { e.stopPropagation(); setExpanded(!expanded) }}
      >
        {/* 드래그 핸들 */}
        {dragHandleProps ? (
          <Box 
            {...dragHandleProps} 
            sx={{ cursor: "grab", display: "flex" }}
            onClick={(e) => e.stopPropagation()}
          >
            <DragIcon fontSize="small" sx={{ color: "text.secondary" }} />
          </Box>
        ) : (
          <Stack spacing={0} onClick={(e) => e.stopPropagation()}>
            <IconButton size="small" disabled={isFirst} onClick={() => onMove(sectionId, field.id, "up")}>
              <UpIcon fontSize="small" />
            </IconButton>
            <IconButton size="small" disabled={isLast} onClick={() => onMove(sectionId, field.id, "down")}>
              <DownIcon fontSize="small" />
            </IconButton>
          </Stack>
        )}

        {expanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}

        <Typography variant="body2" fontWeight={500} sx={{ flex: 1 }}>
          {field.schema.title || "새 필드"}
        </Typography>
        
        <Chip label={getTypeLabel()} size="small" variant="outlined" />
        
        {field.required && (
          <Chip label="필수" size="small" color="error" variant="outlined" />
        )}

        <IconButton 
          size="small" 
          color="error" 
          onClick={(e) => { e.stopPropagation(); onRemove(sectionId, field.id) }}
        >
          <DeleteIcon fontSize="small" />
        </IconButton>
      </Stack>

      {/* 상세 설정 */}
      <Collapse in={expanded}>
        <Box sx={{ p: 1.5, pt: 0.5 }}>
          <input type="hidden" value={field.name} />

          {/* 타입 설정 */}
          <Stack direction="row" spacing={1} mb={1.5} flexWrap="wrap">
            <FormControl size="small" sx={{ minWidth: 110 }}>
              <InputLabel>타입</InputLabel>
              <Select
                value={currentUserType}
                label="타입"
                onChange={(e) => handleTypeChange(e.target.value)}
              >
                {USER_FIELD_TYPES.map((opt) => (
                  <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* 텍스트 포맷 */}
            {currentUserType === "text" && (
              <FormControl size="small" sx={{ minWidth: 110 }}>
                <InputLabel>포맷</InputLabel>
                <Select
                  value={currentTextFormat}
                  label="포맷"
                  onChange={(e) => handleTextFormatChange(e.target.value)}
                >
                  {TEXT_FORMAT_OPTIONS.map((opt) => (
                    <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            )}

            {/* 숫자 포맷 */}
            {currentUserType === "number" && (
              <>
                <FormControl size="small" sx={{ minWidth: 100 }}>
                  <InputLabel>형식</InputLabel>
                  <Select
                    value={currentNumberFormat}
                    label="형식"
                    onChange={(e) => handleNumberFormatChange(e.target.value)}
                  >
                    {NUMBER_FORMAT_OPTIONS.map((opt) => (
                      <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <FormControl size="small" sx={{ minWidth: 100 }}>
                  <InputLabel>위젯</InputLabel>
                  <Select
                    value={field.ui.widget || "default"}
                    label="위젯"
                    onChange={(e) => {
                      const widget = e.target.value === "default" ? undefined : e.target.value as FieldWidget
                      onUpdate(sectionId, field.id, {
                        ui: { ...field.ui, widget },
                      })
                    }}
                  >
                    {NUMBER_WIDGET_OPTIONS.map((opt) => (
                      <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </>
            )}

            {/* 선택 표시 방식 */}
            {currentUserType === "select" && (
              <FormControl size="small" sx={{ minWidth: 120 }}>
                <InputLabel>표시</InputLabel>
                <Select
                  value={field.ui.widget || "select"}
                  label="표시"
                  onChange={(e) => handleDisplayChange(e.target.value as FieldWidget)}
                >
                  {SELECT_DISPLAY_OPTIONS.map((opt) => (
                    <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            )}

            {/* 다중선택 표시 방식 */}
            {currentUserType === "multiselect" && (
              <FormControl size="small" sx={{ minWidth: 150 }}>
                <InputLabel>표시</InputLabel>
                <Select
                  value={field.ui.widget || "checkboxes"}
                  label="표시"
                  onChange={(e) => handleDisplayChange(e.target.value as FieldWidget)}
                >
                  {MULTISELECT_DISPLAY_OPTIONS.map((opt) => (
                    <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            )}
          </Stack>

          <Divider sx={{ my: 1 }} />

          {/* 기본 정보 */}
          <Stack direction="row" spacing={1} mb={1}>
            <TextField
              key={`title-${field.id}`}
              size="small"
              label="제목"
              defaultValue={field.schema.title}
              onBlur={(e) => onUpdate(sectionId, field.id, {
                schema: { ...field.schema, title: e.target.value },
              })}
              sx={{ flex: 1 }}
            />
            <TextField
              key={`placeholder-${field.id}`}
              size="small"
              label="안내 문구"
              defaultValue={field.ui.placeholder || ""}
              onBlur={(e) => onUpdate(sectionId, field.id, {
                ui: { ...field.ui, placeholder: e.target.value },
              })}
              sx={{ flex: 1 }}
            />
          </Stack>

          <TextField
            key={`desc-${field.id}`}
            size="small"
            label="설명"
            fullWidth
            defaultValue={field.schema.description || ""}
            onBlur={(e) => onUpdate(sectionId, field.id, {
              schema: { ...field.schema, description: e.target.value },
            })}
            sx={{ mb: 1 }}
          />

          {/* 선택 옵션 */}
          {currentTypeConfig?.needsEnum && (
            <Box mb={1}>
              <Typography variant="caption" color="text.secondary" fontWeight={500}>
                선택 옵션
              </Typography>
              <Stack direction="row" spacing={0.5} flexWrap="wrap" gap={0.5} mb={0.5} mt={0.5}>
                {currentEnums?.map((item, i) => (
                  <Chip
                    key={i}
                    label={String(item)}
                    size="small"
                    onDelete={() => handleRemoveEnum(i)}
                  />
                ))}
                {(!currentEnums || currentEnums.length === 0) && (
                  <Typography variant="caption" color="text.secondary">
                    옵션을 추가하세요
                  </Typography>
                )}
              </Stack>
              <Stack direction="row" spacing={1}>
                <TextField
                  size="small"
                  placeholder="옵션 입력 후 Enter"
                  value={enumInput}
                  onChange={(e) => setEnumInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), handleAddEnum())}
                  sx={{ flex: 1 }}
                />
                <Button size="small" variant="outlined" onClick={handleAddEnum}>
                  추가
                </Button>
              </Stack>
            </Box>
          )}

          {/* Validation - 텍스트 */}
          {currentUserType === "text" && currentTextFormat !== "textarea" && (
            <Stack direction="row" spacing={1} mb={1}>
              <TextField
                key={`minLength-${field.id}`}
                size="small"
                label="최소 글자수"
                type="number"
                defaultValue={field.schema.minLength ?? ""}
                onBlur={(e) => onUpdate(sectionId, field.id, {
                  schema: { ...field.schema, minLength: e.target.value ? Number(e.target.value) : undefined },
                })}
                inputProps={{ min: 0 }}
              />
              <TextField
                key={`maxLength-${field.id}`}
                size="small"
                label="최대 글자수"
                type="number"
                defaultValue={field.schema.maxLength ?? ""}
                onBlur={(e) => onUpdate(sectionId, field.id, {
                  schema: { ...field.schema, maxLength: e.target.value ? Number(e.target.value) : undefined },
                })}
                inputProps={{ min: 0 }}
              />
            </Stack>
          )}

          {/* Validation - 숫자 */}
          {currentUserType === "number" && (
            <Stack direction="row" spacing={1} mb={1}>
              <TextField
                key={`min-${field.id}`}
                size="small"
                label="최솟값"
                type="number"
                defaultValue={field.schema.minimum ?? ""}
                onBlur={(e) => onUpdate(sectionId, field.id, {
                  schema: { ...field.schema, minimum: e.target.value !== "" ? Number(e.target.value) : undefined },
                })}
              />
              <TextField
                key={`max-${field.id}`}
                size="small"
                label="최댓값"
                type="number"
                defaultValue={field.schema.maximum ?? ""}
                onBlur={(e) => onUpdate(sectionId, field.id, {
                  schema: { ...field.schema, maximum: e.target.value !== "" ? Number(e.target.value) : undefined },
                })}
              />
            </Stack>
          )}

          {/* 파일 옵션 */}
          {currentUserType === "file" && (
            <FormControlLabel
              control={
                <Checkbox
                  size="small"
                  checked={!!(field.ui.options as { filePreview?: boolean })?.filePreview}
                  onChange={(e) => onUpdate(sectionId, field.id, {
                    ui: { ...field.ui, options: { ...field.ui.options, filePreview: e.target.checked } },
                  })}
                />
              }
              label={<Typography variant="body2">미리보기 표시</Typography>}
            />
          )}

          {/* 필수 여부 */}
          <FormControlLabel
            control={
              <Checkbox
                size="small"
                checked={field.required}
                onChange={(e) => onUpdate(sectionId, field.id, { required: e.target.checked })}
              />
            }
            label={<Typography variant="body2">필수 입력</Typography>}
          />
        </Box>
      </Collapse>
    </Paper>
  )
}
