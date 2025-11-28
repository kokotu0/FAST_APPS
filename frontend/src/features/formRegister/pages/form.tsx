import { FormBuilder } from "@/features/formRegister/components/FormBuilder/FormBulider"
import {
  ObjectFieldTemplate,
  SubmitButton,
  customWidgets,
} from "@/features/formRegister/components/FormBuilder/components"
import FormJSON from "@/features/formRegister/components/FormJSON"
import { useFormRegister } from "@/features/formRegister/hooks/useFormRegister"
import {
  type FormRegisterCreateFormData,
  type FormRegisterUpdateFormData,
} from "@/client"
import { 
  Box, 
  Button, 
  Paper, 
  Tab, 
  Tabs, 
  TextField, 
  Typography,
  Stack,
  Snackbar,
  Alert,
  CircularProgress,
} from "@mui/material"
import { Save as SaveIcon } from "@mui/icons-material"
import { useState, useCallback, useEffect } from "react"
import type { RJSFSchema, UiSchema } from "@rjsf/utils"
import type { IChangeEvent } from "@rjsf/core"
import Form from "@rjsf/mui"
import validator from "@rjsf/validator-ajv8"
import { nanoid } from "nanoid"
import { useNavigate } from "@tanstack/react-router"

interface FormPageProps {
  uuid?: string  // "new" 또는 실제 uuid
}

function FormPage({ uuid }: FormPageProps) {
  const navigate = useNavigate()
  const isNew = !uuid || uuid === "new"
  
  // 훅 가져오기
  const { useFormDetail, createMutation, updateMutation } = useFormRegister()
  const { data: formData, isLoading } = useFormDetail(uuid)
  
  // 폼 메타 정보
  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")
  const [category, setCategory] = useState("default")
  
  // 스키마 상태
  const [schema, setSchema] = useState<RJSFSchema>({})
  const [uiSchema, setUiSchema] = useState<UiSchema>({})
  const [previewData, setPreviewData] = useState<unknown>({})
  
  // UI 상태
  const [selectedFieldId, setSelectedFieldId] = useState<string | null>(null)
  const [tab, setTab] = useState(0)
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: "success" | "error" }>({
    open: false,
    message: "",
    severity: "success",
  })

  // 기존 데이터 로드
  useEffect(() => {
    if (formData?.data) {
      setTitle(formData.data?.title || "" )
      setDescription(formData.data?.description || "" )
      setCategory(formData.data?.category || "")
      setSchema(formData.data?.JSONSchema || {})
      setUiSchema(formData.data?.UISchema || {})
    }
  }, [formData])

  // 스키마 변경 콜백
  const handleSchemaChange = useCallback((newSchema: RJSFSchema) => {
    setSchema(newSchema)
  }, [])

  const handleUiSchemaChange = useCallback((newUiSchema: UiSchema) => {
    setUiSchema(newUiSchema)
  }, [])

  // 폼 데이터 변경 콜백
  const handleFormChange = useCallback((e: IChangeEvent) => {
    setPreviewData(e.formData)
  }, [])

  // 폼 제출 콜백 (미리보기용)
  const handleFormSubmit = useCallback((e: IChangeEvent) => {
    console.log("Form preview submitted:", e.formData)
  }, [])

  // 폼 저장
  const handleSave = async () => {
    if (!title.trim()) {
      setSnackbar({ open: true, message: "제목을 입력해주세요", severity: "error" })
      return
    }

    try {
      if (isNew) {
        const newUuid = nanoid()
        const payload: FormRegisterCreateFormData["requestBody"] = {
          uuid: newUuid,
          category,
          title,
          description,
          JSONSchema: schema,
          UISchema: uiSchema,
          Theme: "mui",
        }
        
        await createMutation.mutateAsync(payload)
        setSnackbar({ open: true, message: "폼이 생성되었습니다", severity: "success" })
        
        // 생성 후 해당 폼 페이지로 이동
        navigate({ to: "/form-register/$idx", params: { idx: newUuid } })
      } else {
        const payload: FormRegisterUpdateFormData["requestBody"] = {
          category,
          title,
          description,
          JSONSchema: schema,
          UISchema: uiSchema,
        }
        
        await updateMutation.mutateAsync({ formUuid: uuid!, data: payload })
        setSnackbar({ open: true, message: "폼이 저장되었습니다", severity: "success" })
      }
    } catch (error) {
      console.error("Save error:", error)
      setSnackbar({ 
        open: true, 
        message: error instanceof Error ? error.message : "저장 중 오류가 발생했습니다", 
        severity: "error" 
      })
    }
  }

  const isSaving = createMutation.isPending || updateMutation.isPending

  // 로딩 중
  if (!isNew && isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="calc(100vh - 64px)">
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box display="flex" flexDirection="column" height="calc(100vh - 64px)" p={2} gap={2}>
      {/* 상단: 메타 정보 + 저장 버튼 */}
      <Paper variant="outlined" sx={{ p: 2, flexShrink: 0 }}>
        <Stack direction="row" spacing={2} alignItems="center">
          <TextField
            size="small"
            label="제목"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            sx={{ flex: 1 }}
            required
          />
          <TextField
            size="small"
            label="설명"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            sx={{ flex: 2 }}
          />
          <TextField
            size="small"
            label="카테고리"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            sx={{ width: 150 }}
          />
          <Button
            variant="contained"
            startIcon={isSaving ? <CircularProgress size={16} color="inherit" /> : <SaveIcon />}
            onClick={handleSave}
            disabled={isSaving}
          >
            {isSaving ? "저장 중..." : isNew ? "생성" : "저장"}
          </Button>
        </Stack>
      </Paper>

      {/* 하단: 빌더 + 미리보기 */}
      <Box display="grid" gridTemplateColumns="1fr 1fr" gap={2} flex={1} minHeight={0}>
        {/* 왼쪽: 폼 미리보기 / 스키마 뷰어 (탭) */}
        <Paper
          variant="outlined"
          sx={{ display: "flex", flexDirection: "column", overflow: "hidden" }}
        >
          <Tabs
            value={tab}
            onChange={(_, v: number) => setTab(v)}
            sx={{ borderBottom: 1, borderColor: "divider", flexShrink: 0 }}
          >
            <Tab label="폼 미리보기" />
            <Tab label="스키마 뷰어" />
          </Tabs>

          <Box sx={{ flex: 1, overflow: "auto", p: 2 }}>
            {tab === 0 && (
              <Form
                schema={schema}
                uiSchema={uiSchema}
                formData={previewData}
                validator={validator}
                onChange={handleFormChange}
                onSubmit={handleFormSubmit}
                templates={{
                  ObjectFieldTemplate,
                  ButtonTemplates: { SubmitButton },
                }}
                widgets={customWidgets}
              />
            )}
            {tab === 1 && (
              <FormJSON 
                schema={schema} 
                uiSchema={uiSchema} 
                formData={previewData}
              />
            )}
          </Box>
        </Paper>

        {/* 오른쪽: 폼 빌더 */}
        <Paper
          variant="outlined"
          sx={{ display: "flex", flexDirection: "column", overflow: "hidden" }}
        >
          <Box
            sx={{
              p: 1.5,
              borderBottom: 1,
              borderColor: "divider",
              flexShrink: 0,
            }}
          >
            <Typography variant="subtitle2" fontWeight={600}>
              폼 빌더
            </Typography>
          </Box>
          <Box sx={{ flex: 1, overflow: "auto", p: 2 }}>
            <FormBuilder
              onSchemaChange={handleSchemaChange}
              onUiSchemaChange={handleUiSchemaChange}
              selectedFieldId={selectedFieldId}
              onFieldSelect={setSelectedFieldId}
            />
          </Box>
        </Paper>
      </Box>

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert 
          severity={snackbar.severity} 
          onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  )
}

export default FormPage
