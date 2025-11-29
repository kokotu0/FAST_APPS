import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { FormRegisterService } from "@/client"
import { OpenAPI } from "@/client/core/OpenAPI"
import {
  Box,
  Paper,
  Typography,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Stack,
  Card,
  CardContent,
  Grid,
  LinearProgress,
  Tabs,
  Tab,
  Divider,
} from "@mui/material"
import { 
  Visibility as ViewIcon, 
  Download as DownloadIcon,
  Email as EmailIcon,
  CheckCircle,
  Schedule,
  ErrorOutline,
  TableChart,
  BarChart,
} from "@mui/icons-material"
import Form from "@rjsf/mui"
import validator from "@rjsf/validator-ajv8"
import {
  ObjectFieldTemplate,
  customWidgets,
} from "@/features/formRegister/components/FormBuilder/components"
import type { FormPublishItem } from "@/features/formRegister/hooks/useFormRegister"

export const Route = createFileRoute("/_layout/form-register/responses")({
  component: FormResponsesPage,
})

// 폼 목록 아이템 타입
interface FormItem {
  idx: number
  uuid: string
  title: string
  category: string
}

// 폼 상세 데이터 타입
interface FormDetailData {
  idx: number
  uuid: string
  title: string
  description: string | null
  JSONSchema: Record<string, unknown>
  UISchema: Record<string, unknown>
  Theme: string
}

// 통계 응답 타입
interface StatsResponse {
  success: boolean
  message: string
  data: {
    form_uuid: string
    form_title: string
    publish_stats: {
      total: number
      submitted: number
      pending: number
      expired: number
      email_sent: number
      email_not_sent: number
      submission_rate: number
    }
    field_stats: Record<string, {
      title: string
      type: string
      is_enum: boolean
      total_responses: number
      value_counts?: Record<string, number>
      responses?: unknown[]
    }>
  }
}

function FormResponsesPage() {
  const [selectedFormUuid, setSelectedFormUuid] = useState<string>("")
  const [activeTab, setActiveTab] = useState(0)
  const [responseDialogOpen, setResponseDialogOpen] = useState(false)
  const [selectedResponse, setSelectedResponse] = useState<FormPublishItem | null>(null)

  // 폼 목록 조회
  const { data: formListDataRaw, isLoading: isFormListLoading } = useQuery({
    queryKey: ["forms", 1, 100],
    queryFn: () => FormRegisterService.getFormList({ page: 1, pageSize: 100 }),
  })
  const formListData = formListDataRaw as { items?: FormItem[] } | undefined

  // 선택한 폼의 상세 정보 (uuid 기반)
  const { data: formDetailDataRaw } = useQuery({
    queryKey: ["form", selectedFormUuid],
    queryFn: () => FormRegisterService.getForm({ formUuid: selectedFormUuid }),
    enabled: !!selectedFormUuid,
  })
  const formDetailData = formDetailDataRaw as { data?: FormDetailData } | undefined

  // 선택한 폼의 배포 목록 (응답 포함, uuid 기반)
  const { data: publishDataRaw, isLoading: isPublishLoading } = useQuery({
    queryKey: ["publishes", selectedFormUuid, 1, 100],
    queryFn: () => FormRegisterService.getFormPublishes({ 
      formUuid: selectedFormUuid, 
      page: 1, 
      pageSize: 100 
    }),
    enabled: !!selectedFormUuid,
  })
  const publishData = publishDataRaw as { items?: FormPublishItem[] } | undefined

  // 통계 조회
  const { data: statsDataRaw, isLoading: isStatsLoading } = useQuery({
    queryKey: ["form-stats", selectedFormUuid],
    queryFn: async () => {
      const response = await fetch(`${OpenAPI.BASE}/formRegister/${selectedFormUuid}/stats`, {
        headers: {
          'Authorization': `Bearer ${OpenAPI.TOKEN}`,
        },
      })
      return response.json()
    },
    enabled: !!selectedFormUuid,
  })
  const statsData = statsDataRaw as StatsResponse | undefined

  // 응답 보기
  const handleViewResponse = (item: FormPublishItem) => {
    setSelectedResponse(item)
    setResponseDialogOpen(true)
  }

  // CSV 다운로드
  const handleDownloadCSV = () => {
    if (!publishData?.items || !formDetailData?.data) return

    const submittedItems = publishData.items.filter((item) => item.is_submitted)
    if (submittedItems.length === 0) {
      alert("제출된 응답이 없습니다")
      return
    }

    // 스키마에서 필드 목록 추출
    const schema = formDetailData.data.JSONSchema as { properties?: Record<string, { title?: string }> }
    const properties = schema?.properties || {}
    const fieldNames = Object.keys(properties)

    // CSV 헤더
    const headers = ["수신자", "이름", "이메일발송", "제출일", ...fieldNames.map(f => properties[f]?.title || f)]
    
    // CSV 데이터
    const rows = submittedItems.map((item) => {
      const response = item.responseSchema || {}
      const rowData = [
        item.receiver,
        item.receiver_name || "",
        item.is_email_sent ? "Y" : "N",
        item.submitted_at ? new Date(item.submitted_at).toLocaleString() : "",
        ...fieldNames.map(field => {
          const value = (response as Record<string, unknown>)[field]
          if (Array.isArray(value)) return value.join(", ")
          if (typeof value === "object") return JSON.stringify(value)
          return value?.toString() || ""
        })
      ]
      return rowData.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(",")
    })

    const csvContent = [headers.join(","), ...rows].join("\n")
    const blob = new Blob(["\uFEFF" + csvContent], { type: "text/csv;charset=utf-8;" })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = `${formDetailData.data.title || "responses"}_${new Date().toISOString().split("T")[0]}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  const stats = statsData?.data?.publish_stats
  const fieldStats = statsData?.data?.field_stats

  return (
    <Box p={3}>
      <Typography variant="h5" fontWeight={600} gutterBottom>
        응답 결과
      </Typography>
      <Typography color="text.secondary" mb={3}>
        폼별 응답 결과를 조회하고 관리합니다.
      </Typography>

      {/* 폼 선택 */}
      <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
        <Stack direction="row" spacing={2} alignItems="center">
          <FormControl size="small" sx={{ minWidth: 300 }}>
            <InputLabel>폼 선택</InputLabel>
            <Select
              value={selectedFormUuid}
              label="폼 선택"
              onChange={(e) => setSelectedFormUuid(e.target.value)}
              disabled={isFormListLoading}
            >
              <MenuItem value="">선택하세요</MenuItem>
              {formListData?.items?.map((form) => (
                <MenuItem key={form.uuid} value={form.uuid}>
                  {form.title} ({form.category})
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {selectedFormUuid && stats && (
            <>
              <Chip 
                label={`응답률 ${stats.submission_rate}%`}
                color={stats.submission_rate > 50 ? "success" : stats.submission_rate > 20 ? "warning" : "default"}
              />
              <Button
                variant="outlined"
                startIcon={<DownloadIcon />}
                onClick={handleDownloadCSV}
                disabled={stats.submitted === 0}
              >
                CSV 다운로드
              </Button>
            </>
          )}
        </Stack>
      </Paper>

      {selectedFormUuid && (
        <>
          {/* 배포 현황 카드 */}
          {isStatsLoading ? (
            <Box display="flex" justifyContent="center" p={4}>
              <CircularProgress />
            </Box>
          ) : stats && (
            <Grid container spacing={2} mb={3}>
              <Grid size={{ xs: 12, sm: 6, md: 2 }}>
                <Card variant="outlined">
                  <CardContent sx={{ textAlign: "center", py: 2 }}>
                    <Typography variant="caption" color="text.secondary">전체 배포</Typography>
                    <Typography variant="h4" fontWeight={600}>{stats.total}</Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 2 }}>
                <Card variant="outlined" sx={{ borderColor: "success.main" }}>
                  <CardContent sx={{ textAlign: "center", py: 2 }}>
                    <Stack direction="row" alignItems="center" justifyContent="center" spacing={0.5}>
                      <CheckCircle color="success" fontSize="small" />
                      <Typography variant="caption" color="text.secondary">응답 완료</Typography>
                    </Stack>
                    <Typography variant="h4" fontWeight={600} color="success.main">{stats.submitted}</Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 2 }}>
                <Card variant="outlined" sx={{ borderColor: "info.main" }}>
                  <CardContent sx={{ textAlign: "center", py: 2 }}>
                    <Stack direction="row" alignItems="center" justifyContent="center" spacing={0.5}>
                      <Schedule color="info" fontSize="small" />
                      <Typography variant="caption" color="text.secondary">대기중</Typography>
                    </Stack>
                    <Typography variant="h4" fontWeight={600} color="info.main">{stats.pending}</Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 2 }}>
                <Card variant="outlined" sx={{ borderColor: "error.main" }}>
                  <CardContent sx={{ textAlign: "center", py: 2 }}>
                    <Stack direction="row" alignItems="center" justifyContent="center" spacing={0.5}>
                      <ErrorOutline color="error" fontSize="small" />
                      <Typography variant="caption" color="text.secondary">만료됨</Typography>
                    </Stack>
                    <Typography variant="h4" fontWeight={600} color="error.main">{stats.expired}</Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 2 }}>
                <Card variant="outlined" sx={{ borderColor: "primary.main" }}>
                  <CardContent sx={{ textAlign: "center", py: 2 }}>
                    <Stack direction="row" alignItems="center" justifyContent="center" spacing={0.5}>
                      <EmailIcon color="primary" fontSize="small" />
                      <Typography variant="caption" color="text.secondary">이메일 발송</Typography>
                    </Stack>
                    <Typography variant="h4" fontWeight={600} color="primary.main">{stats.email_sent}</Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 2 }}>
                <Card variant="outlined">
                  <CardContent sx={{ textAlign: "center", py: 2 }}>
                    <Typography variant="caption" color="text.secondary">미발송</Typography>
                    <Typography variant="h4" fontWeight={600}>{stats.email_not_sent}</Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          )}

          {/* 응답률 프로그레스 */}
          {stats && (
            <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
              <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                <Typography variant="body2">응답률</Typography>
                <Typography variant="body2" fontWeight={600}>{stats.submission_rate}%</Typography>
              </Box>
              <LinearProgress 
                variant="determinate" 
                value={stats.submission_rate} 
                sx={{ height: 10, borderRadius: 5 }}
              />
            </Paper>
          )}

          {/* 탭 네비게이션 */}
          <Paper variant="outlined" sx={{ mb: 0 }}>
            <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)}>
              <Tab icon={<BarChart />} iconPosition="start" label="질문별 통계" />
              <Tab icon={<TableChart />} iconPosition="start" label="개별 응답" />
            </Tabs>
          </Paper>

          {/* 탭 내용 */}
          <Paper variant="outlined" sx={{ borderTop: 0, borderTopLeftRadius: 0, borderTopRightRadius: 0 }}>
            {activeTab === 0 && (
              /* 질문별 통계 */
              <Box p={2}>
                {isStatsLoading ? (
                  <Box display="flex" justifyContent="center" p={4}>
                    <CircularProgress />
                  </Box>
                ) : fieldStats && Object.keys(fieldStats).length > 0 ? (
                  <Stack spacing={3}>
                    {Object.entries(fieldStats).map(([fieldKey, fieldData]) => (
                      <Box key={fieldKey}>
                        <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                          {fieldData.title}
                        </Typography>
                        <Typography variant="caption" color="text.secondary" display="block" mb={1}>
                          총 {fieldData.total_responses}개 응답
                        </Typography>
                        
                        {fieldData.is_enum && fieldData.value_counts ? (
                          /* 선택형 질문: 막대 그래프 스타일 */
                          <Stack spacing={1}>
                            {Object.entries(fieldData.value_counts)
                              .sort(([, a], [, b]) => b - a)
                              .map(([value, count]) => {
                                const percentage = fieldData.total_responses > 0 
                                  ? Math.round((count / fieldData.total_responses) * 100) 
                                  : 0
                                return (
                                  <Box key={value}>
                                    <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
                                      <Typography variant="body2">{value}</Typography>
                                      <Typography variant="body2" fontWeight={600}>
                                        {count}명 ({percentage}%)
                                      </Typography>
                                    </Box>
                                    <LinearProgress 
                                      variant="determinate" 
                                      value={percentage}
                                      sx={{ height: 8, borderRadius: 4 }}
                                    />
                                  </Box>
                                )
                              })}
                          </Stack>
                        ) : (
                          /* 자유 입력 질문: 응답 목록 */
                          <Box sx={{ maxHeight: 200, overflow: "auto" }}>
                            <Stack spacing={0.5}>
                              {fieldData.responses?.slice(0, 20).map((resp, idx) => (
                                <Chip 
                                  key={idx} 
                                  label={String(resp)} 
                                  size="small" 
                                  variant="outlined"
                                  sx={{ justifyContent: "flex-start" }}
                                />
                              ))}
                              {fieldData.responses && fieldData.responses.length > 20 && (
                                <Typography variant="caption" color="text.secondary">
                                  외 {fieldData.responses.length - 20}개...
                                </Typography>
                              )}
                            </Stack>
                          </Box>
                        )}
                        <Divider sx={{ mt: 2 }} />
                      </Box>
                    ))}
                  </Stack>
                ) : (
                  <Typography color="text.secondary" textAlign="center" py={4}>
                    응답 데이터가 없습니다
                  </Typography>
                )}
              </Box>
            )}

            {activeTab === 1 && (
              /* 개별 응답 테이블 */
              <>
                {isPublishLoading ? (
                  <Box display="flex" justifyContent="center" p={4}>
                    <CircularProgress />
                  </Box>
                ) : publishData?.items && publishData.items.length > 0 ? (
                  <TableContainer>
                    <Table>
                      <TableHead>
                        <TableRow>
                          <TableCell>수신자</TableCell>
                          <TableCell>이름</TableCell>
                          <TableCell>이메일</TableCell>
                          <TableCell>상태</TableCell>
                          <TableCell>제출일</TableCell>
                          <TableCell>만료일</TableCell>
                          <TableCell align="right">액션</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {publishData.items.map((item) => (
                          <TableRow key={item.idx}>
                            <TableCell>{item.receiver}</TableCell>
                            <TableCell>{item.receiver_name || "-"}</TableCell>
                            <TableCell>
                              {item.is_email_sent ? (
                                <Tooltip title={`발송: ${item.email_sent_at ? new Date(item.email_sent_at).toLocaleString() : "-"} (${item.email_sent_count}회)`}>
                                  <Chip
                                    size="small"
                                    icon={<EmailIcon />}
                                    label="발송됨"
                                    color="primary"
                                    variant="outlined"
                                  />
                                </Tooltip>
                              ) : (
                                <Chip
                                  size="small"
                                  label="미발송"
                                  variant="outlined"
                                />
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
                              {item.submitted_at 
                                ? new Date(item.submitted_at).toLocaleString() 
                                : "-"
                              }
                            </TableCell>
                            <TableCell>
                              <Typography 
                                variant="body2"
                                color={new Date(item.expired_at) < new Date() ? "error" : "textPrimary"}
                              >
                                {new Date(item.expired_at).toLocaleDateString()}
                              </Typography>
                            </TableCell>
                            <TableCell align="right">
                              {item.is_submitted && (
                                <Tooltip title="응답 보기">
                                  <IconButton
                                    color="primary"
                                    onClick={() => handleViewResponse(item)}
                                  >
                                    <ViewIcon />
                                  </IconButton>
                                </Tooltip>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                ) : (
                  <Box p={4} textAlign="center">
                    <Typography color="text.secondary">
                      배포된 대상이 없습니다
                    </Typography>
                  </Box>
                )}
              </>
            )}
          </Paper>
        </>
      )}

      {!selectedFormUuid && (
        <Paper variant="outlined" sx={{ p: 4, textAlign: "center" }}>
          <Typography color="text.secondary">
            폼을 선택해주세요
          </Typography>
        </Paper>
      )}

      {/* 응답 상세 다이얼로그 */}
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
          {selectedResponse && formDetailData?.data && (
            <Box sx={{ mt: 1 }}>
              <Stack direction="row" spacing={2} mb={2}>
                <Chip 
                  size="small" 
                  label={`제출일: ${selectedResponse.submitted_at ? new Date(selectedResponse.submitted_at).toLocaleString() : "-"}`}
                />
                {selectedResponse.is_email_sent && (
                  <Chip 
                    size="small" 
                    icon={<EmailIcon />}
                    label={`이메일 발송: ${selectedResponse.email_sent_at ? new Date(selectedResponse.email_sent_at).toLocaleString() : "-"}`}
                    color="primary"
                    variant="outlined"
                  />
                )}
              </Stack>
              <Form
                schema={formDetailData.data.JSONSchema || {}}
                uiSchema={{
                  ...(formDetailData.data.UISchema || {}),
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
    </Box>
  )
}
