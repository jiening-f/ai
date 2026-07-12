import { api } from './client'

export interface Game {
  id: number
  name: string
  window_title: string
  window_class: string
  created_at: string
  updated_at: string
  preset_count?: number
}

export interface GameFormData {
  name: string
  window_title: string
  window_class: string
}

export const gamesApi = {
  list: () => api.get<Game[]>('/games'),
  get: (id: number) => api.get<Game>(`/games/${id}`),
  create: (data: GameFormData) => api.post<Game>('/games', data),
  update: (id: number, data: Partial<GameFormData>) => api.put<Game>(`/games/${id}`, data),
  delete: (id: number) => api.delete<void>(`/games/${id}`),
}
