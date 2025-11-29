import { Box, Flex, Icon, Text } from "@chakra-ui/react"
import { useQueryClient } from "@tanstack/react-query"
import { Link as RouterLink, useLocation } from "@tanstack/react-router"
import { FiUsers, FiChevronDown, FiChevronRight } from "react-icons/fi"
import type { IconType } from "react-icons/lib"
import { useState } from "react"

import type { UserOut } from "@/client"
import { SITEMAP, type SitemapItem } from "./sitemap"

interface SidebarItemsProps {
  onClose?: () => void
}

// 단일 메뉴 아이템
const MenuItem = ({ 
  icon, 
  title, 
  path, 
  onClose,
  isActive,
  indent = false,
}: { 
  icon: IconType
  title: string
  path: string
  onClose?: () => void
  isActive?: boolean
  indent?: boolean
}) => (
  <RouterLink to={path} onClick={onClose}>
    <Flex
      gap={4}
      px={4}
      py={2}
      pl={indent ? 8 : 4}
      _hover={{
        background: "gray.subtle",
      }}
      background={isActive ? "gray.subtle" : undefined}
      alignItems="center"
      fontSize="sm"
    >
      <Icon as={icon} alignSelf="center" />
      <Text ml={2}>{title}</Text>
    </Flex>
  </RouterLink>
)

// 그룹 메뉴 아이템
const MenuGroup = ({ 
  item, 
  onClose,
  currentPath,
}: { 
  item: SitemapItem
  onClose?: () => void
  currentPath: string
}) => {
  // 자식 중에 현재 경로가 있으면 기본으로 열기
  const hasActiveChild = item.children?.some(child => child.path === currentPath)
  const [isOpen, setIsOpen] = useState(hasActiveChild || false)

  return (
    <Box>
      {/* 그룹 헤더 */}
      <Flex
        gap={4}
        px={4}
        py={2}
        _hover={{
          background: "gray.subtle",
          cursor: "pointer",
        }}
        alignItems="center"
        fontSize="sm"
        onClick={() => setIsOpen(!isOpen)}
      >
        <Icon as={item.icon} alignSelf="center" />
        <Text ml={2} flex={1}>{item.title}</Text>
        <Icon as={isOpen ? FiChevronDown : FiChevronRight} />
      </Flex>
      
      {/* 자식 메뉴 */}
      {isOpen && item.children && (
        <Box>
          {item.children.map((child) => (
            child.path && (
              <MenuItem
                key={child.title}
                icon={child.icon}
                title={child.title}
                path={child.path}
                onClose={onClose}
                isActive={currentPath === child.path}
                indent
              />
            )
          ))}
        </Box>
      )}
    </Box>
  )
}

const SidebarItems = ({ onClose }: SidebarItemsProps) => {
  const queryClient = useQueryClient()
  const location = useLocation()
  const currentUser = queryClient.getQueryData<UserOut>(["currentUser"])
  const currentPath = location.pathname

  // Admin 메뉴 추가
  const finalItems: SitemapItem[] = currentUser?.is_superuser
    ? [...SITEMAP, { icon: FiUsers, title: "Admin", path: "/admin" }]
    : SITEMAP

  return (
    <>
      <Text fontSize="xs" px={4} py={2} fontWeight="bold">
        Menu
      </Text>
      <Box>
        {finalItems.map((item) => (
          item.children ? (
            <MenuGroup 
              key={item.title} 
              item={item} 
              onClose={onClose}
              currentPath={currentPath}
            />
          ) : item.path ? (
            <MenuItem
              key={item.title}
              icon={item.icon}
              title={item.title}
              path={item.path}
              onClose={onClose}
              isActive={currentPath === item.path}
            />
          ) : null
        ))}
      </Box>
    </>
  )
}

export default SidebarItems
