import { useState, useCallback } from 'react'
import { api, ApiError } from '../api/client'

interface UseApiState<T> {
  data: T | null
  loading: boolean
  error: string | null
}

export function useApi<T>() {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: false,
    error: null,
  })

  const fetchData = useCallback(async (path: string) => {
    setState((prev) => ({ ...prev, loading: true, error: null }))
    try {
      const data = await api.get<T>(path)
      setState({ data, loading: false, error: null })
      return data
    } catch (e) {
      const message = e instanceof ApiError ? e.message : '未知错误'
      setState((prev) => ({ ...prev, loading: false, error: message }))
      return null
    }
  }, [])

  return { ...state, fetchData }
}
