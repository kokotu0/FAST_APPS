import { createFileRoute } from "@tanstack/react-router"
import { useState, useCallback, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { OpenAPI } from "@/client/core/OpenAPI"
import { request as __request } from "@/client/core/request"
import {
  Box,
  Paper,
  Typography,
  CircularProgress,
  Alert,
  Button,
  Container,
  Snackbar,
} from "@mui/material"
import { Send as SendIcon, Edit as EditIcon } from "@mui/icons-material"
import Form from "@rjsf/mui"
import validator from "@rjsf/validator-ajv8"
import type { IChangeEvent } from "@rjsf/core"
import {
  ObjectFieldTemplate,
  customWidgets,
} from "@/features/formRegister/components/FormBuilder/components"

export const Route = createFileRoute("/p/$token")({
  component: PublicFormPage,
})

interface PublicFormData {
  title: string
  description: string | null
  JSONSchema: Record<string, unknown>
  UISchema: Record<string, unknown>
  Theme: string
  receiver_name: string | null
  is_submitted: boolean
  expired_at: string
  responseSchema: Record<string, unknown>  // 이전 응답 데이터
}

function PublicFormPage() {
  const { token } = Route.useParams()
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState<unknown>({})
  const [isEditing, setIsEditing] = useState(false)
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: "success" | "error" | "info" }>({
    open: false,
    message: "",
    severity: "success",
  })

  // 폼 데이터 조회
  const { data, isLoading, error } = useQuery({
    queryKey: ["public-form", token],
    queryFn: async () => {
      const response = await __request(OpenAPI, {
        method: "GET",
        url: `/formRegister/public/${token}`,
      }) as { success: boolean; data: PublicFormData }
      return response.data
    },
  })

  // 이전 응답 데이터 로드
  useEffect(() => {
    if (data?.responseSchema && Object.keys(data.responseSchema).length > 0) {
      setFormData(data.responseSchema)
    }
  }, [data])

  // 폼 제출/수정
  const submitMutation = useMutation({
    mutationFn: async (responseData: Record<string, unknown>) => {
      return await __request(OpenAPI, {
        method: "POST",
        url: `/formRegister/public/${token}/submit`,
        body: { responseData },
        mediaType: "application/json",
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["public-form", token] })
      setIsEditing(false)
      setSnackbar({ 
        open: true, 
        message: data?.is_submitted ? "응답이 수정되었습니다" : "제출이 완료되었습니다", 
        severity: "success" 
      })
    },
    onError: (error: any) => {
      const message = error?.body?.detail || "제출 중 오류가 발생했습니다"
      setSnackbar({ open: true, message, severity: "error" })
    },
  })

  // 폼 데이터 변경
  const handleFormChange = useCallback((e: IChangeEvent) => {
    setFormData(e.formData)
  }, [])

  // 폼 제출
  const handleSubmit = useCallback((e: IChangeEvent) => {
    submitMutation.mutate(e.formData as Record<string, unknown>)
  }, [submitMutation])

  // 수정 모드 전환
  const handleEdit = () => {
    setIsEditing(true)
  }

  // 로딩 중
  if (isLoading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="100vh"
        bgcolor="#f5f5f5"
      >
        <CircularProgress />
      </Box>
    )
  }

  // 에러
  if (error) {
    const errorMessage = (error as any)?.body?.detail || "폼을 불러올 수 없습니다"
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="100vh"
        bgcolor="#f5f5f5"
      >
        <Paper sx={{ p: 4, maxWidth: 400, textAlign: "center" }}>
          <Typography variant="h6" color="error" gutterBottom>
            오류
          </Typography>
          <Typography color="text.secondary">
            {errorMessage}
          </Typography>
        </Paper>
      </Box>
    )
  }

  // 이미 제출했고 수정 모드가 아닌 경우 - 결과 표시
  const showSubmittedView = data?.is_submitted && !isEditing

  return (
    <Box minHeight="100vh" bgcolor="#f5f5f5" py={4}>
      <Container maxWidth="lg">
        <Paper sx={{ p: 4,  mx: "auto" }}>
          {/* 헤더 */}
          <Box mb={4}>
            <Typography variant="h4" fontWeight={600} gutterBottom>
              {data?.title}
            </Typography>
            {data?.description && (
              <Typography color="text.secondary">
                {data.description}
              </Typography>
            )}
            {data?.receiver_name && (
              <Typography variant="body2" color="primary" mt={1}>
                {data.receiver_name}님을 위한 폼입니다
              </Typography>
            )}
          </Box>

          {/* 상태 안내 */}
          {showSubmittedView ? (
            <Alert severity="success" sx={{ mb: 3 }} action={
              <Button color="inherit" size="small" startIcon={<EditIcon />} onClick={handleEdit}>
                수정하기
              </Button>
            }>
              응답이 제출되었습니다. {new Date(data?.expired_at || "").toLocaleDateString()}까지 수정 가능합니다.
            </Alert>
          ) : (
            <Alert severity="info" sx={{ mb: 3 }}>
              {data?.is_submitted 
                ? `수정 중입니다. ${new Date(data?.expired_at || "").toLocaleDateString()}까지 수정 가능합니다.`
                : `이 폼은 ${new Date(data?.expired_at || "").toLocaleDateString()}까지 유효합니다`
              }
            </Alert>
          )}

          {/* 제출된 응답 보기 (수정 모드 아닐 때) */}
          {showSubmittedView ? (
            <Box>
              <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
                제출된 응답
              </Typography>
              <Form
                schema={data?.JSONSchema || {}}
                uiSchema={{
                  ...data?.UISchema,
                  "ui:readonly": true,
                }}
                formData={formData}
                validator={validator}
                templates={{ ObjectFieldTemplate }}
                widgets={customWidgets}
              >
                <Box /> {/* 빈 children으로 제출 버튼 숨김 */}
              </Form>
            </Box>
          ) : (
            /* 폼 입력/수정 */
            <Form
              schema={data?.JSONSchema || {}}
              uiSchema={data?.UISchema || {}}
              formData={formData}
              validator={validator}
              onChange={handleFormChange}
              onSubmit={handleSubmit}
              templates={{
                ObjectFieldTemplate,
                ButtonTemplates: { 
                  SubmitButton: () => (
                    <Box mt={3} display="flex" gap={2}>
                      {isEditing && (
                        <Button
                          variant="outlined"
                          size="large"
                          onClick={() => setIsEditing(false)}
                          sx={{ flex: 1 }}
                        >
                          취소
                        </Button>
                      )}
                      <Button
                        type="submit"
                        variant="contained"
                        size="large"
                        sx={{ flex: isEditing ? 1 : undefined }}
                        fullWidth={!isEditing}
                        startIcon={submitMutation.isPending ? <CircularProgress size={20} color="inherit" /> : <SendIcon />}
                        disabled={submitMutation.isPending}
                      >
                        {submitMutation.isPending 
                          ? "저장 중..." 
                          : (isEditing ? "수정 완료" : "제출하기")
                        }
                      </Button>
                    </Box>
                  ),
                },
              }}
              widgets={customWidgets}
            />
          )}
        </Paper>
      </Container>

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
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
