import { useState } from "react"
import { Box, Button, Paper, Stack, TextField, Typography } from "@mui/material"
import { Save as SaveIcon } from "@mui/icons-material"
import { createFileRoute } from "@tanstack/react-router"
import {
  FormBuilder,
  FormPreview,
  type FormRegisterData,
  type RJSFSchema,
  type UiSchema,
} from "@/features/formRegister/components"

export const Route = createFileRoute("/_layout/form-register/$idx")({
  component: RouteComponent,
})

const DEFAULT_SCHEMA: RJSFSchema = {
  type: "object",
  properties: {},
}

const DEFAULT_UI_SCHEMA: UiSchema = {}

function RouteComponent() {
  const { idx } = Route.useParams()
  const isNew = idx === "new"

  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")
  const [schemaData, setSchemaData] = useState<{
    jsonSchema: RJSFSchema
    uiSchema: UiSchema
    theme: Record<string, unknown>
  }>({
    jsonSchema: DEFAULT_SCHEMA,
    uiSchema: DEFAULT_UI_SCHEMA,
    theme: {},
  })

  const [focusFieldName, setFocusFieldName] = useState<string | undefined>()

  const handleSchemaChange = (data: {
    jsonSchema: RJSFSchema
    uiSchema: UiSchema
    theme: Record<string, unknown>
  }) => {
    setSchemaData(data)
  }

  const handleFieldClick = (fieldName: string) => {
    setFocusFieldName(fieldName)
    setTimeout(() => setFocusFieldName(undefined), 3000)
  }

  const handleSubmit = () => {
    const data: FormRegisterData = {
      title,
      description,
      jsonSchema: schemaData.jsonSchema,
      uiSchema: schemaData.uiSchema,
      theme: schemaData.theme,
    }
    console.log("폼 데이터:", data)
    // TODO: 백엔드 API 호출
  }

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "calc(100vh - 64px)",
        p: 1.5,
        gap: 1.5,
      }}
    >
      {/* 상단: 기본 정보 */}
      <Paper variant="outlined" sx={{ px: 2, py: 1, flexShrink: 0 }}>
        <Stack direction="row" spacing={1.5} alignItems="center">
          <Typography variant="subtitle2" fontWeight="bold" whiteSpace="nowrap">
            {isNew ? "폼 등록" : `폼 #${idx} 수정`}
          </Typography>
          <TextField
            size="small"
            fullWidth
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="폼 제목"
            variant="outlined"
            sx={{ flex: 1 }}
          />
          <TextField
            size="small"
            fullWidth
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="폼 설명 (선택)"
            variant="outlined"
            sx={{ flex: 2 }}
          />
          <Button
            variant="contained"
            size="small"
            startIcon={<SaveIcon />}
            onClick={handleSubmit}
          >
            저장
          </Button>
        </Stack>
      </Paper>

      {/* 하단: 미리보기 + 빌더 */}
      <Stack
        direction={{ xs: "column", lg: "row" }}
        spacing={1.5}
        sx={{ flex: 1, minHeight: 0 }}
      >
        {/* 왼쪽: 폼 미리보기 */}
        <Paper
          variant="outlined"
          sx={{
            flex: 1,
            p: 1.5,
            overflow: "auto",
          }}
        >
          <FormPreview
            jsonSchema={schemaData.jsonSchema}
            uiSchema={schemaData.uiSchema}
            onFieldClick={handleFieldClick}
          />
        </Paper>

        {/* 오른쪽: 폼 빌더 */}
        <Paper
          variant="outlined"
          sx={{
            flex: 1,
            p: 1.5,
            overflow: "auto",
          }}
        >
          <FormBuilder
            onChange={handleSchemaChange}
            focusFieldName={focusFieldName}
          />
        </Paper>
      </Stack>
    </Box>
  )
}
