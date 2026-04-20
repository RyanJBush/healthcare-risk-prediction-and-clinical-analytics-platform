import { useMemo, useState } from 'react'
import { Navigate, Route, BrowserRouter as Router, Routes } from 'react-router-dom'

import Layout from './components/Layout'
import DashboardPage from './pages/DashboardPage'
import LoginPage from './pages/LoginPage'
import PatientDetailPage from './pages/PatientDetailPage'
import PatientsPage from './pages/PatientsPage'
import RiskAnalysisPage from './pages/RiskAnalysisPage'

function ProtectedRoute({ token, children, onLogout }) {
  if (!token) {
    return <Navigate to="/login" replace />
  }

  return <Layout onLogout={onLogout}>{children}</Layout>
}

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('nova_token'))

  const actions = useMemo(
    () => ({
      login: (nextToken) => {
        localStorage.setItem('nova_token', nextToken)
        setToken(nextToken)
      },
      logout: () => {
        localStorage.removeItem('nova_token')
        setToken('')
      },
    }),
    [],
  )

  return (
    <Router>
      <Routes>
        <Route path="/login" element={token ? <Navigate to="/dashboard" replace /> : <LoginPage onLogin={actions.login} />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute token={token} onLogout={actions.logout}>
              <DashboardPage token={token} />
            </ProtectedRoute>
          }
        />
        <Route
          path="/patients"
          element={
            <ProtectedRoute token={token} onLogout={actions.logout}>
              <PatientsPage token={token} />
            </ProtectedRoute>
          }
        />
        <Route
          path="/patients/:id"
          element={
            <ProtectedRoute token={token} onLogout={actions.logout}>
              <PatientDetailPage token={token} />
            </ProtectedRoute>
          }
        />
        <Route
          path="/risk-analysis"
          element={
            <ProtectedRoute token={token} onLogout={actions.logout}>
              <RiskAnalysisPage token={token} />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to={token ? '/dashboard' : '/login'} replace />} />
      </Routes>
    </Router>
  )
}
