import { api } from './client'

export interface Execution {
  id: number
  preset_id: number
  preset_name?: string
  game_name?: string
  status: 'running' | 'paused' | 'completed' | 'stopped' | 'error'
  started_at: string
  finished_at: string | null
  duration_ms: number | null
  error_message: string | null
}

export interface ExecutionStep {
  id: number
  execution_id: number
  step_order: number
  node_id: string
  node_type: string
  status: string
  input_data: unknown
  output_data: unknown
  started_at: string
  finished_at: string | null
}

export interface ExecQueryParams {
  game_id?: number
  preset_id?: number
  status?: string
  page?: number
  page_size?: number
}

export const executionsApi = {
  list: (params?: ExecQueryParams) => {
    const query = params
      ? '?' + new URLSearchParams(
          Object.entries(params).filter(([_, v]) => v !== undefined).map(([k, v]) => [k, String(v)])
        ).toString()
      : ''
    return api.get<{ items: Execution[]; total: number }>(`/executions${query}`)
  },
  get: (id: number) => api.get<Execution>(`/executions/${id}`),
  getSteps: (executionId: number) => api.get<ExecutionStep[]>(`/executions/${executionId}/steps`),
  delete: (id: number) => api.delete<void>(`/executions/${id}`),
}
