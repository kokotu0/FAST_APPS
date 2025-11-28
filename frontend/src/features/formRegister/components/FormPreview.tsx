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

  const handleChange = (e: IChangeEvent) => {
    console.log("Preview form data:", e.formData)
  }

  const handleFieldFocus = (id: string) => {
    if (onFieldClick) {
      const fieldName = id.replace("root_", "")
      onFieldClick(fieldName)
    }
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
