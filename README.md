# Honeypot for AI Agents

**A tiered sentinel architecture that catches AI agents mid-hijack — before a compromised tool call does damage.**

Built for a hackathon, Track 1: Guardrails & Trust.

---

## The Problem

AI agents with tool access (files, browsing, databases, messaging) treat everything they read as safe input to reason over. A webpage, a file, or a tool's own output can carry hidden instructions that hijack the agent's behavior — without the user ever typing anything malicious.

Most "AI safety" projects filter text for toxicity before it reaches the model. We asked a different question: **did the agent's actual behavior just deviate from its task, and can we catch it fast enough to matter?**

## The Approach

A single detector forces a bad tradeoff — cheap checks miss subtle attacks, and a thorough LLM-based check is too slow to run on every tool call. So instead of one detector, we run three, each triggered only when the cheaper tier below it flags something worth a closer look:

| Tier | What it does | Latency | Runs on |
|---|---|---|---|
| **Tier 0 — Canary Tripwires** | Fake high-entropy secrets are planted in the agent's environment. If one ever leaks into a tool payload, that's unambiguous compromise. | Near-zero | Every call |
| **Tier 1 — Anomaly Detector** | A PyTorch autoencoder, trained only on normal tool-call sequences, scores how well it reconstructs the agent's current trajectory. | Sub-15ms | 100% of calls |
| **Tier 2 — Cognitive Sentinel** | An LLM auditor compares the tool call's actual content against the agent's stated objective and returns a verdict. | Seconds | Only flagged calls |

Most calls clear at Tier 1 in single-digit milliseconds. Only a small fraction ever reach Tier 2 — and Tier 2 is specifically designed to catch attacks that look statistically normal but are semantically wrong.

## Architecture

```
Agent proposes a tool call
        │
        ▼
  Tier 0 — Canary check ──── instant kill on leak
        │ clean
        ▼
  Tier 1 — Anomaly score ─── flag on high reconstruction loss
        │ normal      │ anomalous or high-risk tool
        │             ▼
        │      Tier 2 — Cognitive audit (LLM)
        │             │
        ▼             ▼
     Verdict Aggregator → allow / block / kill
        │
        ├── Logged to MySQL (full audit trail)
        └── Broadcast over WebSocket → Command Center dashboard
```

## Tech Stack

| Component | Stack | Owner |
|---|---|---|
| Agent + tools ("the Sandbox") | Node.js, LangChain.js | Rishi |
| Tier 1 anomaly detector | Python, PyTorch, FastAPI | Srujan |
| Tier 0 canary system + attack corpus | Python, FastAPI | Tanvi |
| Sentinel server ("the Nervous System") + Tier 2 | Express, Prisma, MySQL, WebSockets | Ayush |
| Command Center dashboard | Next.js, Tailwind CSS | Vedant |

Every service talks to the others only through fixed JSON contracts (see `shared/schemas/`) — this is what let all five of us build in parallel across three languages without blocking on each other.

## Repo Structure

```
honeypot-ai-agents/
├── shared/schemas/       # cross-language contracts (JSON Schema)
├── agent/                # Rishi — Node.js agent + tools
├── sentinel-server/      # Ayush — Express orchestrator + Tier 2
├── tier1-pytorch/        # Srujan — anomaly detector service
├── tier0-canary/         # Tanvi — canary planting + detection
├── injections/           # Tanvi — adversarial test corpus
└── frontend/             # Vedant — Command Center dashboard
```

## Running It

Each service is independent and runs against mocks until the real ones are online — see each subfolder's own setup. At minimum:

```bash
# Frontend (Command Center)
cd frontend
npm install
npm run dev
```

The Command Center runs against a mock event stream by default (`lib/socket.ts`, `USE_MOCK = true`), so it's fully demoable without the rest of the stack running.

## What Success Looks Like

- Most tool calls clear Tier 1 in single-digit milliseconds
- Only a small fraction escalate to Tier 2
- Tier 2 specifically catches attacks engineered to slip past Tier 1
- A live demo: a clean task runs calm and fast, then an attack task gets caught and explained in real time on the dashboard

## Ethics Note

Every adversarial test case in `injections/` exists purely to evaluate detection. Even in a "successful attack" scenario, `sendEmailTool` only logs an intended send — it never actually sends anything. This is defensive red-teaming to build and calibrate a detector, not an offensive tool.

## Team

Srujan · Tanvi · Rishi · Ayush · Vedant