import { Box, Button, Paper, Typography } from "@mui/material"
import type { ObjectFieldTemplateProps, SubmitButtonProps } from "@rjsf/utils"
import { getSubmitButtonOptions } from "@rjsf/utils"

// ============ 타입 정의 ============

interface SectionOptions {
  grid?: number
  backgroundColor?: string
  headerImage?: string
  sectionType?: "image" | "description"
  imageSrc?: string
  imageAlt?: string
  descriptionText?: string
  descriptionTitle?: string
}

// ============ ObjectFieldTemplate ============

/**
 * 기본 ObjectFieldTemplate
 */
export const ObjectFieldTemplate = (props: ObjectFieldTemplateProps) => {
  const { title, description, properties, uiSchema } = props
  const options = uiSchema?.["ui:options"] as SectionOptions | undefined
  const gridColumns = options?.grid || 1
  const backgroundColor = options?.backgroundColor
  const headerImage = options?.headerImage
  const sectionType = options?.sectionType

  // 이미지 섹션
  if (sectionType === "image") {
    const imageSrc = options?.imageSrc
    
    if (!imageSrc) {
      return (
        <Paper
          variant="outlined"
          sx={{
            mb: 2,
            p: 3,
            bgcolor: backgroundColor || "grey.100",
            textAlign: "center",
          }}
        >
          <Typography color="text.secondary">
            이미지가 설정되지 않았습니다
          </Typography>
        </Paper>
      )
    }

    return (
      <Paper
        variant="outlined"
        sx={{
          mb: 2,
          bgcolor: backgroundColor || undefined,
          overflow: "hidden",
          textAlign: "center",
        }}
      >
        <Box
          component="img"
          src={imageSrc}
          alt={options?.imageAlt || ""}
          sx={{
            width: gridColumns === 1 ? "100%" : `${100 / gridColumns}%`,
            objectFit: "contain",
            display: "block",
            mx: "auto",
          }}
        />
      </Paper>
    )
  }

  // 설명 섹션
  if (sectionType === "description") {
    const descText = options?.descriptionText
    const descTitle = options?.descriptionTitle
    
    if (!descText && !descTitle) {
      return (
        <Paper
          variant="outlined"
          sx={{
            mb: 2,
            p: 3,
            bgcolor: backgroundColor || "grey.100",
            textAlign: "center",
          }}
        >
          <Typography color="text.secondary">
            설명이 입력되지 않았습니다
          </Typography>
        </Paper>
      )
    }

      return (
        <Paper
          variant="outlined"
          sx={{
            mb: 2,
            p: 3,
            bgcolor: backgroundColor || undefined,
          }}
        >
          {descTitle && (
            <Typography variant="h5" fontWeight={600} gutterBottom>
              {descTitle}
            </Typography>
          )}
          {descText && (
            <Typography variant="body1" sx={{ whiteSpace: "pre-wrap", fontSize: "1.1rem", lineHeight: 1.8 }}>
              {descText}
            </Typography>
          )}
        </Paper>
      )
    }

  // 필드 섹션 (기본)
  const isSection = properties.length > 0

  if (isSection) {
    return (
      <Paper
        variant="outlined"
        sx={{
          mb: 2,
          bgcolor: backgroundColor || undefined,
          overflow: "hidden",
        }}
      >
        {headerImage && (
          <Box
            component="img"
            src={headerImage}
            alt=""
            sx={{ width: "100%", objectFit: "cover" }}
          />
        )}
        <Box sx={{ p: 2 }}>
          {title && (
            <Typography variant="h6" gutterBottom>
              {title}
            </Typography>
          )}
          {description && (
            <Typography variant="body2" color="text.secondary" mb={2}>
              {description}
            </Typography>
          )}
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: `repeat(${gridColumns}, 1fr)`,
              gap: 2,
            }}
          >
            {properties.map((prop) => (
              <Box key={prop.name}>{prop.content}</Box>
            ))}
          </Box>
        </Box>
      </Paper>
    )
  }

  // 루트 레벨
  return (
    <Box>
      {title && (
        <Typography variant="h5" gutterBottom>
          {title}
        </Typography>
      )}
      {description && (
        <Typography variant="body2" color="text.secondary" mb={2}>
          {description}
        </Typography>
      )}
      {properties.map((prop) => (
        <Box key={prop.name}>{prop.content}</Box>
      ))}
    </Box>
  )
}

/**
 * ObjectFieldTemplate 팩토리 (클릭 콜백 지원)
 * @deprecated ObjectFieldTemplate 직접 사용 권장
 */
export const createObjectFieldTemplate = (
  _onFieldClick?: (fieldId: string) => void
) => {
  return ObjectFieldTemplate
}

// ============ SubmitButton ============

/**
 * 커스텀 Submit 버튼
 */
export const SubmitButton = (props: SubmitButtonProps) => {
  const { uiSchema } = props
  const { norender } = getSubmitButtonOptions(uiSchema)
  
  if (norender) {
    return null
  }
  
  return (
    <Button type="submit" variant="contained" sx={{ float: "right" }}>
      제출
    </Button>
  )
}

// ============ Export ============

/**
 * 모든 커스텀 템플릿 export
 */
export const customTemplates = {
  ObjectFieldTemplate,
  ButtonTemplates: { SubmitButton },
}

export default customTemplates
