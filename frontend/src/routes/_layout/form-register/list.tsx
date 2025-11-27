import { Box, Button, Container, Heading, Text } from "@chakra-ui/react"
import { createFileRoute, Link } from "@tanstack/react-router"
import { FiPlus } from "react-icons/fi"

export const Route = createFileRoute("/_layout/form-register/list")({
  component: RouteComponent,
})

function RouteComponent() {
  return (
    <Container maxW="full">
      <Heading size="lg" pt={12}>
        폼 목록
      </Heading>
      <Text color="gray.500" mb={6}>
        등록된 폼 목록입니다.
      </Text>

      <Box mb={4}>
        <Link to="/form-register/$idx" params={{ idx: "new" }} preload="intent">
          <Button colorScheme="teal">
            <FiPlus />
            만들기
          </Button>
        </Link>
      </Box>

      {/* TODO: 폼 목록 테이블 */}
      <Box p={4} borderWidth={1} borderRadius="md" bg="gray.50">
        <Text color="gray.500">등록된 폼이 없습니다.</Text>
      </Box>
    </Container>
  )
}
