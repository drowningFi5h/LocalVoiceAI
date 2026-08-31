# LocalVoiceAI

A local conversational companion that **remembers who you are** and **stays in character across sessions**.

Most chatbots reset every time you open them. LocalVoiceAI is built around the opposite idea: a proactive assistant with durable long-term memory and a personality that is loaded, conditioned, and carried forward — not a disposable prompt.

It runs fully offline against a local LLM (llama.cpp). Nothing leaves your machine.

---

## What this is for

LocalVoiceAI is not a generic Q&A wrapper. It is a small mind:

- **Proactive conversation** — the assistant speaks from a living persona and from what it already knows about you, instead of waiting to be re-taught every turn.
- **Long-term memory** — durable facts about you are extracted, scored, stored, and recalled automatically.
- **Dynamic personality** — character is a first-class object (markdown persona + optional persona memories), not a one-shot system prompt that evaporates when the session ends.

Talk to it today. Come back tomorrow. It should still know your name, your projects, your preferences, and how it relates to you.

---

## How a turn actually works

Every reply is assembled from three layers of mind, then the conversation is mined for anything worth keeping:

```
You speak
    │
    ▼
┌─────────────────────────────────────────┐
│  Working memory                         │
│  current session, forgotten on exit     │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│  Context builder                        │
│  persona  +  long-term memories  +  chat│
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│  Local LLM                              │
│  generates the reply in character       │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│  Memory extractor                       │
│  pulls durable user facts from the turn │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│  Memory manager → SQLite                │
│  keep / update / discard                │
└─────────────────────────────────────────┘
```

The assistant does not “hope” it will remember. After each exchange it runs a dedicated extraction pass, then only commits memories that clear importance and confidence gates.

---

## Long-term memory

Memory is the core product, not a plugin.

### Two timescales

| Layer | Lifetime | Role |
| --- | --- | --- |
| **Working memory** | This session only | Recent turns. Cleared when you quit. |
| **Long-term memory** | Survives restarts | Identity, preferences, relationships, projects, stable facts. |

Working memory is the conversation. Long-term memory is who you are to the assistant.

### What gets stored

The extractor is conservative. It ignores greetings, one-off tasks, small talk, and questions. It looks for things that will still matter later:

- identity
- preferences
- skills
- projects
- occupation and education
- long-term goals
- relationships
- other stable personal facts

Each candidate is a structured record:

```json
{
  "memory_type": "user",
  "category": "preference",
  "key": "coffee",
  "value": "drinks espresso, no sugar",
  "importance": 0.7,
  "confidence": 0.9
}
```

### What gets kept

Not every candidate becomes a memory.

- **confidence &lt; 0.65** → discarded
- **importance &lt; 0.50** → discarded
- otherwise it is written to SQLite

If a memory with the same identity (`memory_type` + `category` + `key`) already exists, it is updated in place: the value is refreshed, importance can only rise, and confidence ticks up. The assistant does not accumulate contradictory copies of the same fact.

### How memory comes back

On the next turn, known user memories are injected as system context:

```
Known information about the user:
- preference.coffee: drinks espresso, no sugar
- project.name: LocalVoiceAI
```

The model is not asked to “try to remember.” The facts are sitting in the prompt. That is why it can bring things up unprompted — a project you mentioned last week, a name, a preference — without you repeating yourself.

Memories live in `src/data/localvoice.db` (configurable). They survive process restarts. They are local.

---

## Personality that actually persists

Personality here is not a vibe in the temperature slider. It is loaded, versioned, and present in every context window.

### Personas as character files

Personas live in `configs/personas/` as markdown. Each file is the assistant’s identity, rules, behavior, and voice. The default persona is selected in `configs/config.yaml`:

```yaml
persona:
  default: "default"
```

Swap the file, and the same memory system talks as a different person. The memories stay; the character changes — or you keep the character and let the memories deepen it.

### How personality develops over time

A static prompt is a costume. LocalVoiceAI treats personality as something that **conditions on history**:

1. **Base character** — the markdown persona is always in context. Tone, boundaries, and relationship to you do not drift back to a generic helpful assistant.
2. **User-conditioned behavior** — long-term memories about you are fed in with the persona. The same character answers differently once it knows you are a night owl, that you hate being interrupted, or that you are building a specific project.
3. **Persona-side memory** — the store already distinguishes `memory_type: "user"` from `memory_type: "persona"`. That is the hook for traits the assistant itself acquires: private opinions, running jokes, how it has decided to treat you. User facts are extracted today; persona memories are first-class in the schema and repository.

The result is a companion that can grow a relationship instead of performing one from scratch each session.

Write a new markdown file under `configs/personas/` to define a different character. Keep the memory pipeline; only the identity layer changes.

---

## Architecture

```
src/
├── main.py                 CLI loop
├── mind/                   the conversational mind
│   ├── mind.py             orchestrates a turn
│   ├── working_memory.py   session history
│   ├── context_builder.py  persona + memories + chat
│   ├── memory_extractor.py LLM pass that proposes facts
│   ├── memory_manager.py   gates, upserts, recall
│   └── candidate_parser.py JSON → MemoryCandidate
├── models/                 Memory, Persona, Interaction, Context
├── storage/                SQLite + memory repository
├── llm/                    llama.cpp via LiteLLM
├── core/                   config, persona loader, instructions
└── instructions/
    └── memory_extractor.md extraction policy
```

`Mind` is the only object that talks to you. It does not call the model with a raw user string. It builds a context, gets a reply, then immediately tries to learn from the exchange.

The LLM backend is swappable (`BaseLLM`). The default client talks to a local OpenAI-compatible server (llama.cpp) through LiteLLM.

---

## Quick start

You need Python 3.10+, a llama.cpp server, and a GGUF model.

### 1. Install Python deps

```bash
bash scripts/setup.sh
pip install litellm pyyaml
```

### 2. Download a model

```bash
bash scripts/download_model.sh
```

This pulls a Qwen3-4B GGUF into `models/llm/`. Point `configs/config.yaml` at the file you actually want to serve.

### 3. Start the local LLM

```bash
bash scripts/start_llm.sh
```

The server should listen on `http://127.0.0.1:8080`. Confirm it:

```bash
bash scripts/check_server.sh
```

### 4. Talk

From the repo root, with `src` on the path:

```bash
cd src
python main.py
```

Type normally. Type `exit` or `quit` to stop.

Memories written during the session remain in the database after you leave.

---

## Configuration

`configs/config.yaml` controls the local server, model, conversation window, default persona, and database path.

```yaml
server:
  provider: openai
  base_url: http://127.0.0.1:8080/v1
  api_key: local

model:
  name: /path/to/your-model.gguf

conversation:
  max_history: 20

persona:
  default: "default"

database:
  path: src/data/localvoice.db
```

The model name should match what llama.cpp is serving. Keep `base_url` on localhost unless you know you want otherwise — this project is designed to stay on-device.

---

## Design principles

- **Remember on purpose.** Extraction is a separate LLM call with its own instructions, not a side effect of chatting.
- **Forget the noise.** Importance and confidence filters exist so the store does not fill with “hi” and today’s weather.
- **One fact, one identity.** Updates overwrite the same key instead of spawning duplicates.
- **Character is data.** Personas are files. Memories are rows. The mind is the glue, not a hidden prompt stuffed in `main.py`.
- **Local by default.** The database, the model, and the conversation never need a cloud API.

---

## Status

End-to-end chat, user-memory extraction, persistence, and persona loading are in place. The interesting work from here is making personality development as automatic as user-memory retention: richer persona memories, better recall ranking, and a companion that gets more itself — and more yours — the longer you talk to it.
