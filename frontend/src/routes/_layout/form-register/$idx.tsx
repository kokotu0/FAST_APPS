import { createFileRoute } from "@tanstack/react-router"
import FormPage from "@/features/formRegister/pages/form"

export const Route = createFileRoute("/_layout/form-register/$idx")({
  component: RouteComponent,
})

function RouteComponent() {
  const { idx } = Route.useParams()
  const uuid = idx === "new" ? undefined : idx

  return <FormPage uuid={uuid} />
}
