/**
 * Plan diff computation — compares current plan with proposed plan and
 * produces a structured diff for the UI to render.
 */
import type { Beat, Plan } from '../types/api'

export interface BeatChange {
  beatId: string
  field: string
  oldValue: unknown
  newValue: unknown
}

export interface PlanDiff {
  added: Beat[]
  removed: Beat[]
  modified: { beat: Beat; changes: BeatChange[] }[]
  unchanged: Beat[]
  reordered: boolean
  currentDuration: number
  proposedDuration: number
  durationDelta: number
}

function beatDuration(beat: Beat): number {
  return beat.duration ?? 0
}

function totalDuration(beats: Beat[]): number {
  return beats.reduce((sum, b) => sum + beatDuration(b), 0)
}

function diffBeats(a: Beat, b: Beat): BeatChange[] {
  const changes: BeatChange[] = []
  const fields: (keyof Beat)[] = ['goal', 'onscreen_text', 'narration', 'duration', 'type', 'image_prompt', 'ken_burns']
  for (const field of fields) {
    const av = JSON.stringify(a[field]) ?? 'null'
    const bv = JSON.stringify(b[field]) ?? 'null'
    if (av !== bv) {
      changes.push({ beatId: a.beat_id, field, oldValue: a[field], newValue: b[field] })
    }
  }
  // Diff style if present
  if (a.style || b.style) {
    const styleFields = ['font_family', 'font_variant', 'text_color', 'accent_color', 'background_mode', 'background_color', 'text_alignment', 'layout_preset', 'animation_preset'] as const
    for (const sf of styleFields) {
      const av = a.style?.[sf] ?? null
      const bv = b.style?.[sf] ?? null
      if (JSON.stringify(av) !== JSON.stringify(bv)) {
        changes.push({ beatId: a.beat_id, field: `style.${sf}`, oldValue: av, newValue: bv })
      }
    }
  }
  return changes
}

export function computePlanDiff(current: Plan, proposed: Plan): PlanDiff {
  const currentById = new Map(current.beats.map((b) => [b.beat_id, b]))
  const proposedById = new Map(proposed.beats.map((b) => [b.beat_id, b]))

  const added: Beat[] = []
  const removed: Beat[] = []
  const modified: { beat: Beat; changes: BeatChange[] }[] = []
  const unchanged: Beat[] = []

  // Find removed beats (in current but not in proposed)
  for (const beat of current.beats) {
    if (!proposedById.has(beat.beat_id)) {
      removed.push(beat)
    }
  }

  // Categorize proposed beats
  for (const beat of proposed.beats) {
    const existing = currentById.get(beat.beat_id)
    if (!existing) {
      added.push(beat)
    } else {
      const changes = diffBeats(existing, beat)
      if (changes.length > 0) {
        modified.push({ beat, changes })
      } else {
        unchanged.push(beat)
      }
    }
  }

  // Check if order changed (for beats that exist in both)
  const currentIds = current.beats.map((b) => b.beat_id).filter((id) => proposedById.has(id))
  const proposedIds = proposed.beats.map((b) => b.beat_id).filter((id) => currentById.has(id))
  const reordered = currentIds.length > 1 && JSON.stringify(currentIds) !== JSON.stringify(proposedIds)

  const curDur = totalDuration(current.beats)
  const propDur = totalDuration(proposed.beats)

  return {
    added,
    removed,
    modified,
    unchanged,
    reordered,
    currentDuration: curDur,
    proposedDuration: propDur,
    durationDelta: propDur - curDur,
  }
}

export function formatDuration(seconds: number): string {
  const s = Math.round(seconds)
  const m = Math.floor(s / 60)
  const sec = s % 60
  return m > 0 ? `${m}:${sec.toString().padStart(2, '0')}` : `${sec}s`
}

export interface MergedBeat {
  beat: Beat
  status: 'added' | 'removed' | 'modified' | 'unchanged' | 'moved'
  changes: BeatChange[]
}

export function mergedView(diff: PlanDiff, proposedBeats?: Beat[]): MergedBeat[] {
  const result: MergedBeat[] = []
  const modifiedMap = new Map(diff.modified.map((m) => [m.beat.beat_id, m.changes]))
  const addedSet = new Set(diff.added.map((b) => b.beat_id))

  // Show removed beats first (with strikethrough)
  for (const beat of diff.removed) {
    result.push({ beat, status: 'removed', changes: [] })
  }

  // Iterate proposed beats in their correct order
  const orderedBeats = proposedBeats ?? [...diff.added, ...diff.modified.map((m) => m.beat), ...diff.unchanged]
  for (const beat of orderedBeats) {
    const changes = modifiedMap.get(beat.beat_id) ?? []
    let status: MergedBeat['status'] = 'unchanged'
    if (addedSet.has(beat.beat_id)) status = 'added'
    else if (modifiedMap.has(beat.beat_id)) status = 'modified'

    result.push({ beat, status, changes })
  }

  return result
}

export function diffSummary(diff: PlanDiff): string {
  const parts: string[] = []
  if (diff.added.length) parts.push(`+${diff.added.length} added`)
  if (diff.removed.length) parts.push(`-${diff.removed.length} removed`)
  if (diff.modified.length) parts.push(`~${diff.modified.length} modified`)
  if (diff.reordered) parts.push('reordered')
  if (parts.length === 0) return 'No changes'
  return parts.join(', ')
}
