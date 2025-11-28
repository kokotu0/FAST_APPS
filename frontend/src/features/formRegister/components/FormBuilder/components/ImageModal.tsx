import { useState, useRef } from "react"
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Tabs,
  Tab,
  Box,
  Typography,
  Stack,
} from "@mui/material"
import { CloudUpload as UploadIcon } from "@mui/icons-material"
import type { ImageContent } from "../types"

interface ImageModalProps {
  open: boolean
  onClose: () => void
  onSave: (content: ImageContent) => void
  initialContent?: ImageContent
}

export const ImageModal = ({ open, onClose, onSave, initialContent }: ImageModalProps) => {
  const [tab, setTab] = useState<0 | 1>(initialContent?.file ? 1 : 0)
  const [url, setUrl] = useState(initialContent?.url || "")
  const [file, setFile] = useState(initialContent?.file || "")
  const [alt, setAlt] = useState(initialContent?.alt || "")
  const [width, setWidth] = useState(initialContent?.width?.toString() || "")
  const [height, setHeight] = useState(initialContent?.height?.toString() || "")
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      const reader = new FileReader()
      reader.onload = () => {
        setFile(reader.result as string)
      }
      reader.readAsDataURL(selectedFile)
    }
  }

  const handleSave = () => {
    const content: ImageContent = {
      alt,
      width: width ? (isNaN(Number(width)) ? width : Number(width)) : undefined,
      height: height ? (isNaN(Number(height)) ? height : Number(height)) : undefined,
    }
    
    if (tab === 0 && url) {
      content.url = url
    } else if (tab === 1 && file) {
      content.file = file
    }
    
    onSave(content)
    onClose()
  }

  const previewSrc = tab === 0 ? url : file

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>이미지 설정</DialogTitle>
      <DialogContent>
        <Tabs value={tab} onChange={(_, v) => setTab(v as 0 | 1)} sx={{ mb: 2 }}>
          <Tab label="URL 입력" />
          <Tab label="파일 업로드" />
        </Tabs>

        {tab === 0 && (
          <TextField
            fullWidth
            label="이미지 URL"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com/image.jpg"
            sx={{ mb: 2 }}
          />
        )}

        {tab === 1 && (
          <Box sx={{ mb: 2 }}>
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept="image/*"
              style={{ display: "none" }}
            />
            <Button
              variant="outlined"
              startIcon={<UploadIcon />}
              onClick={() => fileInputRef.current?.click()}
              fullWidth
              sx={{ py: 2 }}
            >
              {file ? "다른 이미지 선택" : "이미지 선택"}
            </Button>
          </Box>
        )}

        {/* 미리보기 */}
        {previewSrc && (
          <Box
            sx={{
              mb: 2,
              p: 1,
              border: "1px solid",
              borderColor: "divider",
              borderRadius: 1,
              textAlign: "center",
            }}
          >
            <Typography variant="caption" color="text.secondary" display="block" mb={1}>
              미리보기
            </Typography>
            <Box
              component="img"
              src={previewSrc}
              alt={alt || "미리보기"}
              sx={{
                maxWidth: "100%",
                maxHeight: 200,
                objectFit: "contain",
              }}
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = "none"
              }}
            />
          </Box>
        )}

        {/* 추가 설정 */}
        <TextField
          fullWidth
          label="대체 텍스트 (alt)"
          value={alt}
          onChange={(e) => setAlt(e.target.value)}
          placeholder="이미지 설명"
          size="small"
          sx={{ mb: 2 }}
        />
        
        <Stack direction="row" spacing={2}>
          <TextField
            label="너비"
            value={width}
            onChange={(e) => setWidth(e.target.value)}
            placeholder="auto 또는 숫자"
            size="small"
            sx={{ flex: 1 }}
          />
          <TextField
            label="높이"
            value={height}
            onChange={(e) => setHeight(e.target.value)}
            placeholder="auto 또는 숫자"
            size="small"
            sx={{ flex: 1 }}
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>취소</Button>
        <Button variant="contained" onClick={handleSave} disabled={!url && !file}>
          저장
        </Button>
      </DialogActions>
    </Dialog>
  )
}

