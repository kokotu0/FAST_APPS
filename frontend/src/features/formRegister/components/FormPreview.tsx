import { Box, Typography } from "@mui/material"
import Form from "@rjsf/mui"
import validator from "@rjsf/validator-ajv8"
import type { RJSFSchema, UiSchema } from "@rjsf/utils"
import type { IChangeEvent } from "@rjsf/core"

interface FormPreviewProps {
  jsonSchema: RJSFSchema
  uiSchema: UiSchema
  onFieldClick?: (fieldName: string) => void
}

export const FormPreview = ({
  jsonSchema,
  uiSchema,
  onFieldClick,
}: FormPreviewProps) => {
  const hasFields = jsonSchema.properties && Object.keys(jsonSchema.properties).length > 0

  const handleChange = (e: IChangeEvent) => {
    console.log("Preview form data:", e.formData)
  }

  const handleFieldFocus = (id: string) => {
    if (onFieldClick) {
      const fieldName = id.replace("root_", "")
      onFieldClick(fieldName)
    }
  }

  if (!hasFields) {
    return (
      <Box
        sx={{
          p: 2,
          border: "1px dashed",
          borderColor: "grey.400",
          borderRadius: 1,
          textAlign: "center",
          color: "grey.500",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Typography variant="body2">빌더에서 필드를 추가하세요</Typography>
      </Box>
    )
  }

  return (
    <Box sx={{ height: "100%" }}>
      <Typography variant="subtitle2" fontWeight="bold" mb={1}>
        미리보기
      </Typography>
      <Form
        schema={jsonSchema}
        uiSchema={{
          ...uiSchema,
          "ui:submitButtonOptions": { norender: true },
        }}
        validator={validator}
        onChange={handleChange}
        onFocus={handleFieldFocus}
        liveValidate
      />
    </Box>
  )
}

export default FormPreview
