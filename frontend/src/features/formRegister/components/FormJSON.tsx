import { useState } from "react"
import {
  Box,
  Paper,
  Tab,
  Tabs,
  IconButton,
  Snackbar,
} from "@mui/material"
import { ContentCopy as CopyIcon } from "@mui/icons-material"
import type { RJSFSchema, UiSchema } from "@rjsf/utils"

interface FormJSONProps {
  schema: RJSFSchema
  uiSchema: UiSchema
  formData?: unknown
}

export default function FormJSON({ schema, uiSchema, formData }: FormJSONProps) {
  const [tab, setTab] = useState(0)
  const [copied, setCopied] = useState(false)

  const jsonData = [
    { label: 'all', data: { schema, uiSchema, formData } },
    { label: "Schema", data: schema },
    { label: "UI Schema", data: uiSchema },
    { label: "Form Data", data: formData || {} },
  ]

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(jsonData[tab].data, null, 2))
    setCopied(true)
  }

  return (
    <Paper variant="outlined" sx={{ height: "100%" }}>
      <Box sx={{ borderBottom: 1, borderColor: "divider", display: "flex", alignItems: "center" }}>
        <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ flex: 1 }}>
          {jsonData.map((item) => (
            <Tab key={item.label} label={item.label} sx={{ fontSize: 12, minHeight: 40 }} />
          ))}
        </Tabs>
        <IconButton size="small" onClick={handleCopy} sx={{ mr: 1 }}>
          <CopyIcon fontSize="small" />
        </IconButton>
      </Box>

      <Box
        component="pre"
        sx={{
          p: 1.5,
          m: 0,
          fontSize: 11,
          fontFamily: "monospace",
          overflow: "auto",
          bgcolor: "grey.50",
        }}
      >
        {JSON.stringify(jsonData[tab].data, null, 2)}
      </Box>

      <Snackbar
        open={copied}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        autoHideDuration={5000}
        onClose={() => setCopied(false)}
        message="복사됨!"
      />
    </Paper>
  )
}
