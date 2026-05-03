import { useEffect, useState } from "react"

interface Props {
  showLabel?: boolean
  durationMs?: number // optional override
  progress?: number // external progress override (0-100)
}

export function ProgressBar({ showLabel = true, durationMs = 10000, progress: externalProgress }: Props) {
  const [internalProgress, setInternalProgress] = useState(0)

  useEffect(() => {
    if (externalProgress !== undefined) return

    let start = performance.now()

    // irregular easing function (non-linear + jitter)
    const step = (now: number) => {
      const elapsed = now - start
      const t = Math.min(elapsed / durationMs, 1)

      // base smooth curve (ease-in-out)
      const base = t < 0.5
        ? 2 * t * t
        : 1 - Math.pow(-2 * t + 2, 2) / 2

      // add subtle irregularity ("human-like" jitter)
      const jitter = (Math.sin(t * 40) + Math.sin(t * 13)) * 0.015

      const next = Math.min(Math.max(base + jitter, 0), 1)

      setInternalProgress(next)

      if (t < 1) {
        requestAnimationFrame(step)
      }
    }

    const frame = requestAnimationFrame(step)

    return () => cancelAnimationFrame(frame)
  }, [durationMs, externalProgress])

  const currentProgress = externalProgress !== undefined ? (externalProgress / 100) : internalProgress
  const pct = Math.round(currentProgress * 100)

  return (
    <div>
      <div className="progress-bar-container">
        <div
          className="progress-bar-fill"
          style={{
            width: `${pct}%`,
            transition: "width 0.1s linear"
          }}
        />
      </div>

      {showLabel && (
        <div className="progress-label">
          {pct}%
        </div>
      )}
    </div>
  )
}