import { FormBuilder } from "@/features/formRegister/components/FormBuilder/FormBulider"
import {
  ObjectFieldTemplate,
  SubmitButton,
  customWidgets,
} from "@/features/formRegister/components/FormBuilder/components"
import FormJSON from "@/features/formRegister/components/FormJSON"
import { useFormRegister, type FormPublishItem } from "@/features/formRegister/hooks/useFormRegister"
import {
  type FormRegisterCreateFormData,
  type FormRegisterUpdateFormData,
} from "@/client"
import { OpenAPI } from "@/client/core/OpenAPI"
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
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tooltip,
  Autocomplete,
  RadioGroup,
  FormControlLabel,
  Radio,
  FormLabel,
} from "@mui/material"
import { 
  Save as SaveIcon, 
  Add as AddIcon, 
  Delete as DeleteIcon, 
  ContentCopy as CopyIcon,
  Launch as LaunchIcon,
  Visibility as ViewIcon,
  Email as EmailIcon,
} from "@mui/icons-material"
import { useState, useCallback, useEffect, useMemo } from "react"
import type { RJSFSchema, UiSchema } from "@rjsf/utils"
import type { IChangeEvent } from "@rjsf/core"
import Form from "@rjsf/mui"
import validator from "@rjsf/validator-ajv8"
import { nanoid } from "nanoid"
import { useNavigate } from "@tanstack/react-router"
import { useMailSend } from "@/features/mail-send"

interface FormPageProps {
  uuid?: string  // "new" 또는 실제 uuid
}

// Form 데이터 타입 정의
interface FormData {
  idx: number
  uuid: string
  category: string
  title: string
  description: string | null
  JSONSchema: Record<string, unknown>
  UISchema: Record<string, unknown>
  Theme: string
  useYN: boolean
  publish_status: PublishStatus
  publish_start_at: string | null
  publish_end_at: string | null
  max_responses: number | null
  allow_anonymous: boolean
  require_login: boolean
  created_at: string
  updated_at: string
}

type PublishStatus = "draft" | "scheduled" | "published" | "closed"
type ReceiverType = "email" | "phone"

// 날짜를 datetime-local input 형식으로 변환
const formatDatetimeLocal = (date: Date) => {
  const pad = (n: number) => n.toString().padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

// 기본 시작일: 오늘
const getDefaultStartDate = () => formatDatetimeLocal(new Date())

// 기본 종료일: 일주일 후
const getDefaultEndDate = () => {
  const date = new Date()
  date.setDate(date.getDate() + 7)
  return formatDatetimeLocal(date)
}

function FormPage({ uuid }: FormPageProps) {
  const navigate = useNavigate()
  const isNew = !uuid || uuid === "new"
  
  // 훅 가져오기
  const { 
    useFormDetail, 
    useFormList,
    createMutation, 
    updateMutation,
    usePublishList,
    createPublishMutation,
    deletePublishMutation,
  } = useFormRegister()
  const { data: formData, isLoading } = useFormDetail(uuid)
  const { data: formListData } = useFormList(1, 100)  // 카테고리 목록용
  
  // 폼 데이터 캐스팅
  const form = formData?.data as FormData | undefined
  
  // 폼의 uuid 사용
  const formUuid = form?.uuid || uuid
  const { data: publishDataRaw, isLoading: isPublishLoading } = usePublishList(formUuid)
  
  // 배포 데이터 타입 캐스팅
  const publishData = publishDataRaw as { items?: FormPublishItem[]; total?: number } | undefined
  
  // 기존 카테고리 목록 추출
  const existingCategories = useMemo(() => {
    if (!formListData?.items) return []
    const categories = new Set<string>()
    formListData.items.forEach((item: any) => {
      if (item.category) categories.add(item.category)
    })
    return Array.from(categories)
  }, [formListData])
  
  // 폼 메타 정보
  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")
  const [category, setCategory] = useState("default")
  
  // 배포 메타데이터 (기본값 설정)
  const [publishStatus, setPublishStatus] = useState<PublishStatus>("draft")
  const [publishStartAt, setPublishStartAt] = useState(getDefaultStartDate())
  const [publishEndAt, setPublishEndAt] = useState(getDefaultEndDate())
  
  // 스키마 상태
  const [schema, setSchema] = useState<RJSFSchema>({})
  const [uiSchema, setUiSchema] = useState<UiSchema>({})
  const [previewData, setPreviewData] = useState<unknown>({})
  
  // UI 상태
  const [selectedFieldId, setSelectedFieldId] = useState<string | null>(null)
  const [leftTab, setLeftTab] = useState(0)  // 왼쪽: 미리보기/스키마
  const [rightTab, setRightTab] = useState(0)  // 오른쪽: 폼빌더/메타데이터
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: "success" | "error" | "info" }>({
    open: false,
    message: "",
    severity: "success",
  })
  
  // 배포 추가 다이얼로그
  const [publishDialogOpen, setPublishDialogOpen] = useState(false)
  const [receiverType, setReceiverType] = useState<ReceiverType>("email")
  const [newReceiver, setNewReceiver] = useState("")
  const [newReceiverName, setNewReceiverName] = useState("")
  
  // 응답 보기 다이얼로그
  const [responseDialogOpen, setResponseDialogOpen] = useState(false)
  const [selectedResponse, setSelectedResponse] = useState<FormPublishItem | null>(null)

  // 기존 데이터 로드
  useEffect(() => {
    if (form) {
      setTitle(form.title || "")
      setDescription(form.description || "")
      setCategory(form.category || "default")
      setSchema(form.JSONSchema || {})
      setUiSchema(form.UISchema || {})
      // 배포 메타데이터
      setPublishStatus(form.publish_status || "draft")
      const startAt = form.publish_start_at
      const endAt = form.publish_end_at
      if (startAt) setPublishStartAt(startAt.slice(0, 16))  // datetime-local 형식
      if (endAt) setPublishEndAt(endAt.slice(0, 16))
    }
  }, [form])

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
          publish_status: publishStatus,
          publish_start_at: publishStartAt || null,
          publish_end_at: publishEndAt || null,
        } as any
        
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

  // 배포 종료일까지 남은 일수 계산
  const getExpiredDays = () => {
    if (!publishEndAt) return 7
    const endDate = new Date(publishEndAt)
    const today = new Date()
    const diffTime = endDate.getTime() - today.getTime()
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
    return Math.max(1, diffDays)
  }

  // 배포 추가
  const handleAddPublish = async () => {
    if (!newReceiver.trim()) {
      setSnackbar({ open: true, message: "수신자를 입력해주세요", severity: "error" })
      return
    }
    
    // 이메일 형식 검증
    if (receiverType === "email" && !newReceiver.includes("@")) {
      setSnackbar({ open: true, message: "올바른 이메일 형식을 입력해주세요", severity: "error" })
      return
    }
    
    if (!formUuid || formUuid === "new") {
      setSnackbar({ open: true, message: "폼을 먼저 저장해주세요", severity: "error" })
      return
    }
    
    try {
      await createPublishMutation.mutateAsync({
        formUuid,
        data: {
          receiver: newReceiver,
          receiver_name: newReceiverName || undefined,
          expired_days: getExpiredDays(),
        },
      })
      setSnackbar({ open: true, message: "배포 대상이 추가되었습니다", severity: "success" })
      setPublishDialogOpen(false)
      setNewReceiver("")
      setNewReceiverName("")
    } catch (error) {
      setSnackbar({ 
        open: true, 
        message: "배포 추가 실패", 
        severity: "error" 
      })
    }
  }

  // 배포 삭제
  const handleDeletePublish = async (publishIdx: number) => {
    if (!formUuid || formUuid === "new") return
    try {
      await deletePublishMutation.mutateAsync({ formUuid, publishIdx })
      setSnackbar({ open: true, message: "배포가 삭제되었습니다", severity: "success" })
    } catch (error) {
      setSnackbar({ open: true, message: "삭제 실패", severity: "error" })
    }
  }

  // URL 복사
  const handleCopyUrl = (token: string) => {
    const url = `${window.location.origin}/p/${token}`
    navigator.clipboard.writeText(url)
    setSnackbar({ open: true, message: "URL이 복사되었습니다", severity: "success" })
  }

  // URL 열기
  const handleOpenUrl = (token: string) => {
    const url = `${window.location.origin}/p/${token}`
    window.open(url, "_blank")
  }

  // 응답 보기
  const handleViewResponse = (item: FormPublishItem) => {
    setSelectedResponse(item)
    setResponseDialogOpen(true)
  }

  // 이메일 발송 훅
  const { sendFormSurveyEmail, sendFormSurveyEmailsBatch, isSendingBatch } = useMailSend()

  // 이메일 발송 상태 업데이트
  const updateEmailSentStatus = async (publishIdx: number) => {
    if (!formUuid) return
    try {
      await fetch(`${OpenAPI.BASE}/formRegister/${formUuid}/publish/${publishIdx}/email-sent`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${OpenAPI.TOKEN}`,
        },
      })
    } catch (error) {
      console.error("Failed to update email sent status:", error)
    }
  }

  // 이메일 배포 (단일)
  const handleSendEmail = async (item: FormPublishItem) => {
    if (!item.receiver.includes("@")) {
      setSnackbar({ open: true, message: "이메일 주소가 아닙니다", severity: "error" })
      return
    }
    
    try {
      await sendFormSurveyEmail({
        receiverEmail: item.receiver,
        receiverName: item.receiver_name || undefined,
        formTitle: title,
        formDescription: description || undefined,
        formUrl: `${window.location.origin}/p/${item.token}`,
        expiredAt: item.expired_at,
      })
      // 이메일 발송 상태 업데이트
      await updateEmailSentStatus(item.idx)
      setSnackbar({ open: true, message: "이메일이 발송되었습니다", severity: "success" })
    } catch (error) {
      console.error("Email send error:", error)
      setSnackbar({ open: true, message: "이메일 발송 실패", severity: "error" })
    }
  }

  // 전체 이메일 배포
  const handleSendAllEmails = async () => {
    const emailItems = publishData?.items?.filter(
      (item: FormPublishItem) => item.receiver.includes("@") && !item.is_submitted
    )
    if (!emailItems?.length) {
      setSnackbar({ open: true, message: "전송할 이메일 대상이 없습니다", severity: "error" })
      return
    }

    try {
      const result = await sendFormSurveyEmailsBatch(
        emailItems.map((item: FormPublishItem) => ({
          receiverEmail: item.receiver,
          receiverName: item.receiver_name || undefined,
          formTitle: title,
          formDescription: description || undefined,
          formUrl: `${window.location.origin}/p/${item.token}`,
          expiredAt: item.expired_at,
        }))
      )
      
      // 성공한 이메일들의 발송 상태 업데이트
      for (const item of emailItems) {
        await updateEmailSentStatus(item.idx)
      }
      
      if (result.failed > 0) {
        setSnackbar({ 
          open: true, 
          message: `${result.succeeded}명 발송 성공, ${result.failed}명 발송 실패`, 
          severity: "info" 
        })
      } else {
        setSnackbar({ 
          open: true, 
          message: `${result.succeeded}명에게 이메일을 발송했습니다`, 
          severity: "success" 
        })
      }
    } catch (error) {
      console.error("Batch email send error:", error)
      setSnackbar({ open: true, message: "이메일 발송 실패", severity: "error" })
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
    <Box 
      display="flex" 
      flexDirection="column" 
      width="100%"
      height="calc(100vh - 64px)" 
      p={2} 
      gap={2}
      mx="auto"
    >
      {/* 상단: 저장 버튼만 */}
      <Paper variant="outlined" sx={{ p: 2, flexShrink: 0 }}>
        <Stack direction="row" spacing={2} alignItems="center" justifyContent="space-between">
          <Typography variant="h6" fontWeight={600}>
            {isNew ? "새 폼 생성" : (title || "폼 수정")}
          </Typography>
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
            value={leftTab}
            onChange={(_, v: number) => setLeftTab(v)}
            sx={{ borderBottom: 1, borderColor: "divider", flexShrink: 0 }}
          >
            <Tab label="폼 미리보기" />
            <Tab label="스키마 뷰어" />
          </Tabs>

          <Box sx={{ flex: 1, overflow: "auto", p: 2 }}>
            {leftTab === 0 && (
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
            {leftTab === 1 && (
              <FormJSON 
                schema={schema} 
                uiSchema={uiSchema} 
                formData={previewData}
              />
            )}
          </Box>
        </Paper>

        {/* 오른쪽: 폼 빌더 / 메타데이터 & 배포 (탭) */}
        <Paper
          variant="outlined"
          sx={{ display: "flex", flexDirection: "column", overflow: "hidden" }}
        >
          <Tabs
            value={rightTab}
            onChange={(_, v: number) => setRightTab(v)}
            sx={{ borderBottom: 1, borderColor: "divider", flexShrink: 0 }}
          >
            <Tab label="폼 빌더" />
            <Tab label="메타데이터 & 배포" />
          </Tabs>

          <Box sx={{ flex: 1, overflow: "auto", p: 2 }}>
            {rightTab === 0 && (
              <FormBuilder
                onSchemaChange={handleSchemaChange}
                onUiSchemaChange={handleUiSchemaChange}
                selectedFieldId={selectedFieldId}
                onFieldSelect={setSelectedFieldId}
                initialSchema={form?.JSONSchema}
                initialUiSchema={form?.UISchema}
              />
            )}
            {rightTab === 1 && (
              <Box>
                {/* 기본 정보 섹션 */}
                <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                  기본 정보
                </Typography>
                <Stack spacing={2} mb={3}>
                  <TextField
                    size="small"
                    label="제목"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    fullWidth
                    required
                  />
                  <TextField
                    size="small"
                    label="설명"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    fullWidth
                    multiline
                    rows={2}
                  />
                  <Autocomplete
                    freeSolo
                    size="small"
                    options={existingCategories}
                    value={category}
                    onChange={(_, newValue) => setCategory(newValue || "")}
                    onInputChange={(_, newValue) => setCategory(newValue)}
                    renderInput={(params) => (
                      <TextField {...params} label="카테고리" placeholder="기존 카테고리 선택 또는 새로 입력" />
                    )}
                  />
                </Stack>

                <Divider sx={{ my: 2 }} />

                {/* 배포 설정 섹션 */}
                <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                  배포 설정
                </Typography>
                <Stack spacing={2} mb={3}>
                  <FormControl size="small" fullWidth>
                    <InputLabel>배포 상태</InputLabel>
                    <Select
                      value={publishStatus}
                      label="배포 상태"
                      onChange={(e) => setPublishStatus(e.target.value as PublishStatus)}
                    >
                      <MenuItem value="draft">초안 (미배포)</MenuItem>
                      <MenuItem value="scheduled">예약됨</MenuItem>
                      <MenuItem value="published">배포됨</MenuItem>
                      <MenuItem value="closed">종료됨</MenuItem>
                    </Select>
                  </FormControl>
                  
                  <Stack direction="row" spacing={2}>
                    <TextField
                      size="small"
                      label="배포 시작일"
                      type="datetime-local"
                      value={publishStartAt}
                      onChange={(e) => setPublishStartAt(e.target.value)}
                      InputLabelProps={{ shrink: true }}
                      fullWidth
                    />
                    <TextField
                      size="small"
                      label="배포 종료일"
                      type="datetime-local"
                      value={publishEndAt}
                      onChange={(e) => setPublishEndAt(e.target.value)}
                      InputLabelProps={{ shrink: true }}
                      fullWidth
                    />
                  </Stack>
                </Stack>

                <Divider sx={{ my: 2 }} />

                {/* 배포 대상 목록 */}
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                  <Typography variant="subtitle1" fontWeight={600}>
                    배포 대상 목록
                  </Typography>
                  <Stack direction="row" spacing={1}>
                    <Button
                      size="small"
                      variant="outlined"
                      color="primary"
                      startIcon={isSendingBatch ? <CircularProgress size={16} /> : <EmailIcon />}
                      onClick={handleSendAllEmails}
                      disabled={isNew || !publishData?.items?.length || isSendingBatch}
                    >
                      {isSendingBatch ? "발송 중..." : "전체 이메일 발송"}
                    </Button>
                    <Button
                      size="small"
                      variant="outlined"
                      startIcon={<AddIcon />}
                      onClick={() => setPublishDialogOpen(true)}
                      disabled={isNew}
                    >
                      대상 추가
                    </Button>
                  </Stack>
                </Box>

                {isNew ? (
                  <Typography color="text.secondary" textAlign="center" py={2}>
                    폼을 먼저 저장해주세요
                  </Typography>
                ) : isPublishLoading ? (
                  <Box display="flex" justifyContent="center" p={2}>
                    <CircularProgress size={24} />
                  </Box>
                ) : publishData?.items && publishData.items.length > 0 ? (
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>수신자</TableCell>
                          <TableCell>이름</TableCell>
                          <TableCell>이메일</TableCell>
                          <TableCell>상태</TableCell>
                          <TableCell>만료일</TableCell>
                          <TableCell align="right">액션</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {publishData.items.map((item: FormPublishItem) => (
                          <TableRow key={item.idx}>
                            <TableCell>{item.receiver}</TableCell>
                            <TableCell>{item.receiver_name || "-"}</TableCell>
                            <TableCell>
                              {item.is_email_sent ? (
                                <Tooltip title={`발송: ${item.email_sent_at ? new Date(item.email_sent_at).toLocaleString() : "-"} (${item.email_sent_count || 0}회)`}>
                                  <Chip
                                    size="small"
                                    icon={<EmailIcon />}
                                    label="발송됨"
                                    color="primary"
                                    variant="outlined"
                                  />
                                </Tooltip>
                              ) : (
                                <Chip size="small" label="미발송" variant="outlined" />
                              )}
                            </TableCell>
                            <TableCell>
                              <Chip
                                size="small"
                                label={item.is_submitted ? "제출됨" : "대기중"}
                                color={item.is_submitted ? "success" : "default"}
                              />
                            </TableCell>
                            <TableCell>
                              {new Date(item.expired_at).toLocaleDateString()}
                            </TableCell>
                            <TableCell align="right">
                              {item.is_submitted && (
                                <Tooltip title="응답 보기">
                                  <IconButton
                                    size="small"
                                    color="primary"
                                    onClick={() => handleViewResponse(item)}
                                  >
                                    <ViewIcon fontSize="small" />
                                  </IconButton>
                                </Tooltip>
                              )}
                              {!item.is_submitted && item.receiver.includes("@") && (
                                <Tooltip title="이메일 발송">
                                  <IconButton
                                    size="small"
                                    color="primary"
                                    onClick={() => handleSendEmail(item)}
                                  >
                                    <EmailIcon fontSize="small" />
                                  </IconButton>
                                </Tooltip>
                              )}
                              <Tooltip title="URL 복사">
                                <IconButton
                                  size="small"
                                  onClick={() => handleCopyUrl(item.token)}
                                >
                                  <CopyIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                              <Tooltip title="열기">
                                <IconButton
                                  size="small"
                                  onClick={() => handleOpenUrl(item.token)}
                                >
                                  <LaunchIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                              <Tooltip title="삭제">
                                <IconButton
                                  size="small"
                                  color="error"
                                  onClick={() => handleDeletePublish(item.idx)}
                                >
                                  <DeleteIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                ) : (
                  <Typography color="text.secondary" textAlign="center" py={2}>
                    배포 대상이 없습니다
                  </Typography>
                )}
              </Box>
            )}
          </Box>
        </Paper>
      </Box>

      {/* 배포 추가 다이얼로그 */}
      <Dialog open={publishDialogOpen} onClose={() => setPublishDialogOpen(false)}>
        <DialogTitle>배포 대상 추가</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1, minWidth: 350 }}>
            <FormControl>
              <FormLabel>수신자 유형</FormLabel>
              <RadioGroup
                row
                value={receiverType}
                onChange={(e) => setReceiverType(e.target.value as ReceiverType)}
              >
                <FormControlLabel value="email" control={<Radio size="small" />} label="이메일" />
                <FormControlLabel value="phone" control={<Radio size="small" />} label="전화번호" />
              </RadioGroup>
            </FormControl>
            <TextField
              label={receiverType === "email" ? "이메일 주소" : "전화번호"}
              value={newReceiver}
              onChange={(e) => setNewReceiver(e.target.value)}
              fullWidth
              required
              placeholder={receiverType === "email" ? "example@email.com" : "010-1234-5678"}
            />
            <TextField
              label="수신자 이름 (선택)"
              value={newReceiverName}
              onChange={(e) => setNewReceiverName(e.target.value)}
              fullWidth
            />
            <Alert severity="info" sx={{ mt: 1 }}>
              만료일: {publishEndAt ? new Date(publishEndAt).toLocaleDateString() : "배포 종료일 미설정"} 
              (배포 종료일 기준)
            </Alert>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPublishDialogOpen(false)}>취소</Button>
          <Button 
            variant="contained" 
            onClick={handleAddPublish}
            disabled={createPublishMutation.isPending}
          >
            추가
          </Button>
        </DialogActions>
      </Dialog>

      {/* 응답 보기 다이얼로그 */}
      <Dialog 
        open={responseDialogOpen} 
        onClose={() => setResponseDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          응답 내용 - {selectedResponse?.receiver_name || selectedResponse?.receiver}
        </DialogTitle>
        <DialogContent>
          {selectedResponse && (
            <Box sx={{ mt: 1 }}>
              <Typography variant="body2" color="text.secondary" mb={2}>
                제출일: {selectedResponse.submitted_at 
                  ? new Date(selectedResponse.submitted_at).toLocaleString() 
                  : "-"
                }
              </Typography>
              <Form
                schema={schema}
                uiSchema={{
                  ...uiSchema,
                  "ui:readonly": true,
                }}
                formData={selectedResponse.responseSchema}
                validator={validator}
                templates={{ ObjectFieldTemplate }}
                widgets={customWidgets}
              >
                <Box /> {/* 빈 children으로 제출 버튼 숨김 */}
              </Form>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResponseDialogOpen(false)}>닫기</Button>
        </DialogActions>
      </Dialog>

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
