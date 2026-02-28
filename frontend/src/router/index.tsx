import { createBrowserRouter } from 'react-router-dom';
import MainLayout from '../layouts/MainLayout';
import LoginPage from '../pages/login/LoginPage';
import DashboardPage from '../pages/dashboard/DashboardPage';
import ImagingListPage from '../pages/imaging/ImagingListPage';
import ImagingUploadPage from '../pages/imaging/ImagingUploadPage';
import IssueListPage from '../pages/issues/IssueListPage';
import IssueDetailPage from '../pages/issues/IssueDetailPage';
import ReportListPage from '../pages/reports/ReportListPage';
import ProjectListPage from '../pages/projects/ProjectListPage';
import UserListPage from '../pages/users/UserListPage';
import AuditLogPage from '../pages/audit/AuditLogPage';
import SettingsPage from '../pages/settings/SettingsPage';

const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/',
    element: <MainLayout />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'dashboard', element: <DashboardPage /> },
      { path: 'imaging', element: <ImagingListPage /> },
      { path: 'imaging/upload', element: <ImagingUploadPage /> },
      { path: 'issues', element: <IssueListPage /> },
      { path: 'issues/:id', element: <IssueDetailPage /> },
      { path: 'reports', element: <ReportListPage /> },
      { path: 'projects', element: <ProjectListPage /> },
      { path: 'users', element: <UserListPage /> },
      { path: 'audit', element: <AuditLogPage /> },
      { path: 'settings', element: <SettingsPage /> },
    ],
  },
]);

export default router;
