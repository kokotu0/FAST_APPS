import { useState, useCallback } from "react"
import {
  Box,
  Button,
  Checkbox,
  Collapse,
  FormControlLabel,
  IconButton,
  MenuItem,
  Paper,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material"
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  KeyboardArrowUp as UpIcon,
  KeyboardArrowDown as DownIcon,
  Code as CodeIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
} from "@mui/icons-material"
import type { RJSFSchema, UiSchema } from "@rjsf/utils"

type WidgetType =
  | "text"
  | "textarea"
  | "number"
  | "integer"
  | "checkbox"
  | "select"
  | "multiselect"
  | "date"
  | "email"
  | "url"

interface FormField {
  id: string
  name: string
  label: string
  widget: WidgetType
  required: boolean
  placeholder?: string
  description?: string
  options?: string
}

interface FormBuilderProps {
  onChange?: (data: {
    jsonSchema: RJSFSchema
    uiSchema: UiSchema
    theme: Record<string, unknown>
  }) => void
  initialFields?: FormField[]
  focusFieldName?: string
}

export type { FormField }

const WIDGET_TYPES: { value: WidgetType; label: string }[] = [
  { value: "text", label: "텍스트" },
  { value: "textarea", label: "여러 줄 텍스트" },
  { value: "number", label: "숫자" },
  { value: "integer", label: "정수" },
  { value: "checkbox", label: "체크박스" },
  { value: "select", label: "선택 (단일)" },
  { value: "multiselect", label: "선택 (다중)" },
  { value: "date", label: "날짜" },
  { value: "email", label: "이메일" },
  { value: "url", label: "URL" },
]

const fieldToSchemaProperty = (field: FormField): Record<string, unknown> => {
  const options = field.options?.split("\n").filter(Boolean) || []

  switch (field.widget) {
    case "text":
      return { type: "string", title: field.label, description: field.description }
    case "textarea":
      return { type: "string", title: field.label, description: field.description }
    case "number":
      return { type: "number", title: field.label, description: field.description }
    case "integer":
      return { type: "integer", title: field.label, description: field.description }
    case "checkbox":
      return { type: "boolean", title: field.label, description: field.description }
    case "select":
      return {
        type: "string",
        title: field.label,
        description: field.description,
        enum: options,
      }
    case "multiselect":
      return {
        type: "array",
        title: field.label,
        description: field.description,
        items: {
          type: "string",
          enum: options,
        },
        uniqueItems: true,
      }
    case "date":
      return { type: "string", title: field.label, description: field.description, format: "date" }
    case "email":
      return { type: "string", title: field.label, description: field.description, format: "email" }
    case "url":
      return { type: "string", title: field.label, description: field.description, format: "uri" }
    default:
      return { type: "string", title: field.label }
  }
}

const fieldToUiSchema = (field: FormField): Record<string, unknown> | undefined => {
  const ui: Record<string, unknown> = {}

  if (field.placeholder) {
    ui["ui:placeholder"] = field.placeholder
  }

  switch (field.widget) {
    case "textarea":
      ui["ui:widget"] = "textarea"
      break
    case "multiselect":
      ui["ui:widget"] = "checkboxes"
      break
  }

  return Object.keys(ui).length > 0 ? ui : undefined
}

const fieldsToJsonSchema = (fields: FormField[]): RJSFSchema => {
  const properties: RJSFSchema["properties"] = {}
  fields.forEach((field) => {
    properties![field.name] = fieldToSchemaProperty(field)
  })
  const required = fields.filter((f) => f.required).map((f) => f.name)
  return {
    type: "object",
    properties,
    ...(required.length > 0 && { required }),
  }
}

const fieldsToUiSchema = (fields: FormField[]): UiSchema => {
  const uiSchema: UiSchema = {
    "ui:order": fields.map((f) => f.name),
  }
  fields.forEach((field) => {
    const fieldUi = fieldToUiSchema(field)
    if (fieldUi) {
      uiSchema[field.name] = fieldUi
    }
  })
  return uiSchema
}

export const FormBuilder = ({ onChange, initialFields = [], focusFieldName }: FormBuilderProps) => {
  const [fields, setFields] = useState<FormField[]>(initialFields)
  const [theme] = useState<Record<string, unknown>>({})
  const [showSchema, setShowSchema] = useState(false)

  const notifyChange = useCallback(
    (updatedFields: FormField[]) => {
      onChange?.({
        jsonSchema: fieldsToJsonSchema(updatedFields),
        uiSchema: fieldsToUiSchema(updatedFields),
        theme,
      })
    },
    [onChange, theme]
  )

  const addField = () => {
    const newField: FormField = {
      id: `field_${Date.now()}`,
      name: `field_${fields.length + 1}`,
      label: `필드 ${fields.length + 1}`,
      widget: "text",
      required: false,
    }
    const updated = [...fields, newField]
    setFields(updated)
    notifyChange(updated)
  }

  const removeField = (id: string) => {
    const updated = fields.filter((f) => f.id !== id)
    setFields(updated)
    notifyChange(updated)
  }

  const updateField = (id: string, updates: Partial<FormField>) => {
    const updated = fields.map((f) => (f.id === id ? { ...f, ...updates } : f))
    setFields(updated)
    notifyChange(updated)
  }

  const moveField = (index: number, dir: "up" | "down") => {
    if ((dir === "up" && index === 0) || (dir === "down" && index === fields.length - 1)) return
    const arr = [...fields]
    const target = dir === "up" ? index - 1 : index + 1
    ;[arr[index], arr[target]] = [arr[target], arr[index]]
    setFields(arr)
    notifyChange(arr)
  }

  const needsOptions = (w: WidgetType) => w === "select" || w === "multiselect"

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1}>
        <Typography variant="subtitle2" fontWeight="bold">
          폼 빌더
        </Typography>
        <Button size="small" variant="contained" startIcon={<AddIcon />} onClick={addField}>
          필드 추가
        </Button>
      </Stack>

      {fields.length === 0 ? (
        <Box
          sx={{
            p: 2,
            border: "1px dashed",
            borderColor: "grey.400",
            borderRadius: 1,
            textAlign: "center",
            color: "grey.500",
          }}
        >
          <Typography variant="body2">필드가 없습니다</Typography>
        </Box>
      ) : (
        <Stack spacing={1}>
          {fields.map((field, index) => (
            <Paper
              key={field.id}
              variant="outlined"
              sx={{
                p: 1.5,
                borderColor: focusFieldName === field.name ? "primary.main" : "grey.300",
                borderWidth: focusFieldName === field.name ? 2 : 1,
                bgcolor: focusFieldName === field.name ? "primary.50" : "background.paper",
                transition: "all 0.2s",
              }}
            >
              {/* 헤더 */}
              <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1}>
                <Stack direction="row" alignItems="center" spacing={0}>
                  <IconButton size="small" onClick={() => moveField(index, "up")} disabled={index === 0}>
                    <UpIcon fontSize="small" />
                  </IconButton>
                  <IconButton size="small" onClick={() => moveField(index, "down")} disabled={index === fields.length - 1}>
                    <DownIcon fontSize="small" />
                  </IconButton>
                  <Typography variant="caption" fontWeight="bold" ml={0.5}>
                    #{index + 1}
                  </Typography>
                </Stack>
                <IconButton size="small" color="error" onClick={() => removeField(field.id)}>
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </Stack>

              {/* 필드명 + 라벨 */}
              <Stack direction="row" spacing={1} mb={1}>
                <TextField
                  size="small"
                  fullWidth
                  value={field.name}
                  onChange={(e) => updateField(field.id, { name: e.target.value })}
                  placeholder="필드명"
                  variant="outlined"
                />
                <TextField
                  size="small"
                  fullWidth
                  value={field.label}
                  onChange={(e) => updateField(field.id, { label: e.target.value })}
                  placeholder="라벨"
                  variant="outlined"
                />
              </Stack>

              {/* 타입 + 필수 */}
              <Stack direction="row" spacing={1} alignItems="center" mb={1}>
                <Select
                  size="small"
                  fullWidth
                  value={field.widget}
                  onChange={(e) => updateField(field.id, { widget: e.target.value as WidgetType })}
                >
                  {WIDGET_TYPES.map((t) => (
                    <MenuItem key={t.value} value={t.value}>
                      {t.label}
                    </MenuItem>
                  ))}
                </Select>
                <FormControlLabel
                  control={
                    <Checkbox
                      size="small"
                      checked={field.required}
                      onChange={(e) => updateField(field.id, { required: e.target.checked })}
                    />
                  }
                  label={<Typography variant="caption">필수</Typography>}
                  sx={{ whiteSpace: "nowrap", ml: 0 }}
                />
              </Stack>

              {/* placeholder */}
              <TextField
                size="small"
                fullWidth
                value={field.placeholder || ""}
                onChange={(e) => updateField(field.id, { placeholder: e.target.value })}
                placeholder="플레이스홀더"
                variant="outlined"
                sx={{ mb: needsOptions(field.widget) ? 1 : 0 }}
              />

              {/* select/multiselect용 옵션 */}
              {needsOptions(field.widget) && (
                <TextField
                  size="small"
                  fullWidth
                  value={field.options || ""}
                  onChange={(e) => updateField(field.id, { options: e.target.value })}
                  placeholder="옵션 (줄바꿈 구분)"
                  variant="outlined"
                  multiline
                  rows={2}
                />
              )}
            </Paper>
          ))}
        </Stack>
      )}

      {/* JSON Schema 접기 */}
      {fields.length > 0 && (
        <Box mt={1}>
          <Button
            size="small"
            fullWidth
            variant="text"
            startIcon={<CodeIcon />}
            endIcon={showSchema ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            onClick={() => setShowSchema(!showSchema)}
            sx={{ justifyContent: "space-between" }}
          >
            JSON Schema
          </Button>
          <Collapse in={showSchema}>
            <Paper variant="outlined" sx={{ p: 1, mt: 0.5, bgcolor: "grey.100" }}>
              <Box
                component="pre"
                sx={{ fontSize: 10, overflow: "auto", maxHeight: 200, m: 0 }}
              >
                {JSON.stringify(fieldsToJsonSchema(fields), null, 2)}
              </Box>
            </Paper>
          </Collapse>
        </Box>
      )}
    </Box>
  )
}

export default FormBuilder
