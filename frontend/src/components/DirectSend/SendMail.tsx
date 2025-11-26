import {
  Box,
  Button,
  Fieldset,
  Flex,
  Heading,
  IconButton,
  Input,
  Stack,
  Textarea,
} from "@chakra-ui/react"
import { useMutation } from "@tanstack/react-query"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { FiPlus, FiTrash2 } from "react-icons/fi"

import { Field } from "@/components/ui/field"
import { toaster } from "@/components/ui/toaster"
import {
  DirectSendMailService,
  type MailReceiver,
  type SendMailRequest,
} from "@/services/directsend"

interface MailFormData {
  subject: string
  body: string
  sender_name?: string
}

const SendMail = () => {
  const [receivers, setReceivers] = useState<MailReceiver[]>([
    { name: "", email: "" },
  ])

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<MailFormData>()

  const mutation = useMutation({
    mutationFn: (data: SendMailRequest) => DirectSendMailService.sendMail(data),
    onSuccess: (response) => {
      if (response.success) {
        toaster.success({
          title: "메일 발송 완료",
          description: response.message,
        })
        reset()
        setReceivers([{ name: "", email: "" }])
      } else {
        toaster.error({
          title: "메일 발송 실패",
          description: response.message,
        })
      }
    },
    onError: (error: Error) => {
      toaster.error({
        title: "오류 발생",
        description: error.message,
      })
    },
  })

  const addReceiver = () => {
    setReceivers([...receivers, { name: "", email: "" }])
  }

  const removeReceiver = (index: number) => {
    if (receivers.length > 1) {
      setReceivers(receivers.filter((_, i) => i !== index))
    }
  }

  const updateReceiver = (
    index: number,
    field: keyof MailReceiver,
    value: string
  ) => {
    const updated = [...receivers]
    updated[index] = { ...updated[index], [field]: value }
    setReceivers(updated)
  }

  const onSubmit = (data: MailFormData) => {
    const validReceivers = receivers.filter((r) => r.name && r.email)
    if (validReceivers.length === 0) {
      toaster.error({
        title: "오류",
        description: "최소 한 명의 수신자를 입력해주세요.",
      })
      return
    }

    mutation.mutate({
      ...data,
      receivers: validReceivers,
    })
  }

  return (
    <Box as="form" onSubmit={handleSubmit(onSubmit)}>
      <Fieldset.Root>
        <Fieldset.Legend>
          <Heading size="md" mb={4}>
            메일 발송
          </Heading>
        </Fieldset.Legend>
        <Fieldset.Content>
          <Stack gap={4}>
            <Field
              label="발신자 이름"
              invalid={!!errors.sender_name}
              errorText={errors.sender_name?.message}
            >
              <Input
                {...register("sender_name")}
                placeholder="발신자 이름 (선택)"
              />
            </Field>

            <Field
              label="제목"
              required
              invalid={!!errors.subject}
              errorText={errors.subject?.message}
            >
              <Input
                {...register("subject", { required: "제목을 입력해주세요" })}
                placeholder="메일 제목"
              />
            </Field>

            <Field
              label="본문"
              required
              invalid={!!errors.body}
              errorText={errors.body?.message}
            >
              <Textarea
                {...register("body", { required: "본문을 입력해주세요" })}
                placeholder="메일 본문 (HTML 지원)"
                rows={8}
              />
            </Field>

            <Box>
              <Flex justify="space-between" align="center" mb={2}>
                <Heading size="sm">수신자</Heading>
                <Button size="sm" onClick={addReceiver} variant="outline">
                  <FiPlus /> 추가
                </Button>
              </Flex>

              <Stack gap={2}>
                {receivers.map((receiver, index) => (
                  <Flex key={index} gap={2} align="center">
                    <Input
                      placeholder="이름"
                      value={receiver.name}
                      onChange={(e) =>
                        updateReceiver(index, "name", e.target.value)
                      }
                      flex={1}
                    />
                    <Input
                      placeholder="이메일"
                      type="email"
                      value={receiver.email}
                      onChange={(e) =>
                        updateReceiver(index, "email", e.target.value)
                      }
                      flex={2}
                    />
                    <IconButton
                      aria-label="수신자 삭제"
                      onClick={() => removeReceiver(index)}
                      disabled={receivers.length === 1}
                      variant="ghost"
                      colorPalette="red"
                      size="sm"
                    >
                      <FiTrash2 />
                    </IconButton>
                  </Flex>
                ))}
              </Stack>
            </Box>

            <Button
              type="submit"
              colorPalette="blue"
              loading={isSubmitting || mutation.isPending}
              loadingText="발송 중..."
            >
              메일 발송
            </Button>
          </Stack>
        </Fieldset.Content>
      </Fieldset.Root>
    </Box>
  )
}

export default SendMail

