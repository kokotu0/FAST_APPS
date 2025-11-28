import { useSortable } from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import { SectionEditor, type SectionEditorProps } from "./SectionEditor"

export type SortableSectionEditorProps = Omit<SectionEditorProps, "dragHandleProps">

export const SortableSectionEditor = (props: SortableSectionEditorProps) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: props.section.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <div ref={setNodeRef} style={style}>
      <SectionEditor {...props} dragHandleProps={{ ...attributes, ...listeners }} />
    </div>
  )
}
