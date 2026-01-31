# Skill Creation Guide

Quick reference for building Clawdbot AgentSkills.

## Structure

```
my-skill/
├── SKILL.md          — Required: frontmatter + instructions
├── scripts/          — Optional: Python/Bash for deterministic tasks
├── references/       — Optional: docs loaded on demand
└── assets/           — Optional: templates, images, files for output
```

## SKILL.md Template

```yaml
---
name: my-skill
description: >
  What it does + when to use it. This is the primary trigger —
  be specific about contexts that should activate this skill.
---
```

```markdown
# My Skill

## Quick Start
[minimal example to get going]

## Commands
[reference for available operations]

## Notes
[gotchas, tips, edge cases]
```

## Key Principles

1. **Concise** — only include what Claude doesn't already know
2. **Progressive disclosure** — SKILL.md stays lean (<500 lines), details in references/
3. **Scripts for repetition** — don't rewrite code each time, bundle it
4. **Description is the trigger** — body only loads AFTER skill activates
5. **Test scripts** — always run them before packaging

## Naming

- Lowercase, hyphens only: `my-cool-skill`
- Verb-led when possible: `rotate-pdf`, `track-expenses`
- Under 64 characters

## Publishing

```bash
# To ClawdHub
clawdhub publish ./my-skill --slug my-skill --name "My Skill" --version 1.0.0

# Or just use locally — drop folder in Clawdbot's skills directory
```
