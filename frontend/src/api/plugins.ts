import { api } from './client'

export interface Plugin {
  id: number
  name: string
  version: string
  author: string
  description: string
  enabled: boolean
  installed_at: string
}

export const pluginsApi = {
  list: () => api.get<Plugin[]>('/plugins'),
  install: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return fetch('/api/plugins/install', { method: 'POST', body: formData }).then((r) => r.json())
  },
  uninstall: (id: number) => api.delete<void>(`/plugins/${id}`),
  toggle: (id: number, enabled: boolean) => api.put<Plugin>(`/plugins/${id}`, { enabled }),
}
