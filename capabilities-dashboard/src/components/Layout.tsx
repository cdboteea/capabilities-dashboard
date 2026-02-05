import { Link, useLocation, useNavigate } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { useState, useEffect, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { KeyboardShortcutsHelp } from '@/components/KeyboardShortcutsHelp'
import {
  BookOpen,
  FileText,
  Workflow,
  MessageSquare,
  Plug,
  Bot,
  Clock,
  Code,
  Brain,
  PlaySquare,
  Activity,
  Search,
  Sun,
  Moon,
  X,
  Menu
} from 'lucide-react'

interface LayoutProps {
  children: React.ReactNode
}

interface SearchResult {
  type: string
  name: string
  path: string
  category: string
  app?: string
  promptCategory?: string
}

const navigation = [
  { name: 'Skills', href: '/skills', icon: BookOpen },
  { name: 'Scripts', href: '/scripts', icon: Code },
  { name: 'Workflows', href: '/workflows', icon: Workflow },
  { name: 'Prompts', href: '/prompts', icon: MessageSquare },
  { name: 'APIs', href: '/apis', icon: Plug },
  { name: 'Agents', href: '/agents', icon: Bot },
  { name: 'Cron', href: '/cron', icon: Clock },
  { name: 'Memory', href: '/memory', icon: Brain },
  { name: 'Media', href: '/media', icon: PlaySquare },
  { name: 'Status', href: '/status', icon: Activity },
]

function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [showSearchResults, setShowSearchResults] = useState(false)
  const [isDark, setIsDark] = useState(false)
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [showShortcutsHelp, setShowShortcutsHelp] = useState(false)
  const searchInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    // Check if dark mode is enabled on mount
    setIsDark(document.documentElement.classList.contains('dark'))
  }, [])

  useEffect(() => {
    // Load theme preference from localStorage
    const savedTheme = localStorage.getItem('theme')
    if (savedTheme === 'dark') {
      setIsDark(true)
      document.documentElement.classList.add('dark')
    } else if (savedTheme === 'light') {
      setIsDark(false)
      document.documentElement.classList.remove('dark')
    } else {
      // Auto-detect system preference
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      setIsDark(prefersDark)
      if (prefersDark) {
        document.documentElement.classList.add('dark')
      }
    }
  }, [])

  useEffect(() => {
    const debounceTimer = setTimeout(() => {
      if (searchQuery.trim()) {
        performSearch(searchQuery)
      } else {
        setSearchResults([])
        setShowSearchResults(false)
      }
    }, 300)

    return () => clearTimeout(debounceTimer)
  }, [searchQuery])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
        event.preventDefault()
        searchInputRef.current?.focus()
      }

      if ((event.ctrlKey || event.metaKey) && event.key === '/') {
        event.preventDefault()
        setShowShortcutsHelp(true)
      }

      if (event.key === 'Escape') {
        setShowSearchResults(false)
        setShowShortcutsHelp(false)
      }

      if (event.key >= '1' && event.key <= '9') {
        const index = parseInt(event.key) - 1
        if (index < navigation.length && !event.ctrlKey && !event.metaKey && document.activeElement?.tagName !== 'INPUT') {
          event.preventDefault()
          navigate(navigation[index].href)
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [navigate])

  const performSearch = async (query: string) => {
    try {
      const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`)
      if (response.ok) {
        const results = await response.json()
        setSearchResults(results)
        setShowSearchResults(true)
      }
    } catch (error) {
      console.error('Search failed:', error)
    }
  }

  const toggleTheme = () => {
    const newIsDark = !isDark
    setIsDark(newIsDark)
    
    if (newIsDark) {
      document.documentElement.classList.add('dark')
      localStorage.setItem('theme', 'dark')
    } else {
      document.documentElement.classList.remove('dark')
      localStorage.setItem('theme', 'light')
    }
  }

  const handleSearchResultClick = (result: SearchResult) => {
    setSearchQuery('')
    setShowSearchResults(false)
    
    // Navigate to the appropriate page based on result type
    switch (result.type) {
      case 'skill':
        navigate('/skills')
        break
      case 'script':
        navigate('/scripts')
        break
      case 'workflow':
        navigate('/workflows')
        break
      case 'prompt':
        navigate('/prompts')
        break
    }
  }

  const getResultIcon = (type: string) => {
    switch (type) {
      case 'skill':
        return <BookOpen className="h-4 w-4" />
      case 'script':
        return <Code className="h-4 w-4" />
      case 'workflow':
        return <Workflow className="h-4 w-4" />
      case 'prompt':
        return <MessageSquare className="h-4 w-4" />
      default:
        return <FileText className="h-4 w-4" />
    }
  }

  return (
    <div className="min-h-screen bg-background flex">
      {/* Mobile Sidebar Overlay */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div
        className={cn(
          "w-64 bg-card border-r border-border fixed lg:static inset-y-0 left-0 z-50 transform transition-transform duration-200",
          isSidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        <div className="p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="text-2xl">🦞</span>
              <h1 className="text-xl font-semibold">Capabilities</h1>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="lg:hidden h-8 w-8 p-0"
              onClick={() => setIsSidebarOpen(false)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <nav className="px-4 space-y-1">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href
            return (
              <Link
                key={item.name}
                to={item.href}
                onClick={() => setIsSidebarOpen(false)}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-200",
                  isActive
                    ? "bg-primary/10 text-primary border-l-4 border-primary font-medium"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )}
              >
                <item.icon className="h-4 w-4" />
                <span>{item.name}</span>
              </Link>
            )
          })}
        </nav>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col lg:ml-0">
        {/* Header */}
        <header className="bg-card border-b border-border px-4 lg:px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Button
                variant="ghost"
                size="sm"
                className="lg:hidden h-8 w-8 p-0"
                onClick={() => setIsSidebarOpen(true)}
              >
                <Menu className="h-4 w-4" />
              </Button>
              <h2 className="text-lg font-semibold">
                {navigation.find(item => item.href === location.pathname)?.name || 'Dashboard'}
              </h2>
            </div>

            {/* Search and Theme Controls */}
            <div className="flex items-center space-x-2 lg:space-x-4">
              {/* Search */}
              <div className="relative">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <input
                    ref={searchInputRef}
                    type="text"
                    placeholder="Search..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10 pr-4 py-2 border border-border rounded-md bg-background text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring w-40 sm:w-48 lg:w-64"
                  />
                  {searchQuery && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="absolute right-1 top-1/2 transform -translate-y-1/2 h-6 w-6 p-0"
                      onClick={() => {
                        setSearchQuery('')
                        setShowSearchResults(false)
                      }}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  )}
                </div>
                
                {/* Search Results */}
                {showSearchResults && searchResults.length > 0 && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-card border border-border rounded-md shadow-lg max-h-64 overflow-y-auto z-50">
                    {searchResults.map((result, index) => (
                      <div
                        key={index}
                        className="flex items-center space-x-3 px-3 py-2 hover:bg-accent cursor-pointer"
                        onClick={() => handleSearchResultClick(result)}
                      >
                        {getResultIcon(result.type)}
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium truncate">{result.name}</div>
                          <div className="text-xs text-muted-foreground">
                            {result.category}
                            {result.app && ` • ${result.app}`}
                            {result.promptCategory && ` • ${result.promptCategory}`}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Theme Toggle */}
              <Button
                variant="ghost"
                size="sm"
                onClick={toggleTheme}
                className="h-8 w-8 p-0"
              >
                {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              </Button>

              <span className="hidden md:inline text-sm text-muted-foreground">
                {new Date().toLocaleDateString()}
              </span>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-4 lg:p-6 overflow-auto">
          {children}
        </main>
      </div>

      {/* Keyboard Shortcuts Help */}
      <KeyboardShortcutsHelp open={showShortcutsHelp} onOpenChange={setShowShortcutsHelp} />
    </div>
  )
}

export default Layout