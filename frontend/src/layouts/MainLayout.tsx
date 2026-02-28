import { useEffect, useState } from 'react';
import { Layout, Menu, Button, Space, Typography, Spin } from 'antd';
import {
  DashboardOutlined, PictureOutlined, AlertOutlined, FileTextOutlined,
  ProjectOutlined, UserOutlined, AuditOutlined, SettingOutlined,
  LogoutOutlined, MenuFoldOutlined, MenuUnfoldOutlined,
} from '@ant-design/icons';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../stores/auth';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

const menuConfig = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: '工作台', roles: ['admin', 'crc', 'cra', 'dm', 'expert', 'pm'] },
  { key: '/imaging', icon: <PictureOutlined />, label: '影像中心', roles: ['admin', 'crc', 'cra', 'dm', 'expert', 'pm'] },
  { key: '/issues', icon: <AlertOutlined />, label: '问题管理', roles: ['admin', 'crc', 'cra', 'dm', 'expert', 'pm'] },
  { key: '/reports', icon: <FileTextOutlined />, label: '报告管理', roles: ['admin', 'crc', 'cra', 'dm', 'expert', 'pm'] },
  { key: '/projects', icon: <ProjectOutlined />, label: '项目管理', roles: ['admin', 'pm'] },
  { key: '/users', icon: <UserOutlined />, label: '用户管理', roles: ['admin'] },
  { key: '/audit', icon: <AuditOutlined />, label: '审计日志', roles: ['admin'] },
  { key: '/settings', icon: <SettingOutlined />, label: '个人设置', roles: ['admin', 'crc', 'cra', 'dm', 'expert', 'pm'] },
];

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, isAuthenticated, loading, fetchMe, logout } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated) {
      fetchMe().catch(() => navigate('/login'));
    }
  }, []);

  if (loading) {
    return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}><Spin size="large" /></div>;
  }

  if (!isAuthenticated || !user) {
    navigate('/login');
    return null;
  }

  const visibleMenuItems = menuConfig
    .filter((item) => item.roles.includes(user.role))
    .map(({ key, icon, label }) => ({ key, icon, label }));

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider trigger={null} collapsible collapsed={collapsed} theme="dark">
        <div style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: collapsed ? 14 : 18, fontWeight: 'bold' }}>
          {collapsed ? '汇禾' : '汇禾影像管理'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={visibleMenuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{ background: '#fff', padding: '0 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', boxShadow: '0 1px 4px rgba(0,0,0,0.08)' }}>
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
          />
          <Space>
            <Text>{user.full_name}</Text>
            <Text type="secondary">({user.role.toUpperCase()})</Text>
            <Button type="text" icon={<LogoutOutlined />} onClick={handleLogout}>
              退出
            </Button>
          </Space>
        </Header>
        <Content style={{ margin: 24, padding: 24, background: '#fff', borderRadius: 8, minHeight: 280 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
