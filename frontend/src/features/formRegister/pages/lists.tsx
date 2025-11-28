import { useMemo, useState } from "react";
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
  type MRT_PaginationState,
} from "material-react-table";
import { Box, Button, IconButton, Tooltip } from "@mui/material";
import { Visibility, Edit, Add } from "@mui/icons-material";
import { useNavigate } from "@tanstack/react-router";
import { useFormRegister } from "../hooks/useFormRegister";

// 폼 아이템 타입 정의
interface FormItem {
  idx: number;
  title: string;
  description: string | null;
  content: Record<string, unknown> | null;
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

  const columns = useMemo<MRT_ColumnDef<FormItem>[]>(
    () => [
      {
        accessorKey: "idx",
        header: "ID",
        size: 80,
      },
      {
        accessorKey: "title",
        header: "제목",
        size: 200,
      },
      {
        accessorKey: "description",
        header: "설명",
        size: 250,
        Cell: ({ cell }) => (
          <Box
            sx={{
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
              maxWidth: 250,
            }}
          >
            {cell.getValue<string>() || "-"}
          </Box>
        ),
      },
      {
        accessorKey: "created_at",
        header: "생성일",
        size: 150,
        Cell: ({ cell }) => {
          const value = cell.getValue<string | null>();
          return value ? new Date(value).toLocaleDateString("ko-KR") : "-";
        },
      },
    ],
    []
  );

  const handleViewForm = (idx: number) => {
    navigate({ to: "/form-register/$idx", params: { idx: String(idx) } });
  };

  const handleCreateForm = () => {
    navigate({ to: "/form-register/$idx", params: { idx: "new" } });
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
            onClick={() => handleViewForm(row.original.idx)}
          >
            <Visibility />
          </IconButton>
        </Tooltip>
        <Tooltip title="수정">
          <IconButton
            color="secondary"
            onClick={() => handleViewForm(row.original.idx)}
          >
            <Edit />
          </IconButton>
        </Tooltip>
      </Box>
    ),
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
