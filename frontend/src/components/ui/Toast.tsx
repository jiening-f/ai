import { useState, useCallback, createContext, useContext, ReactNode } from 'react'

interface ToastItem {
  id: number
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  description?: string
}

interface ToastContextValue {
  toast: (t: Omit<ToastItem, 'id'>) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

let nextId = 1

function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const addToast = useCallback((t: Omit<ToastItem, 'id'>) => {
    const id = nextId++
    setToasts((prev) => [...prev.slice(-4), { ...t, id }])
    if (t.type !== 'error') {
      setTimeout(() => {
        setToasts((prev) => prev.filter((item) => item.id !== id))
      }, t.type === 'success' ? 3000 : t.type === 'warning' ? 5000 : 4000)
    }
  }, [])

  const removeToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  return (
    <ToastContext.Provider value={{ toast: addToast }}>
      {children}
      <div className="toast-container">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.type}`}>
            <span className="toast-icon">
              {t.type === 'success' ? '✓' : t.type === 'error' ? '✕' : t.type === 'warning' ? '!' : 'ℹ'}
            </span>
            <div className="toast-content">
              <div className="toast-title">{t.title}</div>
              {t.description && <div className="toast-description">{t.description}</div>}
            </div>
            <button className="toast-close" onClick={() => removeToast(t.id)}>✕</button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}

export { ToastProvider, useToast }
