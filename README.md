<p align="center">
  <img src="images/nerdface.png" alt="Nerdface Logo" width="600"/>
</p>

# ☝️🤓 Nerdface

Hardened local agent. Hackable. Production-ready.

## Features
- **Security**: Local `llm-guard` scanning. Blocks prompt injection & sandbox escapes.
- **Sandbox**: Strong isolation via Shuru MicroVM.
- **Memory**: Local Holographic HRR + FTS5. O(log N) scaling.
- **Browser**: Camofox. Self-hosted, anti-bot.
- **Search**: 
  - **DuckDuckGo**: Built-in anonymous web search.
  - **SerpBase**: Deep search engine dorking with persistent credits.
- **State**: SQLite persistence at `~/.nerdface/state.db`.

## Setup
```bash
uv sync
```

## Execution
### CLI
```bash
uv run cli.py
```

### API
```bash
uv run run.py
```

---

## Legacy Documentation (Archive)

<details>
<summary>View original README content</summary>

# ☝️🤓 NERD FACE 

A hackable, lightweight local agent hardened for production

## Project Focus for MVP (Work In Progress)

#### Security

- [X] **Guardrails** - Input scanning to prevent prompt injection using llm-guard NLP models
- [X] **Kill Switch** - riased guardrail kills agent
- [ ] **Configurable Kill Switch Behaviour** - set kill switch rate limit, set kill switch to fully block at X hits,
- [ ] **Policy** - Human-in-the-loop approvals (out of band or Auth'd IDV. Would like out of band links and biometric scans ) for destructive actions, all policy outside the prompt.
- [ ] **logging** - immutable logs for auditing user+agent+tool action. connections for loki /tempo
- [X] **Sandbox** - microVM (Shuru) or strong container isolation
- [X] **Secrets Vault** - Shuru MicroVM has secret proxy
- [ ] **Secured Messaging** - API needs token
- [ ] **Biometic, MFA logins** - Identity


#### Agent AI Stuff

- [X] **Memory** - Local HRR Holographic X FTS5 O(log N) with trust score RRF. 
- [ ] **Sub-agents** - We want endless types of 'workflows' for orchestration. Reflex, a deep research workflow, coding workflow for agent scripts, reflection, reflexion, whatever. all can be used in skills. focused on powerusers of agentic ai
- [X] **Search Engine:** (SerpBase) that allows deep search engine Dorking and pay as you go, keep forever credits for searches
- [X] **Tools**
- [X] **CLI** - now with /paste mode for multi-line inputs
- [X] **API**
- [X] **Web Browser** - Camofox: self hosted, bypass bot protections.local , no pay, fast

- [X] **System Design Patterns for Small languge models** - tools schema configurable though default is hybrid schema in system prompt only, both per iteration tool schema, and on tools call schema errors. This cut down context by a massive about. tool naming focused for SLMs. 
- [X] **Compression** - head / tail with summerize the middle. tool calls clean up when not needed. 4 part algorithm. patachute for LLM gateway protection as 2nd safety
- [X] **Reduced Attack Vector** on popular offering
- [ ] **NerdPrompt** - allow to be used with NerdPrompt in terminal. THINK: ASCII OLDSCHOOL BBS output.

## Guardrails Overview

The Nerdface uses **llm-guard** to scan all inputs for security threats before they reach the agent.

### What Guardrails Protect Against

| Threat | Detection Method | Action |
|--------|-----------------|--------|
| **Prompt Injection** | NLP model analyzes text for attempts to override system instructions | Blocks input, triggers kill-switch |
| **Sandbox Escape Attempts** | Regex patterns for `/etc/passwd`, Docker/K8s commands | Blocks output containing system paths |
| **Runaway Loops** | Max iterations limit 
| **Killswitch** | Kills agent dead on security issue detected by guardrails | blocks agent completely till restarted

- **Models run locally** on the agent machine (NOT on the LLM server)
- **Low latency** - models load once, inference takes milliseconds

### NLP Models Used

| Model | Size | Purpose | Hugging Face Path |
|-------|------|---------|-------------------|
| PromptInjection | 714MB | Detects prompt injection attempts | `protectai/deberta-v3-base-prompt-injection-v2` |
| **Total** | **~714MB** | | |

## Feature Updates

#### State Persistence

The agent saves conversation history to SQLite at `~/.nerdface/state.db` using the `user` field from `/v1/chat/completions` as the session ID.

#### Nerdface Query

```bash
curl -X POST http://localhost:8000/apply \
     -H "Content-Type: application/json" \
     -d '{"text": "whats the weather in denver today ? "}'
```

*Note: The Dockerfile includes git, vim, tmux installation and automatic GitHub token configuration for HTTP endpoints. The agent will automatically use the GITHUB_TOKEN environment variable for git operations requiring authentication.*

</details>
