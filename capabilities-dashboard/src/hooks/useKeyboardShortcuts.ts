import { useEffect } from 'react'

interface ShortcutConfig {
  key: string
  ctrl?: boolean
  meta?: boolean
  shift?: boolean
  callback: () => void
  description?: string
}

export function useKeyboardShortcut(config: ShortcutConfig) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const { key, ctrl, meta, shift, callback } = config

      const ctrlPressed = ctrl ? (event.ctrlKey || event.metaKey) : true
      const metaPressed = meta ? (event.ctrlKey || event.metaKey) : true
      const shiftPressed = shift ? event.shiftKey : !event.shiftKey

      if (event.key.toLowerCase() === key.toLowerCase() && ctrlPressed && metaPressed && shiftPressed) {
        event.preventDefault()
        callback()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [config])
}

export function useKeyboardShortcuts(shortcuts: ShortcutConfig[]) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      for (const shortcut of shortcuts) {
        const { key, ctrl, meta, shift, callback } = shortcut

        const needsCtrl = ctrl !== undefined ? ctrl : false
        const needsMeta = meta !== undefined ? meta : false
        const needsShift = shift !== undefined ? shift : false

        const hasModifier = needsCtrl || needsMeta
        const modifierPressed = hasModifier
          ? (needsCtrl && (event.ctrlKey || event.metaKey)) || (needsMeta && (event.ctrlKey || event.metaKey))
          : !event.ctrlKey && !event.metaKey

        const shiftMatches = needsShift ? event.shiftKey : !event.shiftKey

        if (event.key.toLowerCase() === key.toLowerCase() && modifierPressed && shiftMatches) {
          event.preventDefault()
          callback()
          return
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [shortcuts])
}
