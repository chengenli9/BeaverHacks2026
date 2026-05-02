interface Props {
  progress: number // 0-1
  showLabel?: boolean
}

export function ProgressBar({ progress, showLabel = true }: Props) {
  const pct = Math.min(Math.max(progress * 100, 0), 100)
  return (
    <div>
      <div className="progress-bar-container">
        <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
      </div>
      {showLabel && <div className="progress-label">{pct.toFixed(0)}%</div>}
    </div>
  )
}
