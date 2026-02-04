import { Routes, Route } from 'react-router-dom'
import AppLayout from './components/AppLayout'
import HomePage from './pages/HomePage'
import SettingsPage from './pages/SettingsPage'
import TaskDetailPage from './pages/TaskDetailPage'
import ComparePage from './pages/ComparePage'
import ReviewPage from './pages/ReviewPage'
import ReviewTaskPage from './pages/ReviewTaskPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<AppLayout />}>
        <Route index element={<HomePage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="compare" element={<ComparePage />} />
        <Route path="review" element={<ReviewPage />} />
        <Route path="review/:taskId" element={<ReviewTaskPage />} />
        <Route path="tasks/:id" element={<TaskDetailPage />} />
      </Route>
    </Routes>
  )
}

export default App
