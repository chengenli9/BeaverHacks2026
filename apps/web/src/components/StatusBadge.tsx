import type { JobStatusValue } from '../types/api'

interface Props {
  status: JobStatusValue
  label?: string
}

export function StatusBadge({ status, label }: Props) {
  return (
    <span className={`status-badge ${status}`}>
      {status === 'running' && <span className="badge-dot" />}
      {label ?? status}
    </span>
  )
}
