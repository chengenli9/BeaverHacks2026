import { useState, useEffect, useCallback } from 'react'

export interface RouteMatch {
  page: 'home' | 'project'
  projectId?: string
}

function parseHash(hash: string): RouteMatch {
  const h = hash.replace(/^#\/?/, '')

  // #/project/:id
  const projectMatch = h.match(/^project\/([^/]+)/)
  if (projectMatch) {
    return { page: 'project', projectId: projectMatch[1] }
  }

  // #/project (dashboard with no specific project)
  if (h === 'project' || h === 'project/') {
    return { page: 'project' }
  }

  return { page: 'home' }
}

export function useRoute(): RouteMatch {
  const [route, setRoute] = useState<RouteMatch>(() => parseHash(window.location.hash))

  useEffect(() => {
    const handler = () => setRoute(parseHash(window.location.hash))
    window.addEventListener('hashchange', handler)
    return () => window.removeEventListener('hashchange', handler)
  }, [])

  return route
}

export function navigate(path: string) {
  window.location.hash = path
}

export function useNavigate() {
  return useCallback((path: string) => navigate(path), [])
}
