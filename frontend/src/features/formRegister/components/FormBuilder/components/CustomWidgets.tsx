import { TextField, Box, IconButton, InputAdornment } from "@mui/material"
import { Add as AddIcon, Remove as RemoveIcon } from "@mui/icons-material"
import type { WidgetProps } from "@rjsf/utils"

/**
 * 핸드폰 번호 위젯 (xxx-xxxx-xxxx 형식)
 */
export const PhoneNumberWidget = (props: WidgetProps) => {
  const { id, value, disabled, readonly, onChange, label, required } = props

  // 자동 하이픈 삽입
  const formatPhoneNumber = (input: string) => {
    const numbers = input.replace(/\D/g, "")
    if (numbers.length <= 3) return numbers
    if (numbers.length <= 7) return `${numbers.slice(0, 3)}-${numbers.slice(3)}`
    return `${numbers.slice(0, 3)}-${numbers.slice(3, 7)}-${numbers.slice(7, 11)}`
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const formatted = formatPhoneNumber(e.target.value)
    onChange(formatted)
  }

  return (
    <TextField
      id={id}
      label={label}
      value={value || ""}
      onChange={handleChange}
      disabled={disabled || readonly}
      required={required}
      placeholder="010-0000-0000"
      fullWidth
      size="small"
      inputProps={{
        maxLength: 13,
      }}
    />
  )
}

/**
 * 증감 버튼 위젯 (UpDown)
 */
export const UpDownWidget = (props: WidgetProps) => {
  const { 
    id, 
    value, 
    disabled, 
    readonly, 
    onChange, 
    label, 
    required,
    schema,
  } = props

  const numValue = typeof value === "number" ? value : 0
  const step = (schema.multipleOf as number) || 1
  const min = schema.minimum as number | undefined
  const max = schema.maximum as number | undefined

  const handleIncrement = () => {
    const newValue = numValue + step
    if (max === undefined || newValue <= max) {
      onChange(newValue)
    }
  }

  const handleDecrement = () => {
    const newValue = numValue - step
    if (min === undefined || newValue >= min) {
      onChange(newValue)
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value
    if (val === "") {
      onChange(undefined)
    } else {
      const num = Number(val)
      if (!isNaN(num)) {
        onChange(num)
      }
    }
  }

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
      <TextField
        id={id}
        label={label}
        type="number"
        value={value ?? ""}
        onChange={handleInputChange}
        disabled={disabled || readonly}
        required={required}
        size="small"
        sx={{ flex: 1 }}
        InputProps={{
          endAdornment: (
            <InputAdornment position="end">
              <IconButton
                size="small"
                onClick={handleDecrement}
                disabled={disabled || readonly || (min !== undefined && numValue <= min)}
              >
                <RemoveIcon fontSize="small" />
              </IconButton>
              <IconButton
                size="small"
                onClick={handleIncrement}
                disabled={disabled || readonly || (max !== undefined && numValue >= max)}
              >
                <AddIcon fontSize="small" />
              </IconButton>
            </InputAdornment>
          ),
        }}
        inputProps={{
          min,
          max,
          step,
        }}
      />
    </Box>
  )
}

/**
 * 모든 커스텀 위젯 export
 */
export const customWidgets = {
  phone: PhoneNumberWidget,
  updown: UpDownWidget,
}

export default customWidgets

