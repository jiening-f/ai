import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { gamesApi, Game, GameFormData } from '../api/games'
import Modal from '../components/ui/Modal'
import ConfirmDialog from '../components/ui/ConfirmDialog'
import { useToast } from '../components/ui/Toast'

function GameManager() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [games, setGames] = useState<Game[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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
        toast({ type: 'success', title: '游戏已添加' })
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
        <h1>游戏管理</h1>
        <div className="loading"><div className="spinner" /> 加载中...</div>
      </div>
    )
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>游戏管理</h1>
        <button className="btn btn-primary" onClick={openAddForm}>
          + 添加游戏
        </button>
      </div>

      {error && (
        <div className="error-state mb-md">
          <span>⚠️</span> 后端连接失败，显示示例数据
        </div>
      )}

      {games.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🎮</div>
          <div className="empty-state-text">暂无游戏配置</div>
          <button className="btn btn-primary btn-sm" onClick={openAddForm}>
            添加第一个游戏
          </button>
        </div>
      ) : (
        <div className="game-card-grid">
          {games.map((game) => (
            <div
              key={game.id}
              className="game-card"
              onClick={() => handleCardClick(game)}
            >
              <div className="game-card-title">{game.name}</div>
              {game.window_title && (
                <div className="game-card-subtitle">{game.window_title}</div>
              )}
              <div className="game-card-stats">
                <span>📝 {game.preset_count ?? 0} 个预设</span>
                <span>🪟 {game.window_class || '-'}</span>
              </div>
              <div className="game-card-actions" onClick={(e) => e.stopPropagation()}>
                <button className="btn btn-sm" onClick={() => openEditForm(game)}>
                  编辑
                </button>
                <button className="btn btn-sm btn-danger" onClick={() => setDeleteTarget(game)}>
                  删除
                </button>
              </div>
            </div>
          ))}
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
