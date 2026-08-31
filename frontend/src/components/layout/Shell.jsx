import { useState } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import Sidebar from './Sidebar'
import Header from './Header'

export default function Shell() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { logout } = useAuth()
  const navigate = useNavigate()
  const handleLogout = () => { logout(); navigate('/login', { replace: true }) }
  return <div className="app-shell"><Sidebar open={sidebarOpen} onNavigate={() => setSidebarOpen(false)} onLogout={handleLogout}/><div className="main-wrap"><Header onMenu={() => setSidebarOpen((open) => !open)} /><Outlet /></div></div>
}
