import { api } from './client'

export interface Preset {
  id: number
  game_id: number
  name: string
  description: string
  flow_data: unknown
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface PresetFormData {
  name: string
  description: string
  flow_data?: unknown
  is_active?: boolean
}

export const presetsApi = {
  listByGame: (gameId: number) => api.get<Preset[]>(`/presets?game_id=${gameId}`),
  get: (id: number) => api.get<Preset>(`/presets/${id}`),
  create: (gameId: number, data: PresetFormData) =>
    api.post<Preset>('/presets', { ...data, game_id: gameId }),
  update: (id: number, data: Partial<PresetFormData>) =>
    api.put<Preset>(`/presets/${id}`, data),
  delete: (id: number) => api.delete<void>(`/presets/${id}`),
}
