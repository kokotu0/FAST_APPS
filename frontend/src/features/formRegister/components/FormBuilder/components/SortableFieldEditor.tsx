import { useSortable } from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import { FieldEditor, type FieldEditorProps } from "./FieldEditor"

export const SortableFieldEditor = (props: FieldEditorProps) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: props.field.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <div ref={setNodeRef} style={style}>
      <FieldEditor {...props} dragHandleProps={{ ...attributes, ...listeners }} />
    </div>
  )
}

