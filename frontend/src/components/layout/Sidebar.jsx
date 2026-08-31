import { Activity, Code2, LayoutDashboard, LogOut } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import Brand from '../common/Brand'

const navigation = [
  { to: '/dashboard', label: 'Overview', icon: LayoutDashboard },
  { to: '/projects', label: 'Projects', icon: Code2 },
  { to: '/reports', label: 'Reports', icon: Activity },
]

export default function Sidebar({ open, onNavigate, onLogout }) {
  return <aside className={open ? 'open' : ''}><Brand /><nav>{navigation.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} onClick={onNavigate} className={({ isActive }) => isActive ? 'active' : ''}><Icon />{label}</NavLink>)}</nav><div className="aside-bottom"><div className="mini-status"><span/><div><strong>Preview mode</strong><small>Local demo data</small></div></div><button onClick={onLogout}><LogOut /> Sign out</button></div></aside>
}
