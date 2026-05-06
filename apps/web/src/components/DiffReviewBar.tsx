import { Check, X, MessageSquare, ArrowRight, Plus, Minus, RefreshCw } from 'lucide-react'
import { formatDuration } from '../utils/planDiff'
import type { PlanDiff } from '../utils/planDiff'

interface DiffReviewBarProps {
  diff: PlanDiff
  currentDuration: number
  proposedDuration: number
  onAccept: () => void
  onReject: () => void
  onEditPrompt?: () => void
}

export function DiffReviewBar({ diff, currentDuration, proposedDuration, onAccept, onReject, onEditPrompt }: DiffReviewBarProps) {
  const durationDelta = proposedDuration - currentDuration

  return (
    <div className="diff-review-bar">
      <div className="diff-review-summary">
        <div className="diff-review-title">
          <RefreshCw size={14} />
          AI proposed changes
        </div>
        <div className="diff-review-stats">
          {diff.added.length > 0 && (
            <span className="diff-stat diff-stat-added"><Plus size={11} />{diff.added.length} added</span>
          )}
          {diff.removed.length > 0 && (
            <span className="diff-stat diff-stat-removed"><Minus size={11} />{diff.removed.length} removed</span>
          )}
          {diff.modified.length > 0 && (
            <span className="diff-stat diff-stat-modified">~{diff.modified.length} modified</span>
          )}
          {diff.reordered && (
            <span className="diff-stat diff-stat-reordered">reordered</span>
          )}
        </div>
        <div className="diff-duration">
          {formatDuration(currentDuration)}
          <ArrowRight size={12} />
          {formatDuration(proposedDuration)}
          {durationDelta !== 0 && (
            <span className={`diff-duration-delta ${durationDelta < 0 ? 'negative' : 'positive'}`}>
              ({durationDelta > 0 ? '+' : ''}{durationDelta.toFixed(1)}s)
            </span>
          )}
        </div>
      </div>
      <div className="diff-review-actions">
        {onEditPrompt && (
          <button className="diff-btn diff-btn-secondary" onClick={onEditPrompt}>
            <MessageSquare size={12} /> Edit
          </button>
        )}
        <button className="diff-btn diff-btn-reject" onClick={onReject}>
          <X size={12} /> Reject
        </button>
        <button className="diff-btn diff-btn-accept" onClick={onAccept}>
          <Check size={12} /> Accept
        </button>
      </div>
    </div>
  )
}
