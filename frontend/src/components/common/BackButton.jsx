import { ArrowLeft } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export default function BackButton({ to, label = 'Back' }) {
  const navigate = useNavigate()
  return <button className="back-button" onClick={() => navigate(to ?? -1)}><ArrowLeft /> {label}</button>
}
