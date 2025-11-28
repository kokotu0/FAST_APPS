import { createFileRoute } from "@tanstack/react-router";
import type { RJSFSchema, UiSchema } from "@rjsf/utils";
import validator from "@rjsf/validator-ajv8";
import { Form } from "@rjsf/mui";
import { toast } from "react-hot-toast";
import { Box, Typography, Paper, Divider, Grid } from "@mui/material";

// 커스텀 Object Field 템플릿 - 섹션 스타일링 + 그리드 지원
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const ObjectFieldTemplate = (props: any) => {
  const { title, description, properties, idSchema, uiSchema } = props;
  const isRoot = idSchema?.$id === "root";
  
  // ui:grid 옵션 확인 (columns 수)
  const gridColumns = uiSchema?.["ui:grid"] || 1;

  // 루트는 큰 제목/설명
  if (isRoot) {
    return (
      <Box sx={{ maxWidth: 900, mx: "auto", p: 2 }}>
        {title && (
          <Typography variant="h4" fontWeight="bold" gutterBottom>
            {title}
          </Typography>
        )}
        {description && (
          <Typography variant="body1" color="text.secondary" mb={3}>
            {description}
          </Typography>
        )}
        {properties.map((prop: any) => prop.content)}
      </Box>
    );
  }

  // 섹션(중첩 object) - 그리드 레이아웃 지원
  return (
    <Paper variant="outlined" sx={{ p: 3, mb: 3 }}>
      {title && (
        <Typography variant="h6" fontWeight="bold" gutterBottom>
          {title}
        </Typography>
      )}
      {description && (
        <Typography variant="body2" color="text.secondary" mb={2}>
          {description}
        </Typography>
      )}
      <Divider sx={{ mb: 2 }} />
      {gridColumns > 1 ? (
        // 그리드 레이아웃 (2열, 3열 등)
        (<Grid container spacing={2}>
          {properties.map((prop: any) => (
            <Grid size={{ xs: 12, md: 12 / gridColumns }} key={prop.name}>
              {prop.content}
            </Grid>
          ))}
        </Grid>)
      ) : (
        // 기본 세로 레이아웃
        (<Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {properties.map((prop: any) => prop.content)}
        </Box>)
      )}
    </Paper>
  )
};
const schema = {
  "schema": {
    "type": "object",
    "title": "새 폼",
    "description": "",
    "properties": {
      "J3BmVxg-K9Pl5hoFrNzrk": {
        "type": "object",
        "title": "ㅇ",
        "description": "",
        "properties": {
          "2LPeuolbTG29gzSJC3ouu": {
            "type": "number",
            "title": "새 필드asdsa",
            "minimum": 1,
            "maximum": 22222
          }
        },
        "required": [
          "2LPeuolbTG29gzSJC3ouu"
        ]
      },
      "Ulli_Q2IBQEAeOY57iTNi": {
        "type": "object",
        "title": "새 섹션",
        "description": "",
        "properties": {}
      }
    },
    "required": []
  },
  "uiSchema": {
    "ui:order": [
      "J3BmVxg-K9Pl5hoFrNzrk",
      "Ulli_Q2IBQEAeOY57iTNi"
    ],
    "J3BmVxg-K9Pl5hoFrNzrk": {
      "2LPeuolbTG29gzSJC3ouu": {
        "ui:widget": "updown"
      },
      "ui:order": [
        "2LPeuolbTG29gzSJC3ouu"
      ],
      "ui:options": {
        "headerImage": "https://search.pstatic.net/common/?src=http%3A%2F%2Fblogfiles.naver.net%2FMjAyNTEwMzBfMTAw%2FMDAxNzYxNzUyMDAyNjUx.hUyZiXZkZ2F4UlyW97sUOxsAOntzc6VPWPloCh0g_fIg.Cm96c_AH9nORIsS1AoaCAYutVioLJtF6h1uL-AhHD_og.JPEG%2FIMG%25A3%25DF7711.jpg&type=sc960_832"
      }
    },
    "Ulli_Q2IBQEAeOY57iTNi": {
      "ui:order": []
    }
  }
};

export const Route = createFileRoute("/_layout/form-register/test")({
  component: RouteComponent,
});

function RouteComponent() {
  return (
    <Form
      schema={schema.schema}
      uiSchema={schema.uiSchema}
      validator={validator}
      templates={{
        ObjectFieldTemplate,
      }}
      onSubmit={({ formData }) => {
        toast.success("제출 완료!");
        console.log("formData:", formData);
      }}
    />
  );
}
