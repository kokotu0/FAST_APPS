import { Container, Heading } from "@chakra-ui/react"
import { createFileRoute } from "@tanstack/react-router"

import SendSMS from "@/components/DirectSend/SendSMS"

export const Route = createFileRoute("/_layout/directsend-sms")({
  component: DirectSendSMS,
})

function DirectSendSMS() {
  return (
    <Container maxW="full">
      <Heading size="lg" pt={12} mb={6}>
        DirectSend SMS
      </Heading>
      <SendSMS />
    </Container>
  )
}

