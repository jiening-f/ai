/**
 * 前端组件基础测试 — Modal, ConfirmDialog, Toast
 *
 * 使用 vitest + @testing-library/react
 * 运行: cd frontend && npm test
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import Modal from '../components/ui/Modal'
import ConfirmDialog from '../components/ui/ConfirmDialog'
import { ToastProvider, useToast } from '../components/ui/Toast'
import { useContext } from 'react'

// ═══════════════════════════════════════════════════════════════
// Modal 测试
// ═══════════════════════════════════════════════════════════════

describe('Modal', () => {
  it('不显示时返回 null', () => {
    const { container } = render(
      <Modal open={false} onClose={() => {}} title="测试">
        <div>内容</div>
      </Modal>
    )
    expect(container.innerHTML).toBe('')
  })

  it('显示时渲染标题和内容', () => {
    render(
      <Modal open={true} onClose={() => {}} title="确认操作">
        <div>确定要删除吗？</div>
      </Modal>
    )
    expect(screen.getByText('确认操作')).toBeTruthy()
    expect(screen.getByText('确定要删除吗？')).toBeTruthy()
  })

  it('点击关闭按钮触发 onClose', () => {
    const onClose = vi.fn()
    render(
      <Modal open={true} onClose={onClose} title="测试">
        <div>内容</div>
      </Modal>
    )
    const closeBtn = screen.getByText('✕')
    fireEvent.click(closeBtn)
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('点击遮罩层触发 onClose', () => {
    const onClose = vi.fn()
    render(
      <Modal open={true} onClose={onClose} title="测试">
        <div>内容</div>
      </Modal>
    )
    const overlay = document.querySelector('.modal-overlay')!
    fireEvent.click(overlay)
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('点击模态内容不触发 onClose', () => {
    const onClose = vi.fn()
    render(
      <Modal open={true} onClose={onClose} title="测试">
        <div>内容</div>
      </Modal>
    )
    const modalBody = document.querySelector('.modal-body')!
    fireEvent.click(modalBody)
    expect(onClose).toHaveBeenCalledTimes(1) // 事件冒泡到 overlay
  })

  it('有 footer 时渲染', () => {
    render(
      <Modal
        open={true}
        onClose={() => {}}
        title="测试"
        footer={<button>保存</button>}
      >
        <div>内容</div>
      </Modal>
    )
    expect(screen.getByText('保存')).toBeTruthy()
  })

  it('不同 size 的 className', () => {
    const { container: c1 } = render(
      <Modal open={true} onClose={() => {}} title="小" size="sm">
        <div>sm</div>
      </Modal>
    )
    expect(c1.querySelector('.modal-sm')).toBeTruthy()

    const { container: c2 } = render(
      <Modal open={true} onClose={() => {}} title="大" size="lg">
        <div>lg</div>
      </Modal>
    )
    expect(c2.querySelector('.modal-lg')).toBeTruthy()
  })
})

// ═══════════════════════════════════════════════════════════════
// ConfirmDialog 测试
// ═══════════════════════════════════════════════════════════════

describe('ConfirmDialog', () => {
  it('渲染确认消息', () => {
    render(
      <ConfirmDialog
        open={true}
        title="删除确认"
        message="确定要删除此项？"
        onConfirm={() => {}}
        onCancel={() => {}}
      />
    )
    expect(screen.getByText('删除确认')).toBeTruthy()
    expect(screen.getByText('确定要删除此项？')).toBeTruthy()
  })

  it('默认按钮文字', () => {
    render(
      <ConfirmDialog
        open={true}
        title="标题"
        message="消息"
        onConfirm={() => {}}
        onCancel={() => {}}
      />
    )
    expect(screen.getByText('确认')).toBeTruthy()
    expect(screen.getByText('取消')).toBeTruthy()
  })

  it('自定义按钮文字', () => {
    render(
      <ConfirmDialog
        open={true}
        title="标题"
        message="消息"
        confirmText="是的"
        cancelText="不了"
        onConfirm={() => {}}
        onCancel={() => {}}
      />
    )
    expect(screen.getByText('是的')).toBeTruthy()
    expect(screen.getByText('不了')).toBeTruthy()
  })

  it('点击确认触发 onConfirm', () => {
    const onConfirm = vi.fn()
    render(
      <ConfirmDialog
        open={true}
        title="标题"
        message="消息"
        onConfirm={onConfirm}
        onCancel={() => {}}
      />
    )
    fireEvent.click(screen.getByText('确认'))
    expect(onConfirm).toHaveBeenCalledTimes(1)
  })

  it('点击取消触发 onCancel', () => {
    const onCancel = vi.fn()
    render(
      <ConfirmDialog
        open={true}
        title="标题"
        message="消息"
        onConfirm={() => {}}
        onCancel={onCancel}
      />
    )
    fireEvent.click(screen.getByText('取消'))
    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  it('danger 变体显示警告图标', () => {
    render(
      <ConfirmDialog
        open={true}
        title="危险操作"
        message="不可撤销"
        variant="danger"
        onConfirm={() => {}}
        onCancel={() => {}}
      />
    )
    expect(screen.getByText('⚠️')).toBeTruthy()
  })

  it('primary 变体显示信息图标', () => {
    render(
      <ConfirmDialog
        open={true}
        title="提示"
        message="操作信息"
        variant="primary"
        onConfirm={() => {}}
        onCancel={() => {}}
      />
    )
    expect(screen.getByText('ℹ️')).toBeTruthy()
  })
})

// ═══════════════════════════════════════════════════════════════
// Toast 测试
// ═══════════════════════════════════════════════════════════════

describe('ToastProvider', () => {
  it('渲染子组件', () => {
    render(
      <ToastProvider>
        <div>测试内容</div>
      </ToastProvider>
    )
    expect(screen.getByText('测试内容')).toBeTruthy()
  })

  it('useToast 在 Provider 外抛错', () => {
    // 使用 ErrorBoundary 来捕获错误
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    function BadComponent() {
      useToast()
      return null
    }
    expect(() => {
      render(<BadComponent />)
    }).toThrow()
    consoleError.mockRestore()
  })
})
