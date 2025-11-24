import { Routes, Route, Navigate } from 'react-router-dom'
import { Invoices } from './pages/Invoices'
import { DevDebug } from './pages/DevDebug'
import { ChatAssistant } from './components/ChatAssistant'

function App() {
  return (
    <div className="App">
      <main>
        <Routes>
          <Route path="/invoices" element={<Invoices />} />
          <Route path="/dev/debug" element={<DevDebug />} />
          <Route path="/" element={<Navigate to="/invoices" replace />} />
        </Routes>
      </main>
      <ChatAssistant />
    </div>
  )
}

export default App
