/**
 * BIM 标书生成 App — 公共布局（UI 阶段 1.1）
 * 侧栏（Sider）+ 主内容区（Content）；子页面通过 Outlet 渲染在 Content 内。
 */
import { useNavigate, useLocation, Outlet } from 'react-router-dom'
import { Layout, Menu, Typography } from 'antd'
import { designTokens } from '../theme/tokens'
import '../App.css'

const { Sider, Content } = Layout
const { Title } = Typography

const SIDER_WIDTH = 220

const menuItems = [
  { key: '/', label: '首页' },
  { key: '/settings', label: '设置' },
  { key: '/compare', label: '对比' },
]

const contentStyle: React.CSSProperties = {
  padding: designTokens.marginLG,
}

export default function AppLayout() {
  const navigate = useNavigate()
  const location = useLocation()

  const selectedKey =
    location.pathname === '/'
      ? '/'
      : location.pathname.startsWith('/settings')
        ? '/settings'
        : location.pathname.startsWith('/compare')
          ? '/compare'
          : location.pathname.startsWith('/tasks')
            ? '/'
            : location.pathname

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        width={SIDER_WIDTH}
        style={{
          background: designTokens.colorBgContainer,
          borderRight: `1px solid ${designTokens.colorBorderSecondary}`,
        }}
      >
        <div
          style={{
            padding: designTokens.marginLG,
            borderBottom: `1px solid ${designTokens.colorBorderSecondary}`,
          }}
        >
          <Title
            level={5}
            style={{
              margin: 0,
              color: designTokens.colorText,
              fontWeight: designTokens.fontWeightStrong,
              fontSize: designTokens.fontSizeHeading5,
            }}
          >
            BIM 标书生成
          </Title>
        </div>
        <Menu
          mode="inline"
          items={menuItems}
          selectedKeys={[selectedKey]}
          style={{
            marginTop: designTokens.marginXS,
            borderRight: 'none',
            background: 'transparent',
          }}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Content style={contentStyle}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
