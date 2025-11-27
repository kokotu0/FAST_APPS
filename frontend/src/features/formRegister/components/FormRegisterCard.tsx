import { Box, Heading, Text, VStack } from "@chakra-ui/react"
import type { FormRegisterResponse } from "@/client"

interface FormRegisterCardProps {
  form: FormRegisterResponse
  onClick?: () => void
}

/**
 * Form 카드 컴포넌트
 */
export const FormRegisterCard = ({ form, onClick }: FormRegisterCardProps) => {
  return (
    <Box
      p={4}
      borderWidth="1px"
      borderRadius="lg"
      cursor={onClick ? "pointer" : "default"}
      onClick={onClick}
      _hover={onClick ? { bg: "gray.50" } : undefined}
      transition="background 0.2s"
    >
      <VStack align="start" gap={2}>
        <Heading size="sm">{form.title}</Heading>
        {form.description && (
          <Text color="gray.600" fontSize="sm">
            {form.description}
          </Text>
        )}
        {form.created_at && (
          <Text color="gray.400" fontSize="xs">
            생성일: {new Date(form.created_at).toLocaleDateString()}
          </Text>
        )}
      </VStack>
    </Box>
  )
}

export default FormRegisterCard

