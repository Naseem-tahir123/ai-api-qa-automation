import { ChevronRight, Menu, Search } from 'lucide-react'
import { useLocation } from 'react-router-dom'

function pageName(pathname) {
  if (pathname.includes('/report') || pathname === '/reports') return 'Reports'
  if (pathname.startsWith('/projects/')) return 'Project workspace'
  if (pathname === '/projects') return 'Projects'
  return 'Overview'
}

export default function Header({ onMenu }) {
  const location = useLocation()
  return <header><button className="menu" aria-label="Toggle navigation" onClick={onMenu}><Menu /></button><div className="crumb">Workspace <ChevronRight /> <strong>{pageName(location.pathname)}</strong></div><div className="header-actions"><button className="icon-btn" aria-label="Search"><Search /></button><div className="avatar">QA</div></div></header>
}
