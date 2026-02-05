# Frontend Fixes & Design Overhaul Task

## Priority: HIGH | Deadline: ASAP

Fix UI bugs and implement modern soothing color palette.

---

## 1. Fix Workflows Horizontal Scrolling (`src/pages/Workflows.tsx`)

**Problem:** Long YAML lines get cut off, only vertical scroll works.

**Solution:** Update the SyntaxHighlighter container:
```tsx
<CardContent className="h-[calc(100%-80px)] overflow-hidden">
  <div className="h-full overflow-auto">
    <SyntaxHighlighter
      language="yaml"
      style={isDark ? vscDarkPlus : oneLight}
      customStyle={{
        margin: 0,
        padding: '16px',
        background: 'transparent',
        fontSize: '14px',
        overflow: 'visible',  // Let parent handle scroll
        minWidth: 'max-content'  // Prevent line wrapping
      }}
      wrapLines={false}
      wrapLongLines={false}
    >
      {selectedWorkflow.content}
    </SyntaxHighlighter>
  </div>
</CardContent>
```

Also add CSS to `src/styles/globals.css`:
```css
/* Syntax highlighter horizontal scroll fix */
.syntax-highlighter-container pre {
  overflow-x: auto !important;
  white-space: pre !important;
}
```

---

## 2. Color Palette Overhaul (`src/styles/globals.css`)

Replace the current grayscale CSS variables with soothing forest/sage tones:

```css
@layer base {
  :root {
    /* Light Mode - Soft sage/forest tones */
    --background: 150 20% 98%;
    --foreground: 150 25% 10%;
    --card: 150 15% 99%;
    --card-foreground: 150 25% 10%;
    --popover: 150 15% 99%;
    --popover-foreground: 150 25% 10%;
    --primary: 160 45% 40%;
    --primary-foreground: 0 0% 100%;
    --secondary: 150 15% 94%;
    --secondary-foreground: 150 25% 15%;
    --muted: 150 10% 93%;
    --muted-foreground: 150 10% 40%;
    --accent: 175 40% 92%;
    --accent-foreground: 175 45% 25%;
    --destructive: 0 65% 55%;
    --destructive-foreground: 0 0% 100%;
    --border: 150 15% 88%;
    --input: 150 15% 88%;
    --ring: 160 45% 40%;
    --radius: 0.75rem;
    
    /* Status colors */
    --success: 160 60% 45%;
    --warning: 40 90% 50%;
    --info: 200 80% 50%;
  }

  .dark {
    /* Dark Mode - Deep forest tones */
    --background: 160 25% 7%;
    --foreground: 150 15% 95%;
    --card: 160 22% 10%;
    --card-foreground: 150 15% 95%;
    --popover: 160 22% 10%;
    --popover-foreground: 150 15% 95%;
    --primary: 160 50% 50%;
    --primary-foreground: 160 25% 7%;
    --secondary: 160 20% 15%;
    --secondary-foreground: 150 15% 90%;
    --muted: 160 15% 18%;
    --muted-foreground: 150 10% 60%;
    --accent: 175 35% 20%;
    --accent-foreground: 175 40% 80%;
    --destructive: 0 55% 45%;
    --destructive-foreground: 0 0% 100%;
    --border: 160 15% 18%;
    --input: 160 15% 18%;
    --ring: 160 50% 50%;
  }
}

/* Additional polish */
@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground antialiased;
  }
}

/* Smooth transitions */
.transition-theme {
  transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease;
}

/* Card hover effects */
.card-hover {
  @apply transition-all duration-200 hover:shadow-lg hover:scale-[1.02];
}

/* Glass morphism for dark mode cards */
.dark .glass-card {
  @apply bg-card/80 backdrop-blur-sm border-white/10;
}
```

---

## 3. Update Navigation Active State (`src/components/Layout.tsx`)

**Problem:** Hard to tell which page is active.

**Solution:** Add left border accent and background:
```tsx
// In the NavLink component or wherever nav items are rendered
<NavLink
  to={item.path}
  className={({ isActive }) =>
    cn(
      "flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-200",
      isActive
        ? "bg-primary/10 text-primary border-l-4 border-primary font-medium"
        : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
    )
  }
>
```

---

## 4. Add Media Delete Button (`src/pages/Media.tsx`)

**Problem:** No way to delete files.

**Solution:** Add delete button to file preview:
```tsx
// Add to imports
import { Trash2 } from 'lucide-react'

// Add delete function
const deleteFile = async (file: MediaFile) => {
  if (!confirm(`Delete "${file.name}"? This will move it to trash.`)) return
  
  try {
    const response = await fetch(
      `/api/media/${file.subfolder}/${encodeURIComponent(file.name)}`,
      { method: 'DELETE' }
    )
    if (!response.ok) throw new Error('Delete failed')
    
    showToast('success', 'File moved to trash')
    setSelectedFile(null)
    fetchMediaFiles() // Refresh list
  } catch (err) {
    showToast('error', 'Failed to delete file')
  }
}

// Add button to file preview header (next to other buttons)
<Button
  size="sm"
  variant="ghost"
  onClick={() => selectedFile && deleteFile(selectedFile)}
  className="text-destructive hover:text-destructive hover:bg-destructive/10"
  title="Delete file"
>
  <Trash2 className="h-4 w-4 mr-2" />
  Delete
</Button>
```

---

## 5. Add Skills Detail Modal (`src/pages/Skills.tsx`)

**Problem:** Can't see full SKILL.md content.

**Solution:** Add click handler and modal:
```tsx
// Add imports
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import ReactMarkdown from 'react-markdown'

// Add state
const [selectedSkill, setSelectedSkill] = useState<string | null>(null)
const [skillDetail, setSkillDetail] = useState<any>(null)
const [loadingDetail, setLoadingDetail] = useState(false)

// Add fetch function
const fetchSkillDetail = async (name: string) => {
  setLoadingDetail(true)
  try {
    const response = await fetch(`/api/skills/${encodeURIComponent(name)}`)
    if (!response.ok) throw new Error('Failed to fetch')
    const data = await response.json()
    setSkillDetail(data)
    setSelectedSkill(name)
  } catch (err) {
    showToast('error', 'Failed to load skill details')
  } finally {
    setLoadingDetail(false)
  }
}

// Make cards clickable
<Card 
  key={skill.name} 
  className="hover:shadow-md transition-all duration-200 hover:scale-[1.02] cursor-pointer"
  onClick={() => fetchSkillDetail(skill.name)}
>
  {/* existing content */}
</Card>

// Add modal at end of component
<Dialog open={!!selectedSkill} onOpenChange={() => setSelectedSkill(null)}>
  <DialogContent className="max-w-4xl max-h-[80vh] overflow-hidden">
    <DialogHeader>
      <DialogTitle className="flex items-center gap-2">
        <BookOpen className="h-5 w-5" />
        {selectedSkill}
      </DialogTitle>
    </DialogHeader>
    {loadingDetail ? (
      <div className="flex justify-center py-8">
        <Spinner size="lg" />
      </div>
    ) : skillDetail ? (
      <div className="overflow-y-auto max-h-[60vh] pr-4">
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <ReactMarkdown>{skillDetail.content}</ReactMarkdown>
        </div>
        {skillDetail.scripts?.length > 0 && (
          <div className="mt-6 pt-4 border-t">
            <h4 className="font-medium mb-2">Scripts in this skill:</h4>
            <ul className="text-sm text-muted-foreground space-y-1">
              {skillDetail.scripts.map((s: string) => (
                <li key={s} className="font-mono">{s}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    ) : null}
  </DialogContent>
</Dialog>
```

---

## 6. Add Dark Mode Toggle (`src/components/Layout.tsx`)

**Problem:** Only follows system preference, no manual toggle.

**Solution:** Add toggle button in header:
```tsx
// Add state (with localStorage persistence)
const [isDark, setIsDark] = useState(() => {
  if (typeof window !== 'undefined') {
    const saved = localStorage.getItem('theme')
    if (saved) return saved === 'dark'
    return window.matchMedia('(prefers-color-scheme: dark)').matches
  }
  return false
})

useEffect(() => {
  document.documentElement.classList.toggle('dark', isDark)
  localStorage.setItem('theme', isDark ? 'dark' : 'light')
}, [isDark])

// Add toggle button in header
<Button
  variant="ghost"
  size="icon"
  onClick={() => setIsDark(!isDark)}
  title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
>
  {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
</Button>
```

---

## Files to Modify
1. `src/styles/globals.css` - Color palette
2. `src/pages/Workflows.tsx` - Horizontal scroll fix
3. `src/pages/Media.tsx` - Delete button
4. `src/pages/Skills.tsx` - Detail modal
5. `src/components/Layout.tsx` - Nav active state, dark mode toggle

## Dependencies to Add (if not present)
- `react-markdown` (for skill modal)
- Already have: `lucide-react`, dialog components
