# Honeypot for AI Agents — Tiered Sentinel Architecture

A three-tier defense system that detects when an LLM agent has been hijacked mid-task by prompt injection: canary tripwires, a sub-15ms PyTorch anomaly detector, and an LLM cognitive auditor for deep semantic review.

---

## 0. Project Context (read this first — for anyone, human or AI, picking this up cold)

**What this document is:** a complete build plan for a hackathon project, written to be self-contained. If you're an AI assistant being handed this file to help with one part of the project, everything you need to understand the whole system and where your piece fits is below.

**The event:** a hackathon, Track 1 ("Guardrails & Trust"). Team of 5 people, deliberately polyglot — Python for the two ML/security microservices, Node.js for the agent and orchestration backbone, Next.js for the frontend. Claude and Gemini are used as coding assistants throughout, not as part of the shipped product's runtime (except where a module explicitly calls an LLM API, i.e. Tier 2).

**The problem being solved:** AI agents with tool access (file access, web browsing, database queries, sending messages) are vulnerable to *indirect prompt injection* — malicious instructions hidden inside content the agent reads (a webpage, a file, a tool's output), which can hijack the agent's behavior without the user ever typing anything malicious themselves. Most hackathon "AI safety" submissions build generic content filters (is this text toxic). This project targets a different, less-crowded angle: **behavioral security for agents that already have tools** — catching what the agent actually does after being hijacked, not trying to pre-filter every possible bad input.

**The core design decision — three tiers instead of one detector:** a single detection method forces a bad tradeoff (fast/cheap methods miss subtle attacks; a thorough LLM-based check is too slow/expensive to run on every tool call). So the system runs three tiers in increasing order of cost, each triggered only when the cheaper tier below it flags something worth a closer look:
- **Tier 0 (Canary Tripwires):** deterministic, near-zero latency. Fake high-entropy secrets are planted in the agent's environment; if one ever leaks into a tool payload, that's unambiguous compromise — instant kill.
- **Tier 1 (PyTorch Anomaly Detector):** a custom autoencoder, trained only on normal tool-call sequences, scores every single tool call in under 15ms based on how well it reconstructs the agent's action trajectory. Runs on 100% of calls.
- **Tier 2 (Cognitive LLM Sentinel):** only triggered when Tier 1's score spikes or a high-risk tool is invoked. An LLM auditor compares the tool call's actual content against the agent's original stated objective and gives a final verdict.

**What "success" looks like:** proving the tiering is real, not decorative — showing most tool calls clear at Tier 1 in single-digit milliseconds, only a small fraction ever reach the expensive Tier 2 check, and Tier 2 specifically catches attacks designed to slip past Tier 1 (semantically wrong but statistically normal-looking action sequences).

**Team & stack (5 people, one service each):**
- **Srujan** — ML Architect, Python/PyTorch — Tier 1
- **Tanvi** — Threat Engineer, Python — Attack Corpus + Tier 0
- **Rishi** — Agent Backend, Node.js/LangChain.js — the Sandbox (agent + tools)
- **Ayush** — Systems Integrator, Express/Prisma/MySQL/WebSockets — the Nervous System + Tier 2
- **Vedant** — Frontend Lead, Next.js/Tailwind — the Command Center

The five services integrate only through the shared contracts in Section 4 — HTTP request/response shapes and one WebSocket event shape. That contract is what makes independent parallel work across three different languages possible without people blocking each other.

---

## 1. The Problem

Agentic AI systems are being deployed fast, and every tool result, webpage, or file an agent reads is untrusted input fed straight back into its context. This is a largely unguarded attack surface: hidden instructions in that content can hijack the agent's behavior without the user ever typing anything malicious. Most "AI safety" hackathon projects filter text for toxicity. This project instead asks: **did the agent's actual behavior just deviate from the task, and can we catch it fast enough to matter?**

## 2. Why a Tiered Architecture

Running one expensive LLM check on every tool call is too slow and too costly. Running only cheap rule-based checks misses subtle, semantically-wrong-but-statistically-normal-looking attacks. So: cheap and instant checks run on everything, and only the suspicious fraction pays the cost of a deep audit. This tiering is itself a demoable result — you can show the overwhelming majority of calls clearing in single-digit milliseconds, and only a handful ever reaching Tier 2.

## 3. Architecture Overview

```
  User Task
     │
     ▼
┌─────────────────────────┐
│   Agent (Node.js /        │   RISHI
│   LangChain.js)            │   builds tools + reasoning loop
│   reasoning loop            │
└──────────┬────────────────┘
           │ before executing any tool call, agent
           │ calls out to the Sentinel Server and WAITS
           │ for an allow / block / kill decision
           ▼
┌─────────────────────────────────────────────┐
│         Sentinel Server (Express)              │   AYUSH
│         "the Nervous System"                    │   owns this entire box
│                                                  │
│   1. Calls Tier 0 service  ──► instant_kill?     │──── TANVI's FastAPI /check
│              │ clean                             │
│              ▼                                   │
│   2. Calls Tier 1 service  ──► recon_loss, flag?  │──── SRUJAN's FastAPI /score
│              │ normal        │ anomalous OR        │
│              │               │ high-risk tool       │
│              │               ▼                      │
│              │      3. Calls Tier 2 (LLM Sentinel,   │──── LLM API (Claude/Gemini)
│              │         built directly in this box)    │
│              │               │                         │
│              ▼               ▼                         │
│         Verdict Aggregator → allow / block / kill        │
│              │                                            │
│      ┌───────┴────────┐                                   │
│      ▼                ▼                                   │
│  Prisma → MySQL   WebSocket broadcast                       │
│ (log every span)   (live SentinelEvent)                     │
└─────────────────────────────────────────────┘
                              │
                              ▼
                  ┌───────────────────────┐
                  │  Command Center (Next.js) │   VEDANT
                  │  live terminal, anomaly    │
                  │  gauge, attack dissector    │
                  └───────────────────────┘
```

Tanvi also owns the adversarial injection corpus — the attack content (webpages/files/tool-output payloads) fed into Rishi's agent during testing to exercise all three tiers. This isn't a runtime component; it's the test fixture set the whole system is evaluated against.

---

## 4. Shared Contracts (lock these on hour 0–1)

Because this project spans three languages (Python, TypeScript/Node, TypeScript/Next.js), the contract isn't a shared class/schema file — it's a set of plain JSON shapes everyone implements independently in their own language. Put these in a `shared/schemas/` folder as JSON Schema or even just annotated example JSON — the point is everyone reads the same source of truth before writing their own types.

### `ToolCallEvent` — what Rishi's agent sends to Ayush's server before executing a tool
```json
{
  "call_id": "uuid",
  "task_id": "uuid",
  "timestamp": "ISO8601",
  "tool_name": "read_file | summarize | query_db | send_email",
  "tool_id": 1,
  "tool_input": {},
  "turn_index": 0,
  "trajectory_so_far": [1, 2],
  "objective_summary": "short restatement of the task's goal",
  "allowed_tools": [1, 2, 3, 4],
  "high_risk_tools": [4]
}
```

### Tier 0 request/response — Ayush → Tanvi's FastAPI `POST /check`
```json
// request: the ToolCallEvent above, or a minimal subset (tool_input + tool_output if already executed for read-only checks)
// response:
{
  "call_id": "uuid",
  "leak_detected": false,
  "matched_token_id": null,
  "verdict": "instant_kill | clean"
}
```

### Tier 1 request/response — Ayush → Srujan's FastAPI `POST /score`
```json
// request:
{
  "call_id": "uuid",
  "tool_id_sequence": [1, 2, 4]   // fixed-length sliding window, zero-padded if shorter
}
// response:
{
  "call_id": "uuid",
  "recon_loss": 0.0,
  "is_anomalous": false,
  "latency_ms": 0.0
}
```

### Tier 2 verdict — produced inside Ayush's own code (calls an LLM API directly, no separate service needed)
```json
{
  "call_id": "uuid",
  "verdict": "benign | malicious",
  "confidence": 0.0,
  "reasoning": "string",
  "compared_against_objective": "string"
}
```

### `SentinelEvent` — the WebSocket payload Ayush broadcasts, that Vedant's frontend consumes
```json
{
  "call_id": "uuid",
  "task_id": "uuid",
  "timestamp": "ISO8601",
  "tool_name": "string",
  "tier0": { "leak_detected": false, "verdict": "clean" },
  "tier1": { "recon_loss": 0.0, "is_anomalous": false },
  "tier2": { "triggered": false, "verdict": null, "reasoning": null },
  "final_action": "allow | block | kill",
  "flagged_content_snippet": "string | null"
}
```

**Coordination rule:** the three cross-language handshakes (Rishi↔Ayush, Tanvi↔Ayush, Srujan↔Ayush) each need a 10-minute conversation between exactly those two people at hour 0–1 to confirm field names and types match exactly. Ayush should treat "confirm every contract" as their literal first task, since they're the one integrating all four other services.

---

## 5. Concurrency Strategy — Work Fully in Parallel

Nobody should be idle waiting on someone else's real service. Build against mocks/fixtures first, swap in real services as they come online.

- **Rishi** needs nothing from anyone to start — build the agent, all four tools, and the reasoning loop completely standalone. The `toolCallHook` that calls out to Ayush's server can point at a stub URL returning a hardcoded `{"final_action": "allow"}` until Ayush's real server exists.
- **Ayush** builds the entire Express app, Prisma schema, and WebSocket server against **mocked HTTP responses** standing in for Tier 0 and Tier 1, and a stubbed LLM call for Tier 2. Swap in Srujan's and Tanvi's real endpoints one at a time as they come online — since the contract is fixed, this is a URL change, not a rewrite.
- **Srujan** doesn't wait on Rishi's real trajectories — write a synthetic trajectory generator (sample plausible normal tool-ID sequences yourself from the agreed 4-tool list) and train against that first. Swap to Rishi's real logged trajectories later.
- **Tanvi** doesn't wait on anyone — canary generation/planting/detection can be built and unit-tested against a hand-written mock tool-call payload, and the injection corpus only needs the agreed tool list, not working agent code.
- **Vedant** doesn't wait on Ayush's real WebSocket server — build a fake event emitter that fires mock `SentinelEvent` payloads on a timer, and develop the entire Command Center UI against that. Swap to the real WebSocket connection once Ayush's server is live.

**Shared rule:** nobody changes a contract shape unilaterally after hour 1. A real change is a quick message to the two people on that specific handshake, not a silent field rename.

---

## 6. Folder Structure

```
honeypot-ai-agents/
├── README.md
├── shared/
│   └── schemas/                      # JSON Schema / annotated example JSON — the cross-language contract
│       ├── tool-call-event.json
│       ├── tier0-contract.json
│       ├── tier1-contract.json
│       ├── tier2-verdict.json
│       └── sentinel-event.json
│
├── agent/                              # RISHI — Node.js / LangChain.js
│   ├── package.json
│   ├── src/
│   │   ├── agentLoop.ts
│   │   ├── systemPrompt.ts
│   │   ├── toolCallHook.ts             # calls the sentinel server, awaits decision
│   │   └── tools/
│   │       ├── readFileTool.ts          # id 1
│   │       ├── summarizeTool.ts         # id 2
│   │       ├── queryDbTool.ts           # id 3
│   │       └── sendEmailTool.ts         # id 4, mock only
│   └── tests/
│
├── sentinel-server/                     # AYUSH — Express, Prisma, MySQL, WebSockets
│   ├── package.json
│   ├── prisma/
│   │   └── schema.prisma
│   └── src/
│       ├── app.ts
│       ├── middleware/interceptToolCall.ts
│       ├── clients/
│       │   ├── tier0Client.ts
│       │   └── tier1Client.ts
│       ├── tier2/
│       │   ├── auditorPrompt.ts
│       │   └── llmSentinel.ts
│       ├── orchestrator/escalationLogic.ts
│       ├── db/logSpan.ts
│       └── websocket/broadcast.ts
│
├── tier1-pytorch/                        # SRUJAN — Python / PyTorch
│   ├── requirements.txt
│   ├── synthetic_data.py
│   ├── trajectory_encoder.py
│   ├── model.py
│   ├── train.py
│   ├── calibrate_threshold.py
│   ├── export_torchscript.py
│   ├── service.py                        # FastAPI: POST /score
│   └── checkpoints/
│
├── tier0-canary/                          # TANVI — Python (security)
│   ├── requirements.txt
│   ├── token_generator.py
│   ├── canary_planter.py
│   ├── leak_detector.py
│   └── service.py                         # FastAPI: POST /check
│
├── injections/                             # TANVI — attack corpus
│   ├── injection_taxonomy.md
│   ├── generate_corpus.py
│   ├── test_cases.json
│   └── corpus/
│       ├── webpages/
│       ├── files/
│       ├── tool_outputs/
│       └── metadata_tricks/
│
└── frontend/                                # VEDANT — Next.js, Tailwind
    ├── package.json
    ├── app/
    │   ├── page.tsx                          # split-screen Command Center
    │   └── components/
    │       ├── LiveTerminal.tsx
    │       ├── AnomalyGauge.tsx
    │       ├── AttackDissectorPanel.tsx
    │       └── VerdictBadge.tsx
    └── lib/
        └── socket.ts
```

---

## 7. Person-Wise Task Breakdowns

### Srujan — ML Architect (Python / PyTorch) — Tier 1
1. Don't wait on Rishi. Build `synthetic_data.py`: hand-write a generator sampling plausible normal tool-ID sequences from the agreed 4-tool list (e.g. `[1,2]`, `[1,3,2]`) so training isn't blocked.
2. Design the trajectory window representation: fixed-length sliding window of the last N tool IDs, zero-padded for shorter histories
3. Implement the encoding step in `trajectory_encoder.py` — one-hot per tool ID or a small learned embedding
4. Define the `Autoencoder` in `model.py`: encoder compressing to a small bottleneck, decoder reconstructing — start feedforward, since latency matters more than long-range sequence modeling
5. Train (`train.py`) on synthetic clean trajectories only — the model must never see attack sequences during training
6. Build `calibrate_threshold.py`: pick the anomaly cutoff from the reconstruction-loss distribution on held-out clean data (e.g. 95th/99th percentile)
7. Once Tanvi's trajectory-anomaly-goal test cases exist, validate that loss spikes clearly above threshold on those and stays low on clean sequences
8. Build `export_torchscript.py` to compile the model for fast inference — required to realistically hit sub-15ms
9. Build the FastAPI service (`service.py`) exposing `POST /score`, matching the exact contract in Section 4
10. Warm up the model on service startup so the first real request isn't slow
11. Benchmark actual latency on your hardware — record P50/P95/P99, iterate on model size if not hitting sub-15ms
12. Add a sensible default for the first call or two in a run, before the trajectory window has enough history
13. Log every scored trajectory locally for later analysis/retraining
14. Build a simple recalibration script for if the tool set changes later
15. Confirm the exact `/score` request/response field names directly with Ayush at hour 0–1 — this is the one hard cross-team dependency, resolve it first
16. Swap the training pipeline from synthetic to Rishi's real logged trajectories once available — should be a data-source change only
17. Write up the measured latency numbers and clean-vs-attack loss separation as a short report — these become real, citable numbers in the pitch
18. (stretch) Build an LSTM/GRU version and compare accuracy vs. latency tradeoff against the feedforward version
19. (stretch) Add per-tool-ID risk weighting into the loss calculation
20. Write a short internal explainer: why reconstruction loss is a valid anomaly signal here, for judges who ask "why an autoencoder"

### Tanvi — Threat Engineer (Security / Python) — Attack Corpus + Tier 0
1. Write the injection taxonomy doc: define the techniques you'll build test cases for (white-text/invisible-unicode, fake system-tag override, direct instruction override, nested delegation, role-play framing)
2. Build white-text/invisible-unicode injection test cases
3. Build fake-system-tag override test cases
4. Build direct-instruction-override test cases
5. Build nested-delegation test cases
6. Build **canary-exfiltration-goal** test cases specifically designed to make the agent try to leak a planted secret (targets Tier 0)
7. Build **trajectory-anomaly-goal** test cases designed to produce an unusual tool-call sequence (targets Tier 1 — hand these to Srujan once ready)
8. Build **objective-drift-goal** test cases where the sequence looks statistically normal but the semantic content contradicts the task (targets Tier 2 specifically)
9. Build hard-negative test cases: legitimate content that merely mentions instruction-like language, to test false-positive rate
10. Package everything into `test_cases.json`, tagging each case with which tier it's meant to target
11. Build `token_generator.py`: generate realistic, high-entropy fake secrets
12. Build `canary_planter.py` with multiple planting strategies (file content, tool output payload, env var) — coordinate directly with Rishi on exactly where these get embedded in his mock tools
13. Build `leak_detector.py`: regex + exact-match + partial/obfuscated-match scanning of tool call input/output for planted canary values
14. Distinguish **leak** (canary sent somewhere it shouldn't be) from **mere exposure** (canary appeared in context but wasn't acted on) with different severities
15. Build the FastAPI service (`service.py`) exposing `POST /check`, matching the exact contract in Section 4 — confirm field names with Ayush at hour 0–1
16. Test that canaries never interfere with legitimate task completion on clean runs
17. Validate every injection test case against a raw, unguarded version of Rishi's agent to confirm it actually achieves its stated attack goal
18. Write a short doc on why canary detection has a near-zero false-positive profile compared to the statistical/semantic tiers
19. (stretch) Add partial/obfuscated-match detection for a canary value split or lightly transformed across multiple calls
20. (stretch) Add a second canary class: a tempting but fake high-risk tool description that a legitimate task never needs, flagged as instant-kill if ever invoked

### Rishi — Agent Backend (Node.js / LangChain.js) — the Sandbox
1. Set up the Node.js project and LangChain.js scaffold
2. Build the system prompt and reasoning loop (`agentLoop.ts`)
3. Implement `readFileTool.ts` (id 1)
4. Implement `summarizeTool.ts` (id 2)
5. Implement `queryDbTool.ts` (id 3) — a simple mock data source is fine
6. Implement `sendEmailTool.ts` (id 4) as a mock that logs "would have sent X to Y" and never actually sends anything
7. Add an `objective_summary` field to every task definition — a short, clean restatement of the goal, since Tier 2 depends on comparing against this
8. Write 4–6 realistic legitimate task prompts exercising the tools in different plausible orders
9. Build `toolCallHook.ts`: before actually executing any tool, POST the `ToolCallEvent` to the sentinel server and **await** the allow/block/kill decision before proceeding
10. Point `toolCallHook.ts` at a stub URL returning a hardcoded `allow` response initially — don't wait on Ayush's real server to start building this
11. Implement the `block` response handling: skip real tool execution, return a safe refusal into the agent's context instead
12. Implement the `kill` response handling: halt the agent loop immediately, log the reason
13. Add a max-turn safety cutoff independent of the sentinel tiers
14. Support injecting Tanvi's test-case content into whichever tool a given test case targets
15. Build a script to run a batch of clean legitimate task runs and save the resulting trajectories — this becomes Srujan's real training data once ready
16. Add a "log only" mode toggle (no blocking) for generating training/eval data without early termination
17. Confirm the exact `ToolCallEvent` field names and the response shape directly with Ayush at hour 0–1
18. Write unit tests confirming each tool works correctly standalone before wiring in the sentinel hook
19. Test full clean-task runs end-to-end once `toolCallHook` is pointed at Ayush's real server
20. (stretch) Add a second high-risk tool (e.g. `delete_file`) to test the high-risk-forces-Tier-2 rule specifically

### Ayush — Systems Integrator (Express / Prisma / MySQL / WebSockets) — the Nervous System + Tier 2
1. **Confirm all three cross-language contracts first** (with Rishi, Srujan, and Tanvi separately) — this is the actual hour-0 priority for this role, since you're integrating everyone
2. Set up the Express app skeleton and the MySQL connection
3. Design the Prisma schema: `Task`, `ToolCallSpan`, and a verdict/flag model capturing every tier's result per span
4. Run the initial Prisma migration
5. Build the intercept endpoint that Rishi's `toolCallHook` calls before executing a tool
6. Build `tier0Client.ts`, initially pointed at a mocked response, then swapped to Tanvi's real `/check` endpoint
7. Build `tier1Client.ts`, initially mocked, then swapped to Srujan's real `/score` endpoint
8. Build `escalationLogic.ts`: trigger Tier 2 if Tier 1's `is_anomalous` is true, OR the tool is in `high_risk_tools`, regardless of score
9. Design the Tier 2 auditor prompt: compare the tool call's actual content against `objective_summary`
10. Implement `llmSentinel.ts` calling an LLM API (Claude/Gemini) with that prompt, returning the `SentinelVerdict` shape
11. Build the verdict aggregator combining Tier 0/1/2 into one final `allow | block | kill` action
12. Return that decision synchronously to Rishi's `toolCallHook` so the agent actually pauses correctly on it
13. Build `logSpan.ts`: log every tool call span plus all three tiers' results to MySQL via Prisma
14. Build the WebSocket broadcast (`broadcast.ts`) pushing the `SentinelEvent` payload to connected frontend clients in real time
15. Handle partial service failures gracefully (a Tier 0/1/2 timeout or error shouldn't crash the whole pipeline — define a safe default action for each failure case)
16. Build a REST endpoint for Vedant's frontend to fetch historical task runs for the replay view
17. Confirm the exact `SentinelEvent` field names with Vedant at hour 0–1
18. Measure end-to-end latency added per tool call across the full escalation path, not just Tier 1's isolated latency
19. Write internal docs on the full request lifecycle (agent → intercept → Tier 0 → Tier 1 → conditional Tier 2 → aggregator → log + broadcast) for anyone debugging this later
20. (stretch) Add a manual override endpoint (a human can force-allow or force-kill a specific pending call) for the live demo's flexibility

### Vedant — Frontend Lead (Next.js / Tailwind) — the Command Center
1. Set up the Next.js project with Tailwind CSS
2. **Don't wait on Ayush's real server.** Build a mock event emitter firing fake `SentinelEvent` payloads on a timer, matching the exact schema in Section 4, and develop the whole UI against that first
3. Build `socket.ts`: the WebSocket client, initially pointed at the mock emitter
4. Build the split-screen Command Center layout (`page.tsx`)
5. Build `LiveTerminal.tsx`: a live, terminal-styled feed of tool calls as they stream in
6. Build `AnomalyGauge.tsx`: a live-updating visual for Tier 1's `recon_loss`, changing color/intensity as it approaches the threshold
7. Build `AttackDissectorPanel.tsx`: shows the `flagged_content_snippet` and reasoning whenever any tier fires
8. Build `VerdictBadge.tsx`: a clear, glanceable allow/block/kill indicator per call
9. Wire all four components to the live `SentinelEvent` stream
10. Handle WebSocket disconnect/reconnect gracefully in the UI
11. Build a historical replay view using Ayush's REST endpoint, stepping through a past run tier-by-tier
12. Add distinct visual treatment per tier (Tier 0 kill vs. Tier 1 flag vs. Tier 2 verdict) — color, iconography, whatever reads instantly
13. Add a results/metrics summary view once evaluation numbers exist (precision/recall/escalation rate)
14. Design the "at rest" clean-run state to look calm and quiet, so the visual contrast during an actual attack demo is dramatic
15. Do a full visual polish pass on the whole Command Center — this is the single thing judges watch most, so it disproportionately matters
16. Confirm the exact `SentinelEvent` field names with Ayush at hour 0–1, so your mock fixture and the eventual real stream match exactly
17. Swap the mock emitter for the real WebSocket connection once Ayush's server is live, and verify nothing breaks
18. Handle rapid event bursts gracefully so a fast agent loop doesn't visually overwhelm the terminal feed
19. Add a clearly distinct alert treatment specifically for a Tier 0 instant-kill event — it's the most dramatic demo moment and should read as such
20. (stretch) Add a manual "run demo scenario" trigger button in the UI for a cleaner live presentation flow

---

## 8. Rough Timeline

- **Hours 0–1**: Every cross-language contract in Section 4 gets confirmed in person, pairwise: Rishi↔Ayush, Tanvi↔Ayush, Srujan↔Ayush, Ayush↔Vedant. This is the only sequential step.
- **Hours 1–14**: All 5 people build in parallel against mocks/fixtures, per Section 5. Nobody should be idle.
- **Hours 14–16**: First real-data/service swaps — Rishi hands real trajectory logs to Srujan; Ayush starts swapping mocked Tier 0/1 responses for the real FastAPI services one at a time; Vedant swaps the mock event emitter for Ayush's real WebSocket connection.
- **Hours 16–22**: First full end-to-end integration — a real task, through the real agent, through the real three-tier pipeline, logged to real MySQL, shown on the real dashboard. Fix contract mismatches here.
- **Hours 22–28**: Run the full corpus through the integrated system. Expect real bugs — budget time for it.
- **Hours 28–32**: Tune thresholds/escalation rules based on real precision/recall numbers. Triage stretch tasks.
- **Hours 32–36**: Demo rehearsal, fallback plan tested, feature freeze.

---

## 9. Ethics Note
Every adversarial test case in `injections/` exists purely to evaluate detection and must never perform a genuinely harmful action even in the "successful attack" case — `sendEmailTool` logs an intended send, it never actually sends anything. This is defensive red-teaming to build and calibrate a detector, not an offensive tool.