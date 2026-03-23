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

const mainNavItems = [
  { key: '/one-click', label: '一键生成' },
  { key: '/', label: '高级生成' },
  { key: '/compare', label: '修正对比' },
  { key: '/review', label: '标书校审' },
]
const bottomNavItems = [{ key: '/settings', label: '设置' }]

const contentStyle: React.CSSProperties = {
  padding: designTokens.marginLG,
}

export default function AppLayout() {
  const navigate = useNavigate()
  const location = useLocation()

  const selectedKey =
    location.pathname === '/'
      ? '/'
      : location.pathname.startsWith('/one-click')
        ? '/one-click'
        : location.pathname.startsWith('/settings')
          ? '/settings'
          : location.pathname.startsWith('/compare')
            ? '/compare'
            : location.pathname.startsWith('/review')
              ? '/review'
              : location.pathname.startsWith('/tasks')
                ? '/'
                : location.pathname

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        width={SIDER_WIDTH}
        style={{
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          height: '100vh',
          zIndex: 100,
          background: designTokens.colorBgContainer,
          borderRight: `1px solid ${designTokens.colorBorderSecondary}`,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            minHeight: '100vh',
            height: '100%',
          }}
        >
          <div
            style={{
              padding: designTokens.marginLG,
              borderBottom: `1px solid ${designTokens.colorBorderSecondary}`,
              flexShrink: 0,
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
          <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
            <Menu
              mode="inline"
              items={mainNavItems}
              selectedKeys={[selectedKey]}
              style={{
                marginTop: designTokens.marginXS,
                borderRight: 'none',
                background: 'transparent',
              }}
              onClick={({ key }) => navigate(key)}
            />
          </div>
          <div
            style={{
              borderTop: `1px solid ${designTokens.colorBorderSecondary}`,
              flexShrink: 0,
            }}
          >
            <Menu
              mode="inline"
              items={bottomNavItems}
              selectedKeys={[selectedKey]}
              style={{
                borderRight: 'none',
                background: 'transparent',
              }}
              onClick={({ key }) => navigate(key)}
            />
          </div>
        </div>
      </Sider>
      <Layout style={{ marginLeft: SIDER_WIDTH, minHeight: '100vh' }}>
        <Content style={contentStyle}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
