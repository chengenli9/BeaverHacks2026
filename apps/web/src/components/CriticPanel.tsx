import { CheckCircle, Send, ShieldCheck, XCircle } from 'lucide-react'
import { usePipeline, usePipelineActions } from '../state/pipelineStore'

export function CriticPanel() {
  const { criticSuggestions, approvalState } = usePipeline()
  const { setApproval, submitApprovals } = usePipelineActions()

  if (!criticSuggestions) return null

  const decisions = Object.values(approvalState)
  const approvedCount = decisions.filter((value) => value === 'approved').length
  const rejectedCount = decisions.filter((value) => value === 'rejected').length
  const skippedCount = decisions.filter((value) => value === 'pending').length
  const hasAnyDecision = approvedCount + rejectedCount > 0

  return (
    <div id="critic-section">
      <div className="section-header">
        <ShieldCheck size={12} /> Review Suggestions ({criticSuggestions.suggestions.length})
      </div>

      {criticSuggestions.suggestions.map((suggestion) => {
        const state = approvalState[suggestion.suggestion_id] ?? 'pending'

        return (
          <div key={suggestion.suggestion_id} className="card" id={`suggestion-${suggestion.suggestion_id}`}>
            <div className="card-header">
              <span className="card-title">
                {suggestion.suggestion_id}
                <span style={{ fontWeight: 400, color: 'var(--text-muted)', fontSize: 11 }}>
                  - {suggestion.block_id}
                </span>
              </span>
              <span className={`type-badge ${suggestion.action}`}>{suggestion.action.replace('_', ' ')}</span>
            </div>

            <div className="card-body">
              <div>{suggestion.reason}</div>
              {suggestion.viewer_problem && (
                <div style={{ marginTop: 6, color: 'var(--text-muted)' }}>{suggestion.viewer_problem}</div>
              )}
            </div>

            <div className="card-meta">
              {suggestion.category && <span className="card-meta-item">{suggestion.category}</span>}
              {suggestion.severity && <span className="card-meta-item">{suggestion.severity}</span>}
              {typeof suggestion.confidence === 'number' && (
                <span className="card-meta-item">{Math.round(suggestion.confidence * 100)}% confidence</span>
              )}
              {suggestion.amount_seconds > 0 && (
                <span className="card-meta-item">{suggestion.amount_seconds.toFixed(1)}s</span>
              )}
              {suggestion.replacement_text && (
                <span className="card-meta-item" style={{ color: 'var(--violet)' }}>
                  - "{suggestion.replacement_text}"
                </span>
              )}
            </div>

            {(suggestion.before_summary || suggestion.after_summary) && (
              <div className="card-meta" style={{ marginTop: 4 }}>
                {suggestion.before_summary && <span className="card-meta-item">Before: {suggestion.before_summary}</span>}
                {suggestion.after_summary && <span className="card-meta-item">After: {suggestion.after_summary}</span>}
              </div>
            )}

            {suggestion.evidence.length > 0 && (
              <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {suggestion.evidence.map((item) => (
                  <span key={item} className="card-meta-item">
                    {item}
                  </span>
                ))}
              </div>
            )}

            <div className="approval-controls">
              <button
                className={`approval-btn approve ${state === 'approved' ? 'active' : ''}`}
                aria-label={`Approve ${suggestion.suggestion_id}`}
                onClick={() => setApproval(
                  suggestion.suggestion_id,
                  state === 'approved' ? 'pending' : 'approved',
                )}
                id={`approve-${suggestion.suggestion_id}`}
              >
                <CheckCircle size={12} /> Approve
              </button>
              <button
                className={`approval-btn reject ${state === 'rejected' ? 'active' : ''}`}
                aria-label={`Reject ${suggestion.suggestion_id}`}
                onClick={() => setApproval(
                  suggestion.suggestion_id,
                  state === 'rejected' ? 'pending' : 'rejected',
                )}
                id={`reject-${suggestion.suggestion_id}`}
              >
                <XCircle size={12} /> Reject
              </button>
            </div>
          </div>
        )
      })}

      <button
        className="apply-btn"
        onClick={submitApprovals}
        disabled={!hasAnyDecision}
        id="apply-patches-btn"
      >
        <Send size={14} />
        Apply {approvedCount} Approved{rejectedCount > 0 ? `, ${rejectedCount} Rejected` : ''}
        {skippedCount > 0 ? ` (${skippedCount} skipped)` : ''}
      </button>
    </div>
  )
}
