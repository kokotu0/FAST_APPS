import {
  FiFileText,
  FiHome,
  FiMail,
  FiMessageSquare,
  FiSettings,
  FiBarChart2,
  FiEdit3,
  FiList,
  FiSend,
} from "react-icons/fi";
import type { IconType } from "react-icons";

export interface SitemapItem {
  icon: IconType;
  title: string;
  path?: string;
  children?: SitemapItem[];
}

export const SITEMAP: SitemapItem[] = [
  { icon: FiHome, title: "Dashboard", path: "/" },
  
  // 폼 관리 그룹
  { 
    icon: FiFileText, 
    title: "폼 관리",
    children: [
      { icon: FiList, title: "폼 리스트", path: "/form-register/list" },
      { icon: FiEdit3, title: "폼 생성", path: "/form-register/new" },
      { icon: FiBarChart2, title: "응답 결과", path: "/form-register/responses" },
    ]
  },
  
  // 메시지 발송 그룹
  {
    icon: FiSend,
    title: "메시지 발송",
    children: [
      { icon: FiMail, title: "이메일 발송", path: "/directsend-mail" },
      { icon: FiMessageSquare, title: "SMS 발송", path: "/directsend-sms" },
    ]
  },
  
  // 설정
  { icon: FiSettings, title: "설정", path: "/settings" },
];
