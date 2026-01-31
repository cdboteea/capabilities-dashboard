# Mac Studio Local‑LLM Endpoint — Tailnet & Public Access Guide

## 1 Purpose

This reference explains **how your agents can reach the Mac Studio LLM server** (Ollama) either inside the Tailscale mesh or through a public HTTPS URL. It consolidates the critical connection details so any workflow on the MacBook—or any other device—can invoke the local models as if they were a standard OpenAI endpoint.

---

## 2 System Architecture (Conceptual)

```
          ┌───────────────────────┐
          │  Mac Studio (Server) │
          │  · Ollama            │
          │  · Port 11434        │
          │  · Launchd service   │
          └─────────┬────────────┘
                    │ (localhost)
      tailscaled ▶ Serve (HTTPS 443) ▶ proxy → 127.0.0.1:11434
                    │
────────────────────┼──────────────────────────────────────────────
   inside tailnet   │   outside tailnet (optional Funnel)
                    │
         Tailnet HTTPS URL             Public Funnel URL
  https://matiass-mac-studio.          https://<yourname>.ts.net/
         tail174e9b.ts.net/            (TLS + rate‑limit)
```

- **Serve**: private HTTPS proxy available to all devices logged into your tailnet.
- **Funnel**: optional public HTTPS endpoint that tunnels through Tailscale's relay; ACL‑controlled.

---

## 3 Accessing the Tailnet URL (Typical Agent / SDK Path)

1. **Install & log in to Tailscale** on the client device.
2. Retrieve/confirm the node address:
   ```bash
   tailscale status | grep mac-studio      # shows node + tailnet URL
   ```
3. Use the canonical URL (auto‑TLS):
   ```text
   BASE_URL = "https://matiass-mac-studio.tail174e9b.ts.net/v1"
   API_KEY  = "ollama"   # placeholder; Ollama ignores it
   ```
4. Any OpenAI‑compatible call now works:
   ```python
   client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
   client.chat.completions.create(
       model="deepseek-r1",
       messages=[{"role":"user","content":"Hello"}]
   )
   ```

---

## 4 Enabling & Using Funnel (Public URL)

> **Requires** the **Funnel** feature flag ON in the admin console.

```bash
# Run once on Mac Studio
tailscale funnel --bg --https=443 11434

# Verify
tailscale funnel status   # displays https://<yourname>.ts.net/
```

- ACL defaults to **tailnet users only**. Edit *Admin → Funnel* to widen access if desired.
- Same `/v1/...` path structure as the tailnet URL.

---

## 5 Environment Variables for Agents (Template)

```bash
export OPENAI_API_BASE="https://matiass-mac-studio.tail174e9b.ts.net/v1"   # or Funnel URL
export OPENAI_API_KEY="ollama"          # placeholder
```

Set these in shell startup files or directly inside your project's runtime.

---

## 6 Model & Runtime Notes

| Model name      | Identifier to pass in `model=` |
| --------------- | ------------------------------ |
| DeepSeek R1     | `deepseek-r1`                  |
| Qwen 3 (32‑B)   | `qwen3:32b`                    |
| Qwen 2.5 (pull) | `qwen25`                       |
| Qwen 2.5 Vision | `qwen2.5vl`                    |
| Llama 4 Scout   | `llama4:scout`                 |
| Llama 4 Maverick | `llama4:maverick`             |

- Swapping models **does not** require restarting the server.
- `ollama pull <model>` on Mac Studio adds new entries instantly.

---

## 7 Quick Health / Status Commands (Mac Studio)

```bash
# Is Ollama running via launchd?
launchctl list | grep com\.ollama\.server

# Is Serve route active?
tailscale serve status

# Is only one Ollama listening?
lsof -iTCP:11434 -sTCP:LISTEN
```

---

## 8 Security & Best Practices

- **Firewall**: macOS firewall allows `/usr/local/bin/ollama`.
- **API‑Key Gate (optional)**: front Ollama with Caddy or Nginx and require `Authorization: Bearer <TOKEN>`.
- **Watchdog**: a simple launchd plist can auto‑restart Ollama on crash.
- **Sleep**: `pmset -c sleep 0` and display‑sleep only—ensures the endpoint stays live.

---

## 9 Reference Snippets

### cURL

```bash
curl -s \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-r1","messages":[{"role":"user","content":"Hello"}]}' \
  https://matiass-mac-studio.tail174e9b.ts.net/v1/chat/completions
```

### Python (OpenAI SDK)

```python
from openai import OpenAI
client = OpenAI(base_url="https://matiass-mac-studio.tail174e9b.ts.net/v1", api_key="ollama")
print(client.chat.completions.create(model="qwen3:32b", messages=[{"role":"user","content":"Ping"}]).choices[0].message.content)
```

---

This document now serves as **"source of truth"** for any local or remote agent that needs to reach the Mac Studio LLM.

---

## 10 Availability / Power‑Management Strategy

Ensuring the endpoint is reachable hinges on **preventing system sleep** while still allowing the display and peripherals to power down.

### 10.1 macOS GUI Settings (Recommended)

| Setting Path                                    | Toggle                                                                           | Notes                                                                                |
| ----------------------------------------------- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| **System Settings → Displays → Advanced**       | **Prevent automatic sleeping on power adapter when the display is off** → **ON** | Guarantees the Mac Studio's CPUs, GPU cores, and network stack stay awake 24/7.      |
| **System Settings → Lock Screen**               | **Turn display off after** → *15 min* (or similar)                               | Lets the monitor sleep, reducing power usage without affecting the server.           |
| **System Settings → Energy Saver** (if present) | **Wake for network access** → **ON**                                             | Enables Wake‑on‑LAN for future use; not required if the machine never system‑sleeps. |

### 10.2 Command‑Line Hardening (PMSET)

```bash
# Disable system sleep when on power adapter
sudo pmset -c sleep 0

# Ensure hibernation never triggers
sudo pmset -c disablesleep 1

# (Optional) Keep awake for X hours, then revert
caffeinate -u -t 7200   # 2 hours
```

- `-c` applies to "charger" mode only, so battery behaviour is unaffected (useful if you repurpose this on a MacBook).
- `caffeinate -w $(pgrep -f 'ollama serve')` keeps the system awake **only while the Ollama process is alive**.

### 10.3 Will a Serve/Funnel request wake the Mac Studio?

- **No.** If the system enters deep sleep, the NIC drops off the LAN → incoming packets never reach tailscaled → Serve cannot wake it.
- That's why we **disable system sleep entirely** for a "home server" setup. Display sleep is fine; network, CPU & GPU stay active.

### 10.4 Quick Health Check Script (optional)

```bash
#!/usr/bin/env bash
# ~/bin/ollama-health.sh
set -e
curl -sf http://127.0.0.1:11434/v1/models >/dev/null || { 
  echo "[watchdog] Ollama unresponsive — restarting" | logger
  launchctl kickstart -k gui/$(id -u)/com.ollama.server
}
```

Add a LaunchAgent to run this every 5 minutes for auto‑recovery.

---

## 11 Remote‑Access Quick‑Start (CLI & GUI)

### 11.1 Tailscale SSH (preferred)

1. **Tailnet flag**: Admin Console → Settings → Security → toggle **Tailscale SSH** ON.
2. **Mac Studio**: `sudo tailscale up --ssh` (runs once; survives reboot).
3. **MacBook alias** in `~/.zshrc` *(SSH key recommended)*

```bash
# ~/.ssh/config shortcut
Host macstudio
  HostName matiass-mac-studio.tail174e9b.ts.net
  User mmirvois
  IdentityFile ~/.ssh/macstudio

# one‑word shell alias
aalias macstudio='ssh macstudio'
```

Usage ➜ `macstudio`

### 11.2 macOS Screen Sharing over Tailscale

- **Enable** on Studio: *System Settings ▸ General ▸ Sharing ▸ Screen Sharing* → ON.
- **MacBook alias:**

```bash
alias macstudio-gui='open vnc://mmirvois@matiass-mac-studio.tail174e9b.ts.net'
```

Usage ➜ `macstudio-gui` → full desktop control.

---

## 12 Adding Additional Model Endpoints (General Recipe)

1. **Start server** on Studio bound to `0.0.0.0:<PORT>` (e.g., vLLM 8000, A1111 7860).
2. **Expose via Serve**

```bash
tailscale serve --bg --https=/mypath <PORT>
# optional public url
tailscale funnel --bg --https=/mypath <PORT>
```

3. **Client env‑var template**

```bash
export MYMODEL_API_BASE="https://macstudio.ts.net/mypath"
```

4. Document model identifier for agents (OpenAI schema, REST, etc.).

---

