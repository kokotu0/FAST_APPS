import { useMemo, useState } from "react";
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
  type MRT_PaginationState,
} from "material-react-table";
import { 
  Box, 
  Button, 
  IconButton, 
  Tooltip, 
  Chip, 
  Typography,
  Stack,
  CircularProgress,
  LinearProgress,
} from "@mui/material";
import { 
  Visibility, 
  Edit, 
  Add, 
  Schedule,
  CheckCircle,
  Block,
  Drafts,
} from "@mui/icons-material";
import { useNavigate } from "@tanstack/react-router";
import { useFormRegister, type FormPublishItem } from "../hooks/useFormRegister";
import { FormRegisterService } from "@/client";
import { useQuery } from "@tanstack/react-query";

// 배포 상태 타입
type PublishStatus = "draft" | "scheduled" | "published" | "closed";

// 폼 아이템 타입 정의
interface FormItem {
  idx: number;
  uuid: string;
  category: string;
  title: string;
  description: string | null;
  JSONSchema: Record<string, unknown>;
  UISchema: Record<string, unknown>;
  Theme: string;
  useYN: boolean;
  publish_status: PublishStatus;
  publish_start_at: string | null;
  publish_end_at: string | null;
  max_responses: number | null;
  allow_anonymous: boolean;
  require_login: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export default function FormListPage() {
  const navigate = useNavigate();
  const { useFormList } = useFormRegister();
  const [pagination, setPagination] = useState<MRT_PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  });

  const { data, isLoading, isError } = useFormList(
    pagination.pageIndex + 1,
    pagination.pageSize
  );

  // 배포 상태별 설정
  const statusConfig: Record<PublishStatus, { label: string; color: "default" | "warning" | "success" | "error"; icon: React.ReactNode }> = {
    draft: { label: "초안", color: "default", icon: <Drafts fontSize="small" /> },
    scheduled: { label: "예약", color: "warning", icon: <Schedule fontSize="small" /> },
    published: { label: "배포중", color: "success", icon: <CheckCircle fontSize="small" /> },
    closed: { label: "종료", color: "error", icon: <Block fontSize="small" /> },
  };

  const columns = useMemo<MRT_ColumnDef<FormItem>[]>(
    () => [
      {
        accessorKey: "idx",
        header: "ID",
        size: 60,
      },
      {
        accessorKey: "title",
        header: "제목",
        size: 200,
      },
      {
        accessorKey: "category",
        header: "카테고리",
        size: 120,
        Cell: ({ cell }) => (
          <Chip 
            label={cell.getValue<string>() || "default"} 
            size="small" 
            variant="outlined"
          />
        ),
      },
      {
        accessorKey: "publish_status",
        header: "배포 상태",
        size: 120,
        Cell: ({ cell }) => {
          const status = cell.getValue<PublishStatus>() || "draft";
          const config = statusConfig[status];
          return (
            <Chip 
              icon={config.icon as React.ReactElement} 
              label={config.label} 
              size="small" 
              color={config.color}
            />
          );
        },
      },
      {
        accessorKey: "publish_start_at",
        header: "배포 시작",
        size: 120,
        Cell: ({ cell }) => {
          const value = cell.getValue<string | null>();
          return value ? new Date(value).toLocaleDateString("ko-KR") : "-";
        },
      },
      {
        accessorKey: "publish_end_at",
        header: "배포 종료",
        size: 120,
        Cell: ({ cell }) => {
          const value = cell.getValue<string | null>();
          if (!value) return "-";
          const endDate = new Date(value);
          const now = new Date();
          const isExpired = endDate < now;
          return (
            <Typography 
              variant="body2" 
              color={isExpired ? "error" : "textPrimary"}
            >
              {endDate.toLocaleDateString("ko-KR")}
            </Typography>
          );
        },
      },
      {
        accessorKey: "created_at",
        header: "생성일",
        size: 100,
        Cell: ({ cell }) => {
          const value = cell.getValue<string | null>();
          return value ? new Date(value).toLocaleDateString("ko-KR") : "-";
        },
      },
    ],
    []
  );

  const handleViewForm = (uuid: string) => {
    navigate({ to: "/form-register/$idx", params: { idx: uuid } });
  };

  const handleCreateForm = () => {
    navigate({ to: "/form-register/$idx", params: { idx: "new" } });
  };

  // Detail Panel 컴포넌트
  const DetailPanel = ({ row }: { row: { original: FormItem } }) => {
    const formUuid = row.original.uuid;
    
    // 배포 목록 조회 (uuid 기반)
    const { data: publishData, isLoading } = useQuery({
      queryKey: ["publishes", formUuid],
      queryFn: () => FormRegisterService.getFormPublishes({ formUuid }),
      enabled: !!formUuid,
    });

    const publishItems = (publishData?.items || []) as FormPublishItem[];
    const totalPublishes = publishItems.length;
    const submittedCount = publishItems.filter(item => item.is_submitted).length;
    const pendingCount = totalPublishes - submittedCount;
    const submissionRate = totalPublishes > 0 ? Math.round((submittedCount / totalPublishes) * 100) : 0;

    // 만료된 배포 수
    const expiredCount = publishItems.filter(item => 
      !item.is_submitted && new Date(item.expired_at) < new Date()
    ).length;

    // 이메일 발송 통계
    const emailSentCount = publishItems.filter(item => item.is_email_sent).length;

    if (isLoading) {
      return (
        <Box sx={{ display: "flex", justifyContent: "center", p: 3 }}>
          <CircularProgress size={24} />
        </Box>
      );
    }

    return (
      <Box sx={{ p: 2, bgcolor: "grey.50" }}>
        <Typography variant="subtitle2" fontWeight={600} gutterBottom>
          배포 현황
        </Typography>
        
        {totalPublishes === 0 ? (
          <Typography variant="body2" color="text.secondary">
            아직 배포된 대상이 없습니다.
          </Typography>
        ) : (
          <Stack spacing={2}>
            {/* 통계 요약 */}
            <Stack direction="row" spacing={3} flexWrap="wrap" useFlexGap>
              <Box>
                <Typography variant="caption" color="text.secondary">전체 배포</Typography>
                <Typography variant="h6">{totalPublishes}명</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">응답 완료</Typography>
                <Typography variant="h6" color="success.main">{submittedCount}명</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">대기중</Typography>
                <Typography variant="h6" color="info.main">{pendingCount}명</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">만료됨</Typography>
                <Typography variant="h6" color="error.main">{expiredCount}명</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">이메일 발송</Typography>
                <Typography variant="h6" color="primary.main">{emailSentCount}명</Typography>
              </Box>
            </Stack>

            {/* 응답률 프로그레스 바 */}
            <Box>
              <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
                <Typography variant="caption" color="text.secondary">응답률</Typography>
                <Typography variant="caption" fontWeight={600}>{submissionRate}%</Typography>
              </Box>
              <LinearProgress 
                variant="determinate" 
                value={submissionRate} 
                sx={{ 
                  height: 8, 
                  borderRadius: 4,
                  bgcolor: "grey.200",
                  "& .MuiLinearProgress-bar": {
                    borderRadius: 4,
                  }
                }}
              />
            </Box>

            {/* 최근 응답자 목록 (최대 5명) */}
            {submittedCount > 0 && (
              <Box>
                <Typography variant="caption" color="text.secondary" gutterBottom display="block">
                  최근 응답 ({submittedCount}건)
                </Typography>
                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                  {publishItems
                    .filter(item => item.is_submitted)
                    .sort((a, b) => new Date(b.submitted_at || "").getTime() - new Date(a.submitted_at || "").getTime())
                    .slice(0, 5)
                    .map((item) => (
                      <Chip
                        key={item.idx}
                        size="small"
                        label={item.receiver_name || item.receiver}
                        color="success"
                        variant="outlined"
                      />
                    ))}
                  {submittedCount > 5 && (
                    <Chip size="small" label={`+${submittedCount - 5}명`} variant="outlined" />
                  )}
                </Stack>
              </Box>
            )}
          </Stack>
        )}
      </Box>
    );
  };

  const table = useMaterialReactTable({
    columns,
    data: (data?.items as FormItem[]) ?? [],
    manualPagination: true,
    rowCount: data?.total ?? 0,
    state: {
      isLoading,
      pagination,
      showAlertBanner: isError,
    },
    onPaginationChange: setPagination,
    enableRowActions: true,
    positionActionsColumn: "last",
    renderRowActions: ({ row }) => (
      <Box sx={{ display: "flex", gap: "0.5rem" }}>
        <Tooltip title="상세보기">
          <IconButton
            color="primary"
            onClick={() => handleViewForm(row.original.uuid)}
          >
            <Visibility />
          </IconButton>
        </Tooltip>
        <Tooltip title="수정">
          <IconButton
            color="secondary"
            onClick={() => handleViewForm(row.original.uuid)}
          >
            <Edit />
          </IconButton>
        </Tooltip>
      </Box>
    ),
    renderDetailPanel: ({ row }) => <DetailPanel row={row} />,
    enableExpanding: true,
    renderTopToolbarCustomActions: () => (
      <Button
        variant="contained"
        startIcon={<Add />}
        onClick={handleCreateForm}
        sx={{ m: 1 }}
      >
        새 폼 생성
      </Button>
    ),
    muiToolbarAlertBannerProps: isError
      ? {
          color: "error",
          children: "데이터를 불러오는데 실패했습니다.",
        }
      : undefined,
    muiTableContainerProps: {
      sx: { maxHeight: "calc(100vh - 250px)" },
    },
    muiTablePaperProps: {
      elevation: 0,
      sx: {
        borderRadius: 2,
        border: "1px solid",
        borderColor: "divider",
      },
    },
    muiTableHeadCellProps: {
      sx: {
        fontWeight: 600,
        backgroundColor: "grey.50",
      },
    },
  });

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ mb: 3 }}>
        <h1 style={{ margin: 0, fontSize: "1.5rem", fontWeight: 600 }}>
          폼 관리
        </h1>
        <p style={{ margin: "0.5rem 0 0", color: "#666" }}>
          등록된 폼 목록을 조회하고 관리합니다.
        </p>
      </Box>
      <MaterialReactTable table={table} />
    </Box>
  );
}
