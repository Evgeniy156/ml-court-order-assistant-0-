import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout as AntLayout, Menu, Button, Avatar, Dropdown } from 'antd'
import {
  DashboardOutlined,
  CreditCardOutlined,
  UploadOutlined,
  HistoryOutlined,
  LogoutOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { useAuth } from '../contexts/AuthContext'
import type { MenuProps } from 'antd'

const { Header, Content, Sider } = AntLayout

const Layout: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuth()

  const menuItems: MenuProps['items'] = [
    {
      key: '/dashboard',
      icon: <DashboardOutlined />,
      label: 'Дашборд',
    },
    {
      key: '/payment',
      icon: <CreditCardOutlined />,
      label: 'Пополнение баланса',
    },
    {
      key: '/upload',
      icon: <UploadOutlined />,
      label: 'Загрузка данных',
    },
    {
      key: '/history',
      icon: <HistoryOutlined />,
      label: 'История транзакций',
    },
  ]

  const userMenuItems: MenuProps['items'] = [
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Выход',
      onClick: () => {
        logout()
        navigate('/login')
      },
    },
  ]

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: '#001529' }}>
        <div style={{ color: 'white', fontSize: '18px', fontWeight: 'bold' }}>
          ML Court Order Assistant
        </div>
        <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
          <Button type="text" style={{ color: 'white' }}>
            <Avatar icon={<UserOutlined />} style={{ marginRight: 8 }} />
            {user?.email}
          </Button>
        </Dropdown>
      </Header>
      <AntLayout>
        <Sider width={200} style={{ background: '#fff' }}>
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
            items={menuItems}
            onClick={({ key }) => navigate(key)}
            style={{ height: '100%', borderRight: 0 }}
          />
        </Sider>
        <AntLayout style={{ padding: '24px' }}>
          <Content
            style={{
              padding: 24,
              margin: 0,
              minHeight: 280,
              background: '#fff',
              borderRadius: '8px',
            }}
          >
            <Outlet />
          </Content>
        </AntLayout>
      </AntLayout>
    </AntLayout>
  )
}

export default Layout

