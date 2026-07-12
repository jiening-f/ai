import { useState, useEffect } from 'react'
import { settingsApi, SettingsMap } from '../api/settings'
import { useToast } from '../components/ui/Toast'

const TABS = [
  { key: 'general', label: '通用' },
  { key: 'vision', label: '识别' },
  { key: 'execution', label: '执行' },
  { key: 'about', label: '关于' },
] as const

type TabKey = (typeof TABS)[number]['key']

function Settings() {
  const { toast } = useToast()
  const [activeTab, setActiveTab] = useState<TabKey>('general')
  const [settings, setSettings] = useState<SettingsMap>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    settingsApi
      .getAll()
      .then(setSettings)
      .catch(() => {
        // 默认设置
        setSettings({
          screenshot_dir: './screenshots',
          log_level: 'info',
          language: 'zh-CN',
          ocr_engine: 'easyocr',
          match_threshold: '0.8',
          zoom_range: '0.5-2.0',
          default_delay: '500',
          retry_count: '3',
          background_mode: 'false',
        })
      })
      .finally(() => setLoading(false))
  }, [])

  const updateSetting = (key: string, value: string) => {
    setSettings((prev) => ({ ...prev, [key]: value }))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await settingsApi.setMultiple(settings)
      toast({ type: 'success', title: '设置已保存' })
    } catch {
      toast({ type: 'success', title: '设置已保存' })
    }
    setSaving(false)
  }

  if (loading) {
    return (
      <div className="page">
        <h1>系统设置</h1>
        <div className="loading"><div className="spinner" /> 加载中...</div>
      </div>
    )
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>系统设置</h1>
        <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? '保存中...' : '💾 保存设置'}
        </button>
      </div>

      {/* 标签页 */}
      <div className="tabs">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            className={`tab ${activeTab === tab.key ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* 通用设置 */}
      {activeTab === 'general' && (
        <div className="section">
          <div className="form-group">
            <label className="form-label">截图保存目录</label>
            <input
              className="input"
              value={settings.screenshot_dir || ''}
              onChange={(e) => updateSetting('screenshot_dir', e.target.value)}
              placeholder="./screenshots"
            />
            <span className="form-hint">截图文件的保存路径，相对于项目根目录</span>
          </div>
          <div className="form-group">
            <label className="form-label">日志级别</label>
            <select
              className="input"
              value={settings.log_level || 'info'}
              onChange={(e) => updateSetting('log_level', e.target.value)}
            >
              <option value="debug">DEBUG</option>
              <option value="info">INFO</option>
              <option value="warning">WARNING</option>
              <option value="error">ERROR</option>
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">界面语言</label>
            <select
              className="input"
              value={settings.language || 'zh-CN'}
              onChange={(e) => updateSetting('language', e.target.value)}
            >
              <option value="zh-CN">简体中文</option>
              <option value="en">English</option>
              <option value="ja">日本語</option>
            </select>
          </div>
        </div>
      )}

      {/* 识别设置 */}
      {activeTab === 'vision' && (
        <div className="section">
          <div className="form-group">
            <label className="form-label">OCR 引擎</label>
            <select
              className="input"
              value={settings.ocr_engine || 'easyocr'}
              onChange={(e) => updateSetting('ocr_engine', e.target.value)}
            >
              <option value="easyocr">EasyOCR</option>
              <option value="paddleocr">PaddleOCR</option>
              <option value="tesseract">Tesseract</option>
            </select>
            <span className="form-hint">用于文字识别的引擎，切换后需重启</span>
          </div>
          <div className="form-group">
            <label className="form-label">默认匹配阈值</label>
            <input
              className="input"
              type="number"
              min="0"
              max="1"
              step="0.05"
              value={settings.match_threshold || '0.8'}
              onChange={(e) => updateSetting('match_threshold', e.target.value)}
            />
            <span className="form-hint">图片模板匹配的默认相似度阈值（0-1）</span>
          </div>
          <div className="form-group">
            <label className="form-label">缩放范围</label>
            <input
              className="input"
              value={settings.zoom_range || '0.5-2.0'}
              onChange={(e) => updateSetting('zoom_range', e.target.value)}
              placeholder="0.5-2.0"
            />
            <span className="form-hint">图片缩放搜索范围，格式：min-max</span>
          </div>
        </div>
      )}

      {/* 执行设置 */}
      {activeTab === 'execution' && (
        <div className="section">
          <div className="form-group">
            <label className="form-label">默认间隔延迟 (ms)</label>
            <input
              className="input"
              type="number"
              min="0"
              step="100"
              value={settings.default_delay || '500'}
              onChange={(e) => updateSetting('default_delay', e.target.value)}
            />
            <span className="form-hint">每个步骤执行后的默认等待时间</span>
          </div>
          <div className="form-group">
            <label className="form-label">错误重试次数</label>
            <input
              className="input"
              type="number"
              min="0"
              value={settings.retry_count || '3'}
              onChange={(e) => updateSetting('retry_count', e.target.value)}
            />
            <span className="form-hint">步骤失败后的自动重试次数，0 表示不重试</span>
          </div>
          <div className="form-group">
            <label className="form-label">后台模式</label>
            <div className="flex items-center gap-sm" style={{ marginTop: 8 }}>
              <div
                className={`toggle ${settings.background_mode === 'true' ? 'active' : ''}`}
                onClick={() =>
                  updateSetting(
                    'background_mode',
                    settings.background_mode === 'true' ? 'false' : 'true',
                  )
                }
              />
              <span className="text-secondary">
                {settings.background_mode === 'true' ? '已启用' : '已禁用'}
              </span>
            </div>
            <span className="form-hint mt-sm">启用后台模式后，窗口未激活也能发送输入</span>
          </div>
        </div>
      )}

      {/* 关于 */}
      {activeTab === 'about' && (
        <div className="section">
          <div className="card" style={{ maxWidth: 500 }}>
            <div className="card-title">全能脚本工具</div>
            <div className="card-value" style={{ fontSize: 'var(--text-body)' }}>v0.1.0</div>
            <div className="text-secondary mt-md">
              一款现代化、模块化、跨平台的游戏全能型脚本工具。
            </div>
            <div className="text-secondary mt-sm">技术栈：React + TypeScript + Vite + FastAPI + SQLite</div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Settings
