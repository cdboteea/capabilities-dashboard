import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import EmailsPage from './pages/EmailsPage'
import KnowledgeGraph from './pages/KnowledgeGraph'
import SearchPage from './pages/SearchPage'
import AnalyticsPage from './pages/AnalyticsPage'
import FilesPage from './pages/FilesPage'
import UrlsPage from './pages/UrlsPage'
import SettingsPage from './pages/SettingsPage'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/emails" element={<EmailsPage />} />
        <Route path="/knowledge-graph" element={<KnowledgeGraph />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/files" element={<FilesPage />} />
        <Route path="/urls" element={<UrlsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </Layout>
  )
}

export default App 