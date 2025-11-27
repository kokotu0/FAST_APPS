import type { ApiError } from "./client"
import useCustomToast from "./hooks/useCustomToast"

export const emailPattern = {
  value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
  message: "올바른 이메일 형식을 입력해주세요",
}

export const namePattern = {
  value: /^[A-Za-z\s\u00C0-\u017F가-힣]{1,30}$/,
  message: "올바른 이름을 입력해주세요",
}

export const passwordRules = (isRequired = true) => {
  const rules: any = {
    minLength: {
      value: 8,
      message: "비밀번호는 8자 이상이어야 합니다",
    },
  }

  if (isRequired) {
    rules.required = "비밀번호를 입력해주세요"
  }

  return rules
}

export const confirmPasswordRules = (
  getValues: () => any,
  passwordField: string = "password",
  isRequired = true,
) => {
  const rules: any = {
    validate: (value: string) => {
      const values = getValues()
      const password = values[passwordField] || values.password || values.new_password || values.plain_password
      return value === password ? true : "비밀번호가 일치하지 않습니다"
    },
  }

  if (isRequired) {
    rules.required = "비밀번호 확인을 입력해주세요"
  }

  return rules
}

export const handleError = (err: ApiError) => {
  const { showErrorToast } = useCustomToast()
  const errDetail = (err.body as any)?.detail
  let errorMessage = errDetail || "Something went wrong."
  if (Array.isArray(errDetail) && errDetail.length > 0) {
    errorMessage = errDetail[0].msg
  }
  showErrorToast(errorMessage)
}
