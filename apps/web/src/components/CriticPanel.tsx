import { CheckCircle, Send, ShieldCheck, XCircle, Pencil, X } from 'lucide-react'
import { usePipeline, usePipelineActions } from '../state/pipelineStore'

export function CriticPanel() {
  const { criticSuggestions, approvalState, manifest } = usePipeline()
  const { setApproval, submitApprovals, highlightBlock, dismissSuggestion } = usePipelineActions()

  if (!criticSuggestions) return null

  const visible = criticSuggestions.suggestions.filter((s) => approvalState[s.suggestion_id] !== 'dismissed')
  const decisions = visible.map((s) => approvalState[s.suggestion_id] ?? 'pending')
  const approvedCount = decisions.filter((v) => v === 'approved').length
  const rejectedCount = decisions.filter((v) => v === 'rejected').length
  const skippedCount = decisions.filter((v) => v === 'pending').length
  const hasAnyDecision = approvedCount + rejectedCount > 0

  const blockTypes: Record<string, string> = {}
  for (const block of manifest?.blocks ?? []) {
    blockTypes[block.block_id] = block.type.replace('_', ' ')
  }

  if (visible.length === 0) return null

  return (
    <div id="critic-section">
      <div className="section-header">
        <ShieldCheck size={12} /> Review Suggestions ({visible.length})
      </div>

      {visible.map((suggestion) => {
        const state = approvalState[suggestion.suggestion_id] ?? 'pending'
        const blockLabel = blockTypes[suggestion.block_id] ?? 'block'

        return (
          <div
            key={suggestion.suggestion_id}
            className="card"
            id={`suggestion-${suggestion.suggestion_id}`}
            onMouseEnter={() => highlightBlock(suggestion.block_id)}
            onMouseLeave={() => highlightBlock(null)}
          >
            <button
              className="card-dismiss"
              title="Dismiss"
              onClick={() => dismissSuggestion(suggestion.suggestion_id)}
            >
              <X size={12} />
            </button>

            <div className="card-header">
              <span className="suggestion-target">
                <Pencil size={10} />
                <span className="suggestion-block-id">{suggestion.block_id}</span>
                <span className="suggestion-block-type">{blockLabel}</span>
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
                  &rarr; "{suggestion.replacement_text}"
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

      {hasAnyDecision && (
        <button
          className="apply-btn"
          onClick={submitApprovals}
          id="apply-patches-btn"
        >
          <Send size={14} />
          {approvedCount > 0
            ? `Apply ${approvedCount} Approved${rejectedCount > 0 ? `, ${rejectedCount} Rejected` : ''}`
            : `Dismiss ${rejectedCount} Suggestion${rejectedCount === 1 ? '' : 's'}`}
          {skippedCount > 0 ? ` (${skippedCount} skipped)` : ''}
        </button>
      )}
    </div>
  )
}
