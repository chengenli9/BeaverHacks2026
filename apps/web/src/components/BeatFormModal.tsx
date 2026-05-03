import { useEffect, useRef, useState } from 'react'
import { ImagePlus, Plus, X } from 'lucide-react'
import type { CreateBeatRequest } from '../types/api'

interface Props {
  insertAfter: string | null
  submitting: boolean
  onClose: () => void
  onSubmit: (payload: CreateBeatRequest) => Promise<void> | void
}

type TabKey = 'scene_card' | 'image_card'

export function BeatFormModal({ insertAfter, submitting, onClose, onSubmit }: Props) {
  const [tab, setTab] = useState<TabKey>('scene_card')
  const [text, setText] = useState('')
  const [duration, setDuration] = useState(3)
  const [layoutPreset, setLayoutPreset] = useState<'centered' | 'hero-left' | 'hero-right' | 'stacked'>('centered')
  const [textColor, setTextColor] = useState('#F9FAFB')
  const [accentColor, setAccentColor] = useState('#5B8CFF')
  const [backgroundColor, setBackgroundColor] = useState('#111827')
  const [imagePrompt, setImagePrompt] = useState('')
  const [kenBurns, setKenBurns] = useState(true)
  const inputRef = useRef<HTMLInputElement>(null)
  const overlayRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const timer = setTimeout(() => inputRef.current?.focus(), 50)
    return () => clearTimeout(timer)
  }, [tab])

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !submitting) onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose, submitting])

  const canSubmit = tab === 'scene_card' ? text.trim().length > 0 : imagePrompt.trim().length > 0

  const handleOverlayClick = (event: React.MouseEvent) => {
    if (event.target === overlayRef.current && !submitting) {
      onClose()
    }
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!canSubmit || submitting) return
    if (tab === 'scene_card') {
      await onSubmit({
        type: 'scene_card',
        text: text.trim(),
        duration,
        insert_after: insertAfter,
        style: {
          layout_preset: layoutPreset,
          text_color: textColor,
          accent_color: accentColor,
          background_color: backgroundColor,
          background_mode: 'color',
          text_alignment: layoutPreset === 'hero-right' ? 'right' : layoutPreset === 'hero-left' ? 'left' : 'center',
        },
      })
      return
    }
    await onSubmit({
      type: 'image_card',
      text: text.trim() || null,
      duration,
      insert_after: insertAfter,
      image_prompt: imagePrompt.trim(),
      ken_burns: kenBurns,
    })
  }

  return (
    <div className="modal-overlay" ref={overlayRef} onClick={handleOverlayClick}>
      <div className="modal" role="dialog" aria-modal="true">
        <div className="modal-header">
          <h2 className="modal-title">Add Beat</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close modal" disabled={submitting}>
            <X size={18} />
          </button>
        </div>

        <form className="modal-body" onSubmit={handleSubmit}>
          <div className="media-tabs" style={{ marginBottom: 12 }}>
            <button type="button" className={`media-tab ${tab === 'scene_card' ? 'active' : ''}`} onClick={() => setTab('scene_card')} disabled={submitting}>
              <Plus size={11} /> Scene Card
            </button>
            <button type="button" className={`media-tab ${tab === 'image_card' ? 'active' : ''}`} onClick={() => setTab('image_card')} disabled={submitting}>
              <ImagePlus size={11} /> Generate Image
            </button>
          </div>

          <div className="modal-meta" style={{ marginBottom: 12 }}>
            <span className="modal-meta-item">Insert after: {insertAfter ?? 'start'}</span>
          </div>

          {tab === 'scene_card' ? (
            <>
              <label className="modal-label" htmlFor="beat-text">Text</label>
              <input
                ref={inputRef}
                id="beat-text"
                className="modal-input"
                type="text"
                value={text}
                onChange={(event) => setText(event.target.value)}
                placeholder="Results that closed the loop"
                autoComplete="off"
              />
            </>
          ) : (
            <>
              <label className="modal-label" htmlFor="image-prompt">Image Prompt</label>
              <textarea
                id="image-prompt"
                className="modal-textarea"
                value={imagePrompt}
                onChange={(event) => setImagePrompt(event.target.value)}
                placeholder="A dramatic product montage with bright UI reflections and cinematic depth"
                rows={4}
              />
              <label className="modal-label" htmlFor="image-caption">
                Optional Caption <span className="modal-label-optional">(optional)</span>
              </label>
              <input
                ref={inputRef}
                id="image-caption"
                className="modal-input"
                type="text"
                value={text}
                onChange={(event) => setText(event.target.value)}
                placeholder="Launch moment"
                autoComplete="off"
              />
            </>
          )}

          <label className="modal-label" htmlFor="beat-duration">Duration ({duration}s)</label>
          <input
            id="beat-duration"
            type="range"
            min={1}
            max={10}
            step={1}
            value={duration}
            onChange={(event) => setDuration(Number(event.target.value))}
          />

          {tab === 'scene_card' ? (
            <>
              <label className="modal-label" htmlFor="layout-preset">Layout</label>
              <select
                id="layout-preset"
                className="modal-input"
                value={layoutPreset}
                onChange={(event) => setLayoutPreset(event.target.value as typeof layoutPreset)}
              >
                <option value="centered">Centered</option>
                <option value="hero-left">Hero Left</option>
                <option value="hero-right">Hero Right</option>
                <option value="stacked">Stacked</option>
              </select>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginTop: 8 }}>
                <label className="modal-label">
                  Text Color
                  <input type="color" value={textColor} onChange={(event) => setTextColor(event.target.value)} style={{ display: 'block', width: '100%', marginTop: 6 }} />
                </label>
                <label className="modal-label">
                  Accent
                  <input type="color" value={accentColor} onChange={(event) => setAccentColor(event.target.value)} style={{ display: 'block', width: '100%', marginTop: 6 }} />
                </label>
                <label className="modal-label">
                  Background
                  <input type="color" value={backgroundColor} onChange={(event) => setBackgroundColor(event.target.value)} style={{ display: 'block', width: '100%', marginTop: 6 }} />
                </label>
              </div>
            </>
          ) : (
            <label className="modal-label" style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8 }}>
              <input type="checkbox" checked={kenBurns} onChange={(event) => setKenBurns(event.target.checked)} />
              Ken Burns zoom
            </label>
          )}

          <div className="modal-footer">
            <button type="button" className="modal-btn modal-btn-cancel" onClick={onClose} disabled={submitting}>
              Cancel
            </button>
            <button type="submit" className="modal-btn modal-btn-primary" disabled={!canSubmit || submitting}>
              {submitting ? (tab === 'image_card' ? 'Generating image...' : 'Creating beat...') : (tab === 'image_card' ? 'Generate Image Beat' : 'Add Scene Card')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
