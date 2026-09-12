## Agent Core

The demo evaluates a naive tool-using agent against local prompt-injection
fixtures. The agent exposes exactly seven tools: `READ_FILE`, `SUMMARIZE`,
`QUERY_DB`, `SEND_EMAIL`, `SEARCH_WEB`, `CALCULATE_MATH`, and `WRITE_FILE`.
Email and file-write operations are simulated or in-memory only.

Injection cases live in `injections/test_cases.json` and are grouped in
`injections/injection_taxonomy.md`.

Offline corpus validation:

```powershell
python -c "import json; from pathlib import Path; print(len(json.loads(Path('injections/test_cases.json').read_text())))"
```

The local demo uses `python -m agent.task_runner` and requires the existing
Groq configuration in `.env`.
### Setup

1. Create a virtual environment and install `requirements.txt`.
2. Copy `.env.example` to `.env`.
3. Set `GROQ_API_KEY` and `GROQ_MODEL` in `.env`.
4. Run `python -m agent.task_runner` from this directory.

The demo runs one clean and one poisoned mock document task. It does not make
The expanded demo reads local HTML fixtures through `READ_FILE`. It runs one
clean document task plus multiple poisoned file tasks. Every model-proposed tool
call is executed by the loop so the experiment can observe attempted hijacks.

### Trace schema

`Agent.run` returns `(answer, trace)`, where `trace` is a list of dictionaries.
Each entry has stable keys: `step`, `timestamp`, `reasoning`, `tool`, `input`,
and `output`.

The agent does not use native reasoning parameters. Before each tool call, the
system prompt requires a short explanation, which is extracted from the normal
assistant `message.content` field and stored as `reasoning` in the trace.

### OpenRouter

OpenRouter is available as a fourth provider through its OpenAI-compatible API.
The adapter uses `https://openrouter.ai/api/v1` and the `OPENROUTER_API_KEY`
environment variable. It does not send an unverified native reasoning option;
it uses the existing prompted-reasoning fallback. Native Qwen3 reasoning fields
through OpenRouter should be checked when testing with a real key.

Configure it with:

```env
MODEL_PROVIDER=openrouter
MODEL_NAME=qwen/qwen3-8b:free
OPENROUTER_API_KEY=your-openrouter-api-key
OPENROUTER_MODEL=qwen/qwen3-8b:free
```

`MODEL_NAME` takes precedence over `OPENROUTER_MODEL`. Groq and Ollama remain
unchanged when `MODEL_PROVIDER` is set to `groq` or `ollama`.

### Model providers

The default provider is Groq, preserving the existing `GROQ_API_KEY` and
`GROQ_MODEL` path. Set `MODEL_PROVIDER=ollama` to use the local Ollama client;
this path requires no API key and uses Ollama's native client at
`localhost:11434`. `MODEL_NAME` overrides the provider-specific model setting.

The Ollama adapter passes the existing tool schema dictionaries to
`ollama.chat`, then normalizes `message.thinking` into `reasoning` and Ollama
tool calls into the response shape used by the agent loop. `OLLAMA_THINK=true`
enables thinking when the selected local model supports it.

Once Ollama is installed, run:

```powershell
ollama pull qwen3:8b
pip install -r requirements.txt
$env:MODEL_PROVIDER = "ollama"
$env:MODEL_NAME = "qwen3:8b"
python -m agent.task_runner
```

To switch back to Groq:

```powershell
$env:MODEL_PROVIDER = "groq"
$env:MODEL_NAME = ""
python -m agent.task_runner
```
