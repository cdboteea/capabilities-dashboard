---
name: chatgpt-app
description: >
  Control the ChatGPT macOS desktop app via UI automation to use an existing OpenAI
  subscription (ChatGPT Plus/Pro). Use when you need to: (1) query ChatGPT/GPT-5.2
  without an API key, (2) generate images via DALL-E through the app, (3) get a
  second opinion from a different AI model, (4) use ChatGPT-specific features like
  browsing, canvas, or memory, (5) compare outputs between Claude and ChatGPT.
  Requires the ChatGPT app to be installed and logged in. Uses Peekaboo for UI automation.
---

# ChatGPT App Control

Drive the ChatGPT macOS app (`com.openai.chat`) via Peekaboo UI automation.
Uses the logged-in subscription — no API key needed.

## Quick Reference

```bash
# Open the app
open -a "ChatGPT"

# See current state + get element IDs
peekaboo see --app ChatGPT --annotate --path /tmp/chatgpt-see.png

# Capture main window (window ID may change between sessions)
peekaboo list windows --app ChatGPT --json
peekaboo image --window-id <MAIN_WINDOW_ID> --retina --path /tmp/chatgpt.png

# Type a prompt and send
peekaboo click --app ChatGPT --on <INPUT_ELEMENT>
peekaboo type "your prompt here" --app ChatGPT
peekaboo press return --app ChatGPT

# Wait for response, then capture
sleep 8  # adjust based on expected response time
peekaboo image --window-id <MAIN_WINDOW_ID> --retina --path /tmp/chatgpt-response.png
```

## Workflow

1. **Open** — `open -a "ChatGPT"` + `sleep 2`
2. **Identify elements** — `peekaboo see --app ChatGPT --annotate` to get element IDs
3. **Find main window** — `peekaboo list windows --app ChatGPT --json` (pick the largest window, ~1054x848)
4. **New chat** (if needed) — `peekaboo hotkey --keys "cmd,n" --app ChatGPT`
5. **Type prompt** — Click input field element, then `peekaboo type`
6. **Send** — `peekaboo press return --app ChatGPT`
7. **Wait** — `sleep 5-15` depending on complexity
8. **Read response** — Capture screenshot, use `image` tool to read text

## Key Elements (typical, verify with `see`)

- Input field: Usually `elem_8` (Textfield: text entry area)
- Send button: Usually `elem_17` (Button: Send)
- Model selector: Usually `elem_14` (shows "5.2" or model name)
- Sidebar toggle: Usually `elem_19`
- Attach button: Usually `elem_9`

Element IDs may shift between sessions — always run `see` first.

## Tips

- **Response time**: Simple queries ~5s, complex/long ~15-30s. Check with screenshot.
- **Window capture**: The app has multiple windows (title bars, etc). The main content window is the largest one with title "ChatGPT".
- **New conversation**: Cmd+N for a fresh chat.
- **Model switching**: Click the model selector element to change models.
- **Reading responses**: Use `peekaboo image` + the `image` vision tool to read text from screenshots. The annotated view can obscure text.
- **Long responses**: Scroll down with `peekaboo scroll --direction down --app ChatGPT` to see more.
- **Avoid conflicts**: Don't run while the user is actively using the app.

## When to Use vs Not

**Use ChatGPT app when:**
- DALL-E image generation is needed
- Comparing Claude vs GPT outputs
- GPT-specific features (browsing, canvas, memory)
- $0 extra cost matters (uses existing subscription)

**Don't use when:**
- Speed matters (UI automation is slow: ~10-30s per exchange)
- Programmatic/batch queries (use API or local models instead)
- User is actively using the app
