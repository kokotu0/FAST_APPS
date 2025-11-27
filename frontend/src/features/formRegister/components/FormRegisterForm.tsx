import { Box, Input, Textarea, VStack } from "@chakra-ui/react"
import { type SubmitHandler, useForm, Controller } from "react-hook-form"
import { Button } from "@/components/ui/button"
import { Field } from "@/components/ui/field"
import type { RJSFSchema, UiSchema } from "@rjsf/utils"

// re-export for convenience
export type { RJSFSchema, UiSchema }

/**
 * 폼 등록 요청 데이터 타입
 */
export interface FormRegisterData {
  title: string
  description?: string
  jsonSchema: RJSFSchema
  uiSchema: UiSchema
  theme: Record<string, unknown>
}

interface FormRegisterFormProps {
  onSubmit: SubmitHandler<FormRegisterData>
  isLoading?: boolean
  defaultValues?: Partial<FormRegisterData>
  /** FormBuilder에서 전달받은 스키마 */
  schemaData?: {
    jsonSchema: RJSFSchema
    uiSchema: UiSchema
    theme: Record<string, unknown>
  }
}

const DEFAULT_JSON_SCHEMA: RJSFSchema = {
  type: "object",
  properties: {},
}

const DEFAULT_UI_SCHEMA: UiSchema = {}

const DEFAULT_THEME: Record<string, unknown> = {}

/**
 * Form 등록/수정 폼 컴포넌트
 * jsonSchema, uiSchema, theme 정보를 담아 백엔드에 전달
 */
export const FormRegisterForm = ({
  onSubmit,
  isLoading,
  defaultValues,
  schemaData,
}: FormRegisterFormProps) => {
  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<FormRegisterData>({
    mode: "onBlur",
    defaultValues: {
      title: "",
      description: "",
      jsonSchema: DEFAULT_JSON_SCHEMA,
      uiSchema: DEFAULT_UI_SCHEMA,
      theme: DEFAULT_THEME,
      ...defaultValues,
      // schemaData가 있으면 덮어쓰기
      ...(schemaData && {
        jsonSchema: schemaData.jsonSchema,
        uiSchema: schemaData.uiSchema,
        theme: schemaData.theme,
      }),
    },
  })

  return (
    <Box as="form" onSubmit={handleSubmit(onSubmit)} w="100%">
      <VStack gap={4}>
        <Field
          label="제목"
          invalid={!!errors.title}
          errorText={errors.title?.message}
        >
          <Input
            {...register("title", {
              required: "제목을 입력해주세요",
              minLength: { value: 1, message: "제목은 1자 이상이어야 합니다" },
              maxLength: { value: 255, message: "제목은 255자 이하여야 합니다" },
            })}
            placeholder="폼 제목"
          />
        </Field>

        <Field
          label="설명"
          invalid={!!errors.description}
          errorText={errors.description?.message}
        >
          <Textarea
            {...register("description", {
              maxLength: { value: 255, message: "설명은 255자 이하여야 합니다" },
            })}
            placeholder="폼 설명 (선택)"
            rows={3}
          />
        </Field>

        {/* Hidden fields for schema data */}
        <Controller
          name="jsonSchema"
          control={control}
          render={() => <input type="hidden" />}
        />
        <Controller
          name="uiSchema"
          control={control}
          render={() => <input type="hidden" />}
        />
        <Controller
          name="theme"
          control={control}
          render={() => <input type="hidden" />}
        />

        <Button
          type="submit"
          variant="solid"
          loading={isLoading}
          w="100%"
        >
          등록
        </Button>
      </VStack>
    </Box>
  )
}

export default FormRegisterForm

