import { CheckCircle, XCircle, Send, ShieldCheck } from 'lucide-react'
import { usePipeline, usePipelineActions } from '../state/pipelineStore'

export function CriticPanel() {
  const { criticSuggestions, approvalState } = usePipeline()
  const { setApproval, submitApprovals } = usePipelineActions()

  if (!criticSuggestions) return null

  const allDecided = Object.values(approvalState).every((v) => v !== 'pending')
  const approvedCount = Object.values(approvalState).filter((v) => v === 'approved').length
  const rejectedCount = Object.values(approvalState).filter((v) => v === 'rejected').length

  return (
    <div id="critic-section">
      <div className="section-header">
        <ShieldCheck size={12} /> Critic Suggestions ({criticSuggestions.suggestions.length})
      </div>

      {criticSuggestions.suggestions.map((s) => {
        const state = approvalState[s.suggestion_id] ?? 'pending'
        return (
          <div key={s.suggestion_id} className="card" id={`suggestion-${s.suggestion_id}`}>
            <div className="card-header">
              <span className="card-title">
                {s.suggestion_id}
                <span style={{ fontWeight: 400, color: 'var(--text-muted)', fontSize: 11 }}>→ {s.block_id}</span>
              </span>
              <span className={`type-badge ${s.action}`}>{s.action.replace('_', ' ')}</span>
            </div>
            <div className="card-body">{s.reason}</div>
            <div className="card-meta">
              {s.amount_seconds > 0 && (
                <span className="card-meta-item">{s.amount_seconds.toFixed(1)}s</span>
              )}
              {s.replacement_text && (
                <span className="card-meta-item" style={{ color: 'var(--violet)' }}>
                  → "{s.replacement_text}"
                </span>
              )}
            </div>
            <div className="approval-controls">
              <button
                className={`approval-btn approve ${state === 'approved' ? 'active' : ''}`}
                onClick={() => setApproval(s.suggestion_id, state === 'approved' ? 'pending' : 'approved')}
                id={`approve-${s.suggestion_id}`}
              >
                <CheckCircle size={12} /> Approve
              </button>
              <button
                className={`approval-btn reject ${state === 'rejected' ? 'active' : ''}`}
                onClick={() => setApproval(s.suggestion_id, state === 'rejected' ? 'pending' : 'rejected')}
                id={`reject-${s.suggestion_id}`}
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
        disabled={!allDecided}
        id="apply-patches-btn"
      >
        <Send size={14} />
        Apply Changes ({approvedCount} approved, {rejectedCount} rejected)
      </button>
    </div>
  )
}
