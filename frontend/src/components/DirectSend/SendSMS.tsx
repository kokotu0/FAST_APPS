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
  DirectSendSMSService,
  type SMSReceiver,
  type SendSMSRequest,
} from "@/services/directsend"

interface SMSFormData {
  title: string
  message: string
}

const SendSMS = () => {
  const [receivers, setReceivers] = useState<SMSReceiver[]>([
    { name: "", mobile: "" },
  ])

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<SMSFormData>()

  const mutation = useMutation({
    mutationFn: (data: SendSMSRequest) => DirectSendSMSService.sendSMS(data),
    onSuccess: (response) => {
      if (response.success) {
        toaster.success({
          title: "SMS 발송 완료",
          description: response.message,
        })
        reset()
        setReceivers([{ name: "", mobile: "" }])
      } else {
        toaster.error({
          title: "SMS 발송 실패",
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
    setReceivers([...receivers, { name: "", mobile: "" }])
  }

  const removeReceiver = (index: number) => {
    if (receivers.length > 1) {
      setReceivers(receivers.filter((_, i) => i !== index))
    }
  }

  const updateReceiver = (
    index: number,
    field: keyof SMSReceiver,
    value: string
  ) => {
    const updated = [...receivers]
    updated[index] = { ...updated[index], [field]: value }
    setReceivers(updated)
  }

  const onSubmit = (data: SMSFormData) => {
    const validReceivers = receivers.filter((r) => r.name && r.mobile)
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
            SMS 발송
          </Heading>
        </Fieldset.Legend>
        <Fieldset.Content>
          <Stack gap={4}>
            <Field
              label="제목 (MMS/LMS)"
              required
              invalid={!!errors.title}
              errorText={errors.title?.message}
            >
              <Input
                {...register("title", {
                  required: "제목을 입력해주세요",
                  maxLength: { value: 40, message: "최대 40자까지 입력 가능" },
                })}
                placeholder="제목 (최대 40byte)"
              />
            </Field>

            <Field
              label="메시지"
              required
              invalid={!!errors.message}
              errorText={errors.message?.message}
            >
              <Textarea
                {...register("message", {
                  required: "메시지를 입력해주세요",
                  maxLength: {
                    value: 2000,
                    message: "최대 2000자까지 입력 가능",
                  },
                })}
                placeholder="메시지 내용 (최대 2000byte)"
                rows={6}
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
                      placeholder="전화번호"
                      value={receiver.mobile}
                      onChange={(e) =>
                        updateReceiver(index, "mobile", e.target.value)
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
              colorPalette="green"
              loading={isSubmitting || mutation.isPending}
              loadingText="발송 중..."
            >
              SMS 발송
            </Button>
          </Stack>
        </Fieldset.Content>
      </Fieldset.Root>
    </Box>
  )
}

export default SendSMS

