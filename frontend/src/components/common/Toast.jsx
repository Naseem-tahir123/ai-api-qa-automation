import { CheckCircle2, X, XCircle } from 'lucide-react'

export default function Toast({ toast, onClose }) {
  if (!toast) return null
  return <div className={`toast ${toast.type || ''}`} role="status"><span>{toast.type === 'error' ? <XCircle /> : <CheckCircle2 />}</span><p>{toast.message}</p><button aria-label="Close notification" onClick={onClose}><X /></button></div>
}
