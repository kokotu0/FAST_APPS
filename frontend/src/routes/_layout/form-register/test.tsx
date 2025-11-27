import { createFileRoute } from "@tanstack/react-router";
import type { RJSFSchema, UiSchema } from "@rjsf/utils";
import validator from "@rjsf/validator-ajv8";
import { Form } from "@rjsf/mui";
import { toast } from "react-hot-toast";
import { Box, Typography, Paper, Divider } from "@mui/material";

// 커스텀 Object Field 템플릿 - 섹션 스타일링
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const ObjectFieldTemplate = (props: any) => {
  const { title, description, properties, idSchema } = props;
  const isRoot = idSchema?.$id === "root";

  // 루트는 큰 제목/설명
  if (isRoot) {
    return (
      <Box>
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

  // 섹션(중첩 object)은 카드 스타일
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
      <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {properties.map((prop: any) => prop.content)}
      </Box>
    </Paper>
  );
};

const schema: RJSFSchema = {
  title: "회원가입 폼",
  description: "아래 정보를 입력해주세요. * 표시는 필수 항목입니다.",
  type: "object",
  properties: {
    // 섹션 1: 기본 정보
    basicInfo: {
      type: "object",
      title: "📋 기본 정보",
      description: "회원 식별을 위한 기본 정보를 입력해주세요.",
      required: ["name", "email"],
      properties: {
        name: {
          type: "string",
          title: "이름",
          description: "본명을 입력해주세요",
        },
        email: {
          type: "string",
          title: "이메일",
          format: "email",
        },
        age: {
          type: "integer",
          title: "나이",
          minimum: 0,
          maximum: 120,
        },
      },
    },

    // 섹션 2: 자기소개
    introduction: {
      type: "object",
      title: "✏️ 자기소개",
      description: "자신을 소개해주세요.",
      properties: {
        bio: {
          type: "string",
          title: "자기소개",
        },
        website: {
          type: "string",
          title: "웹사이트/포트폴리오",
          format: "uri",
        },
      },
    },

    // 섹션 3: 프로필 설정
    profile: {
      type: "object",
      title: "👤 프로필 설정",
      description: "프로필 정보를 설정해주세요.",
      properties: {
        gender: {
          type: "string",
          title: "성별",
          oneOf: [
            { const: "male", title: "남성" },
            { const: "female", title: "여성" },
            { const: "other", title: "기타" },
          ],
          description: "성별을 선택해주세요",
        },
        birthDate: {
          type: "string",
          title: "생년월일",
          format: "date",
        },
        interests: {
          type: "array",
          title: "관심사",
          description: "관심 있는 분야를 모두 선택해주세요",
          items: {
            type: "string",
            oneOf: [
              { const: "sports", title: "스포츠" },
              { const: "music", title: "음악" },
              { const: "reading", title: "독서" },
              { const: "travel", title: "여행" },
              { const: "coding", title: "코딩" },
            ],
          },
          uniqueItems: true,
        },
      },
    },

    // 섹션 4: 알림 설정
    notifications: {
      type: "object",
      title: "🔔 알림 설정",
      description: "알림 수신 여부를 설정해주세요.",
      properties: {
        newsletter: {
          type: "boolean",
          title: "뉴스레터 구독",
          description: "최신 소식을 이메일로 받아보세요",
          default: false,
        },
        marketingAgree: {
          type: "boolean",
          title: "마케팅 정보 수신 동의",
          default: false,
        },
      },
    },
  },
};

const uiSchema: UiSchema = {
  "ui:order": ["basicInfo", "introduction", "profile", "notifications"],
  basicInfo: {
    name: {
      "ui:placeholder": "홍길동",
    },
    email: {
      "ui:placeholder": "example@email.com",
    },
  },
  introduction: {
    bio: {
      "ui:widget": "textarea",
      "ui:placeholder": "간단한 자기소개를 작성해주세요",
      "ui:options": {
        rows: 4,
      },
    },
    website: {
      "ui:placeholder": "https://",
    },
  },
  profile: {
    interests: {
      "ui:widget": "checkboxes",
    },
  },
};
export const Route = createFileRoute("/_layout/form-register/test")({
  component: RouteComponent,
});

function RouteComponent() {
  return (
      <Form
        schema={schema}
        uiSchema={uiSchema}
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
