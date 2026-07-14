import { api } from './client'

export interface SettingsMap {
  [key: string]: string
}

export const settingsApi = {
  getAll: () => api.get<SettingsMap>('/settings'),
  get: (key: string) => api.get<{ key: string; value: string }>(`/settings/${key}`),
  set: (key: string, value: string) => api.put<void>(`/settings/${key}`, { value }),
  setMultiple: (data: SettingsMap) => api.put<void>('/settings', data),
}
