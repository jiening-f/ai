import { api } from './client'
import { ApiError } from './client'

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
  install: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const res = await fetch('/api/plugins/install', { method: 'POST', body: formData })
    const json = await res.json()
    if (!json.success) {
      throw new ApiError(res.status, json.error || '插件安装失败')
    }
    return json.data
  },
  uninstall: (id: number) => api.delete<void>(`/plugins/${id}`),
  toggle: (id: number, enabled: boolean) => api.put<Plugin>(`/plugins/${id}`, { enabled }),
}
