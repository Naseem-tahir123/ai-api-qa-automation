import { Beaker } from 'lucide-react'

export default function Brand({ light = false, mobile = false }) {
  return <div className={`${mobile ? 'mobile-brand ' : ''}brand${light ? ' light' : ''}`}><span><Beaker /></span> QA Pilot</div>
}
