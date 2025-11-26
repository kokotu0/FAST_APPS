import { Container, Heading } from "@chakra-ui/react"
import { createFileRoute } from "@tanstack/react-router"

import SendMail from "@/components/DirectSend/SendMail"

export const Route = createFileRoute("/_layout/directsend-mail")({
  component: DirectSendMail,
})

function DirectSendMail() {
  return (
    <Container maxW="full">
      <Heading size="lg" pt={12} mb={6}>
        DirectSend 메일
      </Heading>
      <SendMail />
    </Container>
  )
}

