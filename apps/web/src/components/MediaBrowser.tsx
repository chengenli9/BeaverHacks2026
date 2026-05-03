import { useRef, useState } from 'react'
import {
  ChevronDown, ChevronRight, FileText, Film, FolderOpen, Image, Music, Plus, Upload,
} from 'lucide-react'
import { usePipeline, usePipelineActions } from '../state/pipelineStore'
import type { MediaNode } from '../types/api'

const FILE_ICONS: Record<string, typeof Film> = {
  video: Film,
  image: Image,
  audio: Music,
  json: FileText,
  file: FileText,
  folder: FolderOpen,
}

function formatSize(bytes?: number): string | null {
  if (!bytes) return null
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDuration(seconds?: number): string | null {
  if (seconds == null) return null
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
}

function FileTreeNode({ node, depth = 0 }: { node: MediaNode; depth?: number }) {
  const { selectedMedia } = usePipeline()
  const { selectMedia } = usePipelineActions()
  const [open, setOpen] = useState(depth < 1)
  const Icon = FILE_ICONS[node.type] ?? FileText
  const isFolder = node.type === 'folder'
  const duration = formatDuration(node.duration)
  const size = formatSize(node.size)

  const handleClick = () => {
    if (isFolder) {
      setOpen(!open)
      return
    }
    selectMedia(node)
  }

  return (
    <div>
      <button
        type="button"
        className={`file-node ${isFolder ? 'folder' : 'leaf'} ${selectedMedia?.path === node.path ? 'selected' : ''}`}
        style={{ paddingLeft: 8 + depth * 14 }}
        onClick={handleClick}
      >
        {isFolder && (open ? <ChevronDown size={12} /> : <ChevronRight size={12} />)}
        <Icon size={13} className={`file-icon file-icon-${node.type}`} />
        <span className="file-name">{node.name}</span>
        {duration && <span className="file-meta">{duration}</span>}
        {!duration && size && <span className="file-meta">{size}</span>}
      </button>
      {isFolder && open && node.children?.map((child) => (
        <FileTreeNode key={child.path} node={child} depth={depth + 1} />
      ))}
    </div>
  )
}

export function MediaBrowser() {
  const { projectId, mediaTree } = usePipeline()
  const { importMedia } = usePipelineActions()
  const [tab, setTab] = useState<'import' | 'media'>('media')
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFiles = async (fileList: FileList | null) => {
    const files = Array.from(fileList ?? [])
    await importMedia(files)
    if (files.length > 0) setTab('media')
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <div className="panel media-browser" id="media-browser">
      <div className="panel-header">
        <div className="media-tabs">
          <button className={`media-tab ${tab === 'media' ? 'active' : ''}`} onClick={() => setTab('media')}>
            Media
          </button>
          <button className={`media-tab ${tab === 'import' ? 'active' : ''}`} onClick={() => setTab('import')}>
            Import
          </button>
        </div>
      </div>
      <div className="panel-content">
        {tab === 'import' && (
          <div
            className={`import-zone ${dragging ? 'dragging' : ''}`}
            id="import-zone"
            onClick={() => inputRef.current?.click()}
            onDragEnter={(event) => {
              event.preventDefault()
              setDragging(true)
            }}
            onDragOver={(event) => event.preventDefault()}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => {
              event.preventDefault()
              setDragging(false)
              void handleFiles(event.dataTransfer.files)
            }}
          >
            <Upload size={28} />
            <span>Drop files here</span>
            <span className="import-hint">or click to browse</span>
            <input
              ref={inputRef}
              type="file"
              accept="video/*,.mp4,.mov,.m4v,.webm,.mkv,.avi"
              multiple
              aria-label="Add media files"
              className="visually-hidden"
              onChange={(event) => void handleFiles(event.currentTarget.files)}
            />
            <button className="stage-btn stage-btn-primary" style={{ marginTop: 12 }} type="button">
              <Plus size={12} /> Add Media
            </button>
          </div>
        )}
        {tab === 'media' && (
          projectId ? (
            <div className="file-tree">
              {mediaTree?.files.length ? (
                mediaTree.files.map((node) => <FileTreeNode key={node.path} node={node} />)
              ) : (
                <div className="empty-state" style={{ padding: '30px 16px' }}>
                  <FolderOpen size={28} />
                  <h3>No Media</h3>
                  <p>Import footage to start building this project</p>
                </div>
              )}
            </div>
          ) : (
            <div className="empty-state" style={{ padding: '30px 16px' }}>
              <FolderOpen size={28} />
              <h3>No Project</h3>
              <p>Open or create a project to browse files</p>
            </div>
          )
        )}
      </div>
    </div>
  )
}
