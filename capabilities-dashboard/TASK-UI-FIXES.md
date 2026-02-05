# UI Fixes Task

## Priority: HIGH | Quick fixes

---

## 1. Sticky Sidebar Navigation (`src/components/Layout.tsx`)

**Problem:** When scrolling down content, the left sidebar with tab navigation scrolls away. User has to scroll back up to change tabs.

**Solution:** Make the sidebar sticky/fixed:
```tsx
// The sidebar nav container should be:
<aside className="fixed left-0 top-0 h-screen w-64 bg-card border-r overflow-y-auto">
  {/* Logo and nav items */}
</aside>

// The main content area needs left margin to account for fixed sidebar:
<main className="ml-64 flex-1 overflow-auto">
  {/* Page content */}
</main>
```

Or use sticky positioning:
```tsx
<aside className="sticky top-0 h-screen w-64 bg-card border-r overflow-y-auto flex-shrink-0">
```

---

## 2. Adjust Panel Width Ratio (`src/pages/Workflows.tsx` and `src/pages/Prompts.tsx`)

**Problem:** Left panel (file list) and right panel (viewer) have equal width. The file list doesn't need that much space, but the viewer needs more horizontal room.

**Solution:** Change the grid from `lg:grid-cols-2` to a ratio like `lg:grid-cols-[350px_1fr]` or `lg:grid-cols-[300px_1fr]`:

```tsx
// In Workflows.tsx and Prompts.tsx, find:
<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

// Change to:
<div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-6">
```

This gives the left panel a fixed 320px width and the viewer gets all remaining space.

---

## 3. Add Visible Horizontal Scrollbar (`src/pages/Workflows.tsx` and `src/styles/globals.css`)

**Problem:** Horizontal scrolling works but there's no visible scrollbar to drag.

**Solution:** Add custom scrollbar styling that's always visible:

In `globals.css`:
```css
/* Always show scrollbars in code viewers */
.code-viewer {
  overflow: auto;
}

.code-viewer::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}

.code-viewer::-webkit-scrollbar-track {
  background: hsl(var(--muted));
  border-radius: 5px;
}

.code-viewer::-webkit-scrollbar-thumb {
  background: hsl(var(--muted-foreground) / 0.3);
  border-radius: 5px;
}

.code-viewer::-webkit-scrollbar-thumb:hover {
  background: hsl(var(--muted-foreground) / 0.5);
}

/* Firefox scrollbar */
.code-viewer {
  scrollbar-width: auto;
  scrollbar-color: hsl(var(--muted-foreground) / 0.3) hsl(var(--muted));
}
```

In `Workflows.tsx`, add the class to the viewer container:
```tsx
<CardContent className="h-[calc(100%-80px)] overflow-hidden">
  <div className="h-full code-viewer">
    <SyntaxHighlighter ... />
  </div>
</CardContent>
```

Also in `Prompts.tsx` if it has a similar viewer.

---

## Files to Modify
1. `src/components/Layout.tsx` - Sticky sidebar
2. `src/pages/Workflows.tsx` - Panel ratio + scrollbar class
3. `src/pages/Prompts.tsx` - Panel ratio + scrollbar class  
4. `src/styles/globals.css` - Scrollbar styling

## Testing
- Scroll down on any page - sidebar should stay visible
- On Workflows/Prompts, viewer should be ~70% width
- Horizontal scrollbar should be visible and draggable in viewer
