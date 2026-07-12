import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/layout/Layout'
import Dashboard from './pages/Dashboard'
import GameManager from './pages/GameManager'
import PresetEditor from './pages/PresetEditor'
import FlowEditor from './pages/FlowEditor'
import ExecutionHistory from './pages/ExecutionHistory'
import PluginManager from './pages/PluginManager'
import Settings from './pages/Settings'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/games" element={<GameManager />} />
        <Route path="/presets/:gameId" element={<PresetEditor />} />
        <Route path="/flow/:presetId" element={<FlowEditor />} />
        <Route path="/history" element={<ExecutionHistory />} />
        <Route path="/plugins" element={<PluginManager />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}

export default App
