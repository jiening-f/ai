interface StatCardProps {
  icon: string
  label: string
  value: string | number
  color: 'purple' | 'blue' | 'green' | 'orange'
}

function StatCard({ icon, label, value, color }: StatCardProps) {
  return (
    <div className="stat-card">
      <div className={`stat-card-icon ${color}`}>{icon}</div>
      <div className="stat-card-body">
        <div className="stat-card-label">{label}</div>
        <div className="stat-card-value">{value}</div>
      </div>
    </div>
  )
}

export default StatCard
