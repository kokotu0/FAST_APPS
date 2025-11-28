import {
  FiBriefcase,
  FiFileText,
  FiHome,
  FiMail,
  FiMessageSquare,
  FiSettings,
  FiUsers,
} from "react-icons/fi";

export const SITEMAP = [
  { icon: FiHome, title: "Dashboard", path: "/" },
  { icon: FiFileText, title: "폼 리스트", path: "/form-register/list" },
  { icon: FiFileText, title: "폼 생성", path: "/form-register/" },
  { icon: FiMail, title: "DirectSend 메일", path: "/directsend-mail" },
  { icon: FiSettings, title: "User Settings", path: "/settings" },
  { icon: FiMessageSquare, title: "DirectSend SMS", path: "/directsend-sms" },

];
