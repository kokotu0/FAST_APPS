import { createFileRoute } from "@tanstack/react-router"
import FormListPage from "@/features/formRegister/pages/lists"

export const Route = createFileRoute("/_layout/form-register/list")({
  component: RouteComponent,
})

function RouteComponent() {
  return <FormListPage />
}
