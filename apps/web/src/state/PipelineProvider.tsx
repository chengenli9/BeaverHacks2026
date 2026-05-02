import { useReducer, type ReactNode } from 'react'
import { DispatchContext, initialState, PipelineContext, reducer } from './pipelineStore'

export function PipelineProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState)

  return (
    <PipelineContext.Provider value={state}>
      <DispatchContext.Provider value={dispatch}>{children}</DispatchContext.Provider>
    </PipelineContext.Provider>
  )
}
