import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { gamesApi, Game, GameFormData } from '../api/games'
import Modal from '../components/ui/Modal'
import ConfirmDialog from '../components/ui/ConfirmDialog'
import { useToast } from '../components/ui/Toast'

/** 渐变色头部配色方案 */
const HEADER_GRADIENTS = ['purple', 'blue', 'pink', 'green', 'orange'] as const

function getHeaderColor(index: number): string {
  return HEADER_GRADIENTS[index % HEADER_GRADIENTS.length]
}

function GameManager() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [games, setGames] = useState<Game[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 搜索 & 排序
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState('name')

  // Modal 状态
  const [showForm, setShowForm] = useState(false)
  const [editingGame, setEditingGame] = useState<Game | null>(null)
  const [formData, setFormData] = useState<GameFormData>({ name: '', window_title: '', window_class: '' })

  // 删除确认
  const [deleteTarget, setDeleteTarget] = useState<Game | null>(null)

  const loadGames = () => {
    setLoading(true)
    setError(null)
    gamesApi
      .list()
      .then(setGames)
      .catch((err) => {
        setError(err.message)
        setGames([])
      })
      .finally(() => setLoading(false))
  }

  useEffect(loadGames, [])

  // 过滤 & 排序
  const filteredGames = games
    .filter((g) => g.name.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => {
      if (sortBy === 'name') return a.name.localeCompare(b.name)
      if (sortBy === 'presets') return (b.preset_count ?? 0) - (a.preset_count ?? 0)
      return 0
    })

  const openAddForm = () => {
    setEditingGame(null)
    setFormData({ name: '', window_title: '', window_class: '' })
    setShowForm(true)
  }

  const openEditForm = (game: Game) => {
    setEditingGame(game)
    setFormData({
      name: game.name,
      window_title: game.window_title,
      window_class: game.window_class,
    })
    setShowForm(true)
  }

  const handleSave = async () => {
    if (!formData.name.trim()) {
      toast({ type: 'warning', title: '请输入游戏名称' })
      return
    }
    try {
      if (editingGame) {
        await gamesApi.update(editingGame.id, formData)
        toast({ type: 'success', title: '游戏已更新' })
      } else {
        await gamesApi.create(formData)
        toast({ type: 'success', title: '游戏已添加', description: `${formData.name} 已成功添加` })
      }
      setShowForm(false)
      loadGames()
    } catch (err) {
      toast({ type: 'error', title: '操作失败', description: err instanceof Error ? err.message : '未知错误' })
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    try {
      await gamesApi.delete(deleteTarget.id)
      toast({ type: 'success', title: `已删除 "${deleteTarget.name}"` })
      setDeleteTarget(null)
      loadGames()
    } catch (err) {
      toast({ type: 'error', title: '删除失败', description: err instanceof Error ? err.message : '未知错误' })
    }
  }

  const handleCardClick = (game: Game) => {
    navigate(`/presets/${game.id}`)
  }

  if (loading) {
    return (
      <div className="page">
        <div className="loading" style={{ paddingTop: 80 }}>
          <div className="spinner" /> 加载中...
        </div>
      </div>
    )
  }

  return (
    <div className="page">
      {/* 统计卡片 */}
      <div className="stat-card-grid">
        {[
          { label: '已添加游戏', value: `${games.length}`, icon: '🎮', color: 'purple' },
          { label: '预设总数', value: `${games.reduce((s, g) => s + (g.preset_count ?? 0), 0)}`, icon: '📋', color: 'blue' },
          { label: '今日运行', value: '3', icon: '▶', color: 'green' },
          { label: '活跃游戏', value: `${games.length}`, icon: '🕹', color: 'orange' },
        ].map((stat) => (
          <div className="stat-card" key={stat.label}>
            <div className={`stat-card-icon ${stat.color}`}>{stat.icon}</div>
            <div className="stat-card-body">
              <div className="stat-card-label">{stat.label}</div>
              <div className="stat-card-value">{stat.value}</div>
            </div>
          </div>
        ))}
      </div>

      {/* 搜索栏 */}
      <div className="search-bar">
        <div className="search-input-wrapper">
          <span className="search-icon">🔍</span>
          <input
            className="input"
            placeholder="搜索游戏名称..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select
          className="input"
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          style={{ width: '140px' }}
        >
          <option value="name">按名称排序</option>
          <option value="presets">按预设数排序</option>
        </select>
        <button className="btn btn-primary" onClick={openAddForm}>
          + 添加游戏
        </button>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="error-state mb-md">
          <span>⚠️</span> 后端连接失败，显示示例数据
        </div>
      )}

      {/* 游戏卡片网格 */}
      {filteredGames.length === 0 && !error ? (
        <div className="empty-state">
          <div className="empty-state-icon">🎮</div>
          <div className="empty-state-text">暂无游戏配置</div>
          <button className="btn btn-primary btn-sm" onClick={openAddForm}>
            添加第一个游戏
          </button>
        </div>
      ) : (
        <div className="game-card-grid-new">
          {filteredGames.map((game, index) => (
            <div
              key={game.id}
              className="game-card-new"
              onClick={() => handleCardClick(game)}
            >
              {/* 渐变色头部 */}
              <div className={`game-card-header ${getHeaderColor(index)}`}>
                <span className="game-card-header-icon">🎮</span>
              </div>

              {/* 卡片内容 */}
              <div className="game-card-body">
                <div className="game-card-name">{game.name}</div>
                {game.window_title && (
                  <div className="game-card-window">{game.window_title}</div>
                )}

                <div className="game-card-meta">
                  <span>📋 {game.preset_count ?? 0} 个预设</span>
                  <span>🪟 {game.window_class || '-'}</span>
                </div>
              </div>

              {/* 底部操作 */}
              <div className="game-card-footer" onClick={(e) => e.stopPropagation()}>
                <button className="btn btn-sm" onClick={() => openEditForm(game)}>
                  编辑
                </button>
                <button className="btn btn-sm" onClick={() => handleCardClick(game)}>
                  运行
                </button>
                <button
                  className="btn btn-sm btn-danger"
                  onClick={() => setDeleteTarget(game)}
                >
                  删除
                </button>
              </div>
            </div>
          ))}

          {/* 添加游戏占位卡片 */}
          <div className="add-game-card" onClick={openAddForm}>
            <div className="add-game-card-icon">+</div>
            <div className="add-game-card-text">添加新游戏</div>
          </div>
        </div>
      )}

      {/* 添加/编辑 Modal */}
      <Modal
        open={showForm}
        onClose={() => setShowForm(false)}
        title={editingGame ? '编辑游戏' : '添加游戏'}
        footer={
          <>
            <button className="btn" onClick={() => setShowForm(false)}>
              取消
            </button>
            <button className="btn btn-primary" onClick={handleSave}>
              保存
            </button>
          </>
        }
      >
        <div className="form-group">
          <label className="form-label">游戏名称 *</label>
          <input
            className="input"
            placeholder="例如：原神"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          />
        </div>
        <div className="form-group">
          <label className="form-label">窗口标题</label>
          <input
            className="input"
            placeholder="窗口标题（可选）"
            value={formData.window_title}
            onChange={(e) => setFormData({ ...formData, window_title: e.target.value })}
          />
          <span className="form-hint">留空则自动匹配</span>
        </div>
        <div className="form-group">
          <label className="form-label">窗口类名</label>
          <input
            className="input"
            placeholder="窗口类名（可选）"
            value={formData.window_class}
            onChange={(e) => setFormData({ ...formData, window_class: e.target.value })}
          />
        </div>
      </Modal>

      {/* 删除确认 */}
      <ConfirmDialog
        open={!!deleteTarget}
        title="删除游戏"
        message={`确定要删除"${deleteTarget?.name}"吗？关联的预设配置也将被删除。`}
        variant="danger"
        confirmText="删除"
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  )
}

export default GameManager
