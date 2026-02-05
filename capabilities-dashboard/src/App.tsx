import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Suspense, lazy } from 'react'
import { ToastProvider } from './contexts/ToastContext'
import Layout from './components/Layout'
import { Spinner } from './components/ui/spinner'

// Lazy load pages for code splitting
const Skills = lazy(() => import('./pages/Skills'))
const Scripts = lazy(() => import('./pages/Scripts'))
const Workflows = lazy(() => import('./pages/Workflows'))
const Prompts = lazy(() => import('./pages/Prompts'))
const Integrations = lazy(() => import('./pages/Integrations'))
const Agents = lazy(() => import('./pages/Agents'))
const Cron = lazy(() => import('./pages/Cron'))
const Status = lazy(() => import('./pages/Status'))
const Memory = lazy(() => import('./pages/Memory'))
const Media = lazy(() => import('./pages/Media'))

// Loading fallback
function PageLoader() {
  return (
    <div className="flex items-center justify-center h-64">
      <Spinner className="w-8 h-8" />
    </div>
  )
}

function App() {
  return (
    <ToastProvider>
      <Router>
        <Layout>
          <Suspense fallback={<PageLoader />}>
            <Routes>
              <Route path="/" element={<Skills />} />
              <Route path="/skills" element={<Skills />} />
              <Route path="/scripts" element={<Scripts />} />
              <Route path="/workflows" element={<Workflows />} />
              <Route path="/prompts" element={<Prompts />} />
              <Route path="/apis" element={<Integrations />} />
              <Route path="/agents" element={<Agents />} />
              <Route path="/cron" element={<Cron />} />
              <Route path="/memory" element={<Memory />} />
              <Route path="/media" element={<Media />} />
              <Route path="/status" element={<Status />} />
            </Routes>
          </Suspense>
        </Layout>
      </Router>
    </ToastProvider>
  )
}

export default App
