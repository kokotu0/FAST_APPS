import { createFileRoute } from "@tanstack/react-router";
import { RJSFSchema, UiSchema } from "@rjsf/utils";
import validator from "@rjsf/validator-ajv8";
import { Form } from "@rjsf/mui";
import { toast } from "react-hot-toast";

const schema: RJSFSchema = {
  type: "object",
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
    bio: {
      type: "string",
      title: "자기소개",
    },
    gender: {
      type: "string",
      title: "성별",
      oneOf: [
        { const: "male", title: "남성" },
        { const: "female", title: "여성" },
        { const: "other", title: "기타" },
      ],
    },
    interests: {
      type: "array",
      title: "관심사",
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
    newsletter: {
      type: "boolean",
      title: "뉴스레터 구독",
      default: false,
    },
    birthDate: {
      type: "string",
      title: "생년월일",
      format: "date",
    },
    website: {
      type: "string",
      title: "웹사이트",
      format: "uri",
    },
  },
};

const uiSchema: UiSchema = {
  bio: {
    "ui:widget": "textarea",
    "ui:placeholder": "간단한 자기소개를 작성해주세요",
  },
  interests: {
    "ui:widget": "checkboxes",
  },
  name: {
    "ui:placeholder": "홍길동",
  },
  email: {
    "ui:placeholder": "example@email.com",
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
      onSubmit={({ formData }) => {
        toast.success("제출 완료!");
        console.log("formData:", formData);
      }}
    />
  );
}
