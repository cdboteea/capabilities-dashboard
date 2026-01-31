# Dashboard Docker Compose Reference

This guide explains how to bring up each dashboard's services using Docker Compose, ensuring you use the correct subdirectory and avoid port conflicts.

---

## 1. Idea Database Dashboard
- **Directory:** `sub-projects/idea-database`
- **Command:**
  ```sh
  cd sub-projects/idea-database
  docker-compose up -d web_interface
  ```
- **Dashboard URL:** [http://localhost:3002](http://localhost:3002)
- **Port Mapping:** Host 3002 → Container 3002

---

## 2. Twin Report Knowledge Base Dashboard
- **Directory:** `sub-projects/twin-report-kb/docker/frontend`
- **Command:**
  ```sh
  cd sub-projects/twin-report-kb/docker/frontend
  docker-compose up -d web_interface
  ```
- **Dashboard URL:** [http://localhost:3100](http://localhost:3100) *(or as defined in compose)*
- **Port Mapping:** Host 3100 → Container 8000 (or as defined)

---

## ⚠️ Important Warning
- **Always run `docker-compose` from the correct subdirectory for the dashboard you want to start.**
- Running from the wrong directory may start the wrong services or cause port conflicts.
- If you need to bring up all dashboards, use the provided script below. 