import { useState } from 'react'
import {
  FolderOpen, Film, Image, Music, FileText, Upload, ChevronRight, ChevronDown, Plus
} from 'lucide-react'
import { usePipeline } from '../state/pipelineStore'

interface FileNode {
  name: string
  type: 'folder' | 'video' | 'image' | 'audio' | 'json' | 'file'
  children?: FileNode[]
  size?: string
  duration?: string
}

const DEMO_TREE: FileNode[] = [
  {
    name: 'source', type: 'folder', children: [
      { name: 'demo_footage.mp4', type: 'video', size: '24.3 MB', duration: '00:42' },
    ]
  },
  {
    name: 'assets', type: 'folder', children: [
      { name: 'backgrounds', type: 'folder', children: [
        { name: 'bg_001.png', type: 'image', size: '340 KB' },
        { name: 'bg_005.png', type: 'image', size: '285 KB' },
      ]},
      { name: 'tts', type: 'folder', children: [
        { name: 'tts_002.wav', type: 'audio', size: '1.2 MB', duration: '00:06' },
        { name: 'tts_003.wav', type: 'audio', size: '1.4 MB', duration: '00:07' },
        { name: 'tts_004.wav', type: 'audio', size: '1.3 MB', duration: '00:06' },
      ]},
      { name: 'fonts', type: 'folder', children: [
        { name: 'Inter-Bold.ttf', type: 'file', size: '312 KB' },
      ]},
    ]
  },
  {
    name: 'manifests', type: 'folder', children: [
      { name: 'plan.json', type: 'json', size: '1.7 KB' },
      { name: 'block_manifest.json', type: 'json', size: '2.0 KB' },
      { name: 'critic_suggestions.json', type: 'json', size: '779 B' },
    ]
  },
  {
    name: 'blocks', type: 'folder', children: [
      { name: '001_title.mp4', type: 'video', size: '1.1 MB', duration: '00:03' },
      { name: '002_problem.mp4', type: 'video', size: '4.2 MB', duration: '00:06' },
      { name: '003_pipeline.mp4', type: 'video', size: '5.8 MB', duration: '00:08' },
      { name: '004_approval.mp4', type: 'video', size: '4.9 MB', duration: '00:07' },
      { name: '005_end.mp4', type: 'video', size: '1.0 MB', duration: '00:03' },
    ]
  },
  {
    name: 'renders', type: 'folder', children: [
      { name: 'final_render.mp4', type: 'video', size: '1.8 MB', duration: '00:29' },
    ]
  },
]

const FILE_ICONS: Record<string, typeof Film> = {
  video: Film, image: Image, audio: Music, json: FileText, file: FileText, folder: FolderOpen
}

function FileTreeNode({ node, depth = 0 }: { node: FileNode; depth?: number }) {
  const [open, setOpen] = useState(depth < 1)
  const Icon = FILE_ICONS[node.type] ?? FileText
  const isFolder = node.type === 'folder'

  return (
    <div>
      <div
        className={`file-node ${isFolder ? 'folder' : 'leaf'}`}
        style={{ paddingLeft: 8 + depth * 14 }}
        onClick={() => isFolder && setOpen(!open)}
      >
        {isFolder && (open ? <ChevronDown size={12} /> : <ChevronRight size={12} />)}
        <Icon size={13} className={`file-icon file-icon-${node.type}`} />
        <span className="file-name">{node.name}</span>
        {node.duration && <span className="file-meta">{node.duration}</span>}
        {!node.duration && node.size && <span className="file-meta">{node.size}</span>}
      </div>
      {isFolder && open && node.children?.map((child) => (
        <FileTreeNode key={child.name} node={child} depth={depth + 1} />
      ))}
    </div>
  )
}

export function MediaBrowser() {
  const { projectId } = usePipeline()
  const [tab, setTab] = useState<'import' | 'media'>('media')

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
          <div className="import-zone" id="import-zone">
            <Upload size={28} />
            <span>Drop files here</span>
            <span className="import-hint">or click to browse</span>
            <button className="stage-btn stage-btn-primary" style={{ marginTop: 12 }}>
              <Plus size={12} /> Add Media
            </button>
          </div>
        )}
        {tab === 'media' && (
          projectId ? (
            <div className="file-tree">
              {DEMO_TREE.map((node) => <FileTreeNode key={node.name} node={node} />)}
            </div>
          ) : (
            <div className="empty-state" style={{ padding: '30px 16px' }}>
              <FolderOpen size={28} />
              <h3>No Project</h3>
              <p>Open a project to browse files</p>
            </div>
          )
        )}
      </div>
    </div>
  )
}
