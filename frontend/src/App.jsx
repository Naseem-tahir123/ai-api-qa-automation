import { Navigate, Route, Routes } from 'react-router-dom'
import ProtectedRoute from './components/layout/ProtectedRoute'
import Shell from './components/layout/Shell'
import DashboardPage from './pages/DashboardPage'
import LoginPage from './pages/LoginPage'
import NotFoundPage from './pages/NotFoundPage'
import ProjectReportPage from './pages/ProjectReportPage'
import ProjectWorkspacePage from './pages/ProjectWorkspacePage'
import ProjectsPage from './pages/ProjectsPage'
import ReportsPage from './pages/ReportsPage'

export default function App() {
  return <Routes>
    <Route path="/login" element={<LoginPage />} />
    <Route element={<ProtectedRoute />}>
      <Route element={<Shell />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="projects" element={<ProjectsPage />} />
        <Route path="projects/:projectId" element={<ProjectWorkspacePage />} />
        <Route path="projects/:projectId/report" element={<ProjectReportPage />} />
        <Route path="reports" element={<ReportsPage />} />
      </Route>
    </Route>
    <Route path="*" element={<NotFoundPage />} />
  </Routes>
}
