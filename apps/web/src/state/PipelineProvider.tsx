import { useReducer, useRef, type ReactNode } from 'react'
import { DispatchContext, initialState, PipelineContext, reducer, VideoRefContext } from './pipelineStore'

export function PipelineProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState)
  const videoRef = useRef<HTMLVideoElement | null>(null)

  return (
    <PipelineContext.Provider value={state}>
      <DispatchContext.Provider value={dispatch}>
        <VideoRefContext.Provider value={videoRef}>
          {children}
        </VideoRefContext.Provider>
      </DispatchContext.Provider>
    </PipelineContext.Provider>
  )
}
