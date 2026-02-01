import { Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import SettingsPage from './pages/SettingsPage'
import TaskDetailPage from './pages/TaskDetailPage'
import ComparePage from './pages/ComparePage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/settings" element={<SettingsPage />} />
      <Route path="/compare" element={<ComparePage />} />
      <Route path="/tasks/:id" element={<TaskDetailPage />} />
    </Routes>
  )
}

export default App
