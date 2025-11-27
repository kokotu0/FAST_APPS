import { Container, Image, Input, Text } from "@chakra-ui/react"
import {
  createFileRoute,
  Link as RouterLink,
  redirect,
} from "@tanstack/react-router"
import { type SubmitHandler, useForm } from "react-hook-form"
import { FiLock, FiUser } from "react-icons/fi"

import type { Body_login_login_access_token as AccessToken } from "@/client"
import { Button } from "@/components/ui/button"
import { Field } from "@/components/ui/field"
import { InputGroup } from "@/components/ui/input-group"
import { PasswordInput } from "@/components/ui/password-input"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"
import Logo from "/assets/images/fastapi-logo.svg"
import { passwordRules } from "../utils"

export const Route = createFileRoute("/login")({
  component: Login,
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({
        to: "/",
      })
    }
  },
})

function Login() {
  const { loginMutation, error, resetError } = useAuth()
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<AccessToken>({
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      username: "",
      password: "",
    },
  })

  const onSubmit: SubmitHandler<AccessToken> = async (data) => {
    if (isSubmitting) return

    resetError()

    try {
      await loginMutation.mutateAsync(data)
    } catch {
      // error is handled by useAuth hook
    }
  }

  return (
    <Container
      as="form"
      onSubmit={handleSubmit(onSubmit)}
      h="100vh"
      maxW="sm"
      alignItems="stretch"
      justifyContent="center"
      gap={4}
      centerContent
    >
      <Image
        src={Logo}
        alt="FastAPI logo"
        height="auto"
        maxW="2xs"
        alignSelf="center"
        mb={4}
      />
      <Field
        invalid={!!errors.username}
        errorText={errors.username?.message || (error ? "로그인 정보를 확인해주세요" : undefined)}
      >
        <InputGroup w="100%" startElement={<FiUser />}>
          <Input
            {...register("username", {
              required: "아이디를 입력해주세요",
              minLength: { value: 4, message: "아이디는 4자 이상이어야 합니다" },
            })}
            placeholder="아이디"
            type="text"
          />
        </InputGroup>
      </Field>
      <PasswordInput
        type="password"
        startElement={<FiLock />}
        {...register("password", passwordRules())}
        placeholder="비밀번호"
        errors={errors}
      />
      <RouterLink to="/recover-password" className="main-link">
        비밀번호를 잊으셨나요?
      </RouterLink>
      <Button variant="solid" type="submit" loading={isSubmitting} size="md">
        로그인
      </Button>
      <Text>
        계정이 없으신가요?{" "}
        <RouterLink to="/signup" className="main-link">
          회원가입
        </RouterLink>
      </Text>
    </Container>
  )
}
