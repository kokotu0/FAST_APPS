import { Container, Flex, Image, Input, Text } from "@chakra-ui/react"
import {
  createFileRoute,
  Link as RouterLink,
  redirect,
} from "@tanstack/react-router"
import { type SubmitHandler, useForm } from "react-hook-form"
import { FiLock, FiMail, FiUser } from "react-icons/fi"

import type { UserRegister } from "@/client"
import { Button } from "@/components/ui/button"
import { Field } from "@/components/ui/field"
import { InputGroup } from "@/components/ui/input-group"
import { PasswordInput } from "@/components/ui/password-input"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"
import { confirmPasswordRules, emailPattern, passwordRules } from "@/utils"
import Logo from "/assets/images/fastapi-logo.svg"

export const Route = createFileRoute("/signup")({
  component: SignUp,
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({
        to: "/",
      })
    }
  },
})

interface UserRegisterForm extends UserRegister {
  confirm_password: string
}

function SignUp() {
  const { signUpMutation } = useAuth()
  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<UserRegisterForm>({
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      user_id: "",
      email: "",
      name: "",
      plain_password: "",
      confirm_password: "",
    },
  })

  const onSubmit: SubmitHandler<UserRegisterForm> = (data) => {
    signUpMutation.mutate(data)
  }

  return (
    <Flex flexDir={{ base: "column", md: "row" }} justify="center" h="100vh">
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
        
        {/* 아이디 */}
        <Field
          invalid={!!errors.user_id}
          errorText={errors.user_id?.message}
        >
          <InputGroup w="100%" startElement={<FiUser />}>
            <Input
              {...register("user_id", {
                required: "아이디를 입력해주세요",
                minLength: { value: 4, message: "아이디는 4자 이상이어야 합니다" },
                maxLength: { value: 50, message: "아이디는 50자 이하여야 합니다" },
              })}
              placeholder="아이디"
              type="text"
            />
          </InputGroup>
        </Field>

        {/* 이름 */}
        <Field
          invalid={!!errors.name}
          errorText={errors.name?.message}
        >
          <InputGroup w="100%" startElement={<FiUser />}>
            <Input
              {...register("name", {
                required: "이름을 입력해주세요",
                minLength: { value: 1, message: "이름은 1자 이상이어야 합니다" },
                maxLength: { value: 100, message: "이름은 100자 이하여야 합니다" },
              })}
              placeholder="이름"
              type="text"
            />
          </InputGroup>
        </Field>

        {/* 이메일 */}
        <Field invalid={!!errors.email} errorText={errors.email?.message}>
          <InputGroup w="100%" startElement={<FiMail />}>
            <Input
              {...register("email", {
                required: "이메일을 입력해주세요",
                pattern: emailPattern,
              })}
              placeholder="이메일"
              type="email"
            />
          </InputGroup>
        </Field>

        {/* 비밀번호 */}
        <PasswordInput
          type="plain_password"
          startElement={<FiLock />}
          {...register("plain_password", passwordRules())}
          placeholder="비밀번호"
          errors={errors}
        />

        {/* 비밀번호 확인 */}
        <PasswordInput
          type="confirm_password"
          startElement={<FiLock />}
          {...register("confirm_password", confirmPasswordRules(getValues, "plain_password"))}
          placeholder="비밀번호 확인"
          errors={errors}
        />

        <Button variant="solid" type="submit" loading={isSubmitting}>
          회원가입
        </Button>
        <Text>
          이미 계정이 있으신가요?{" "}
          <RouterLink to="/login" className="main-link">
            로그인
          </RouterLink>
        </Text>
      </Container>
    </Flex>
  )
}

export default SignUp
