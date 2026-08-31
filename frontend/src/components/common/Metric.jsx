export default function Metric({ icon: Icon, label, value, note, tone }) {
  return <div className="metric"><div className={`metric-icon ${tone}`}><Icon /></div><div><p>{label}</p><strong>{value}</strong><small>{note}</small></div></div>
}
