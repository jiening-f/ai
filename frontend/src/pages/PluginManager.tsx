import { useState, useEffect, useRef } from 'react'
import { pluginsApi, Plugin } from '../api/plugins'
import ConfirmDialog from '../components/ui/ConfirmDialog'
import { useToast } from '../components/ui/Toast'

function PluginManager() {
  const { toast } = useToast()
  const [plugins, setPlugins] = useState<Plugin[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // 卸载确认
  const [uninstallTarget, setUninstallTarget] = useState<Plugin | null>(null)

  const loadPlugins = () => {
    setLoading(true)
    setError(null)
    pluginsApi
      .list()
      .then(setPlugins)
      .catch((err) => {
        setError(err.message)
        setPlugins([])
      })
      .finally(() => setLoading(false))
  }

  useEffect(loadPlugins, [])

  const handleInstall = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (!file.name.endsWith('.py') && !file.name.endsWith('.zip')) {
      toast({ type: 'error', title: '不支持的文件格式', description: '请选择 .py 或 .zip 文件' })
      return
    }

    try {
      await pluginsApi.install(file)
      toast({ type: 'success', title: `插件"${file.name}"安装成功` })
      loadPlugins()
    } catch (err) {
      toast({ type: 'error', title: `安装失败`, description: err instanceof Error ? err.message : '未知错误' })
      loadPlugins()
    }
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleUninstall = async () => {
    if (!uninstallTarget) return
    try {
      await pluginsApi.uninstall(uninstallTarget.id)
      toast({ type: 'success', title: `已卸载"${uninstallTarget.name}"` })
    } catch (err) {
      toast({ type: 'error', title: '卸载失败', description: err instanceof Error ? err.message : '未知错误' })
    }
    setUninstallTarget(null)
    loadPlugins()
  }

  const handleToggle = async (plugin: Plugin) => {
    try {
      await pluginsApi.toggle(plugin.id, !plugin.enabled)
      setPlugins((prev) =>
        prev.map((p) => (p.id === plugin.id ? { ...p, enabled: !p.enabled } : p)),
      )
      toast({
        type: 'info',
        title: plugin.enabled ? `已禁用"${plugin.name}"` : `已启用"${plugin.name}"`,
      })
    } catch (err) {
      toast({ type: 'error', title: '操作失败', description: err instanceof Error ? err.message : '未知错误' })
    }
  }

  if (loading) {
    return (
      <div className="page">
        <h1>插件管理</h1>
        <div className="loading"><div className="spinner" /> 加载中...</div>
      </div>
    )
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>插件管理</h1>
        <button className="btn btn-primary" onClick={handleInstall}>
          + 安装插件
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".py,.zip"
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />
      </div>

      {error && (
        <div className="error-state mb-md">
          <span>⚠️</span> 后端连接失败，插件管理功能受限
        </div>
      )}

      {plugins.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🧩</div>
          <div className="empty-state-text">尚未安装任何插件</div>
          <button className="btn btn-primary btn-sm" onClick={handleInstall}>
            安装第一个插件
          </button>
        </div>
      ) : (
        <div className="plugin-card-grid">
          {plugins.map((plugin) => (
            <div key={plugin.id} className="plugin-card">
              <div className="plugin-card-header">
                <div className="plugin-card-name">{plugin.name}</div>
                <div className={`toggle ${plugin.enabled ? 'active' : ''}`}
                     onClick={() => handleToggle(plugin)} />
              </div>
              <div className="plugin-card-meta">
                v{plugin.version} · {plugin.author}
              </div>
              <div className="plugin-card-desc">
                {plugin.description || '暂无描述'}
              </div>
              <div className="plugin-card-footer">
                <span className="text-small text-tertiary">
                  安装于 {new Date(plugin.installed_at).toLocaleDateString('zh-CN')}
                </span>
                <button
                  className="btn btn-sm btn-danger"
                  onClick={() => setUninstallTarget(plugin)}
                >
                  卸载
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <ConfirmDialog
        open={!!uninstallTarget}
        title="卸载插件"
        message={`确定要卸载"${uninstallTarget?.name}"吗？`}
        variant="danger"
        confirmText="卸载"
        onConfirm={handleUninstall}
        onCancel={() => setUninstallTarget(null)}
      />
    </div>
  )
}

export default PluginManager
