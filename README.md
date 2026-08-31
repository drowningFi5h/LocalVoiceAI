# LocalVoiceAI

Local chat assistant. It runs against llama.cpp on your machine, so nothing goes out to a cloud API.

The point of this repo is not "yet another CLI wrapper around an LLM". I wanted something that:

- actually remembers you between sessions
- keeps a personality instead of sounding like a generic chatbot every time you open it
- can bring stuff up on its own, instead of waiting for you to repeat context

## How a turn works

1. Your message goes into working memory (the current chat, dies when you quit).
2. Context is built from: persona + long-term memories + recent chat.
3. The local model replies.
4. A second LLM pass looks at the turn and decides if anything is worth saving.

Memory extraction is its own call with its own prompt. The chat model is not also responsible for "trying to remember".

## Memory

Two layers:

- **Working memory** — this session only. Cleared on exit.
- **Long-term memory** — SQLite. Survives restarts. Path is `src/data/localvoice.db` (configurable).

The extractor only keeps durable stuff: name, preferences, job, projects, relationships, long-term goals. It skips hi, one-off tasks, small talk, questions.

A candidate looks like this:

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

Not everything gets written:

- confidence below 0.65 → drop
- importance below 0.50 → drop

If the same `memory_type` + `category` + `key` already exists, it updates that row instead of inserting a duplicate. Value gets replaced, importance can go up, confidence bumps a bit.

On the next turn those rows get stuffed into the prompt as:

```
Known information about the user:
- preference.coffee: drinks espresso, no sugar
- project.name: LocalVoiceAI
```

So the model is not guessing. The facts are just there, which is why it can mention something you said last week without you bringing it up.

## Personality

Personas are markdown files in `configs/personas/`. That's the identity, rules, and tone. Which one loads is set in `configs/config.yaml`:

```yaml
persona:
  default: "default"
```

Drop in another `.md` file if you want a different character. Memory stays; only the persona text changes.

Over time the same persona starts answering differently because it has more user memories in context. The DB also has a `persona` memory type (vs `user`) for traits the assistant itself picks up. User facts are extracted today. Persona memories are in the schema, just not fully wired yet.

## Layout

```
src/
  main.py                 CLI loop
  mind/                   turn orchestration + memory
  models/                 Memory, Persona, Context, etc
  storage/                SQLite
  llm/                    llama.cpp via LiteLLM
  core/                   config + persona loader
  instructions/           memory extractor prompt
configs/
  config.yaml
  personas/
```

`Mind` is the thing that talks to you. It builds context, gets a reply, then tries to learn from the exchange. LLM backend is a `BaseLLM` so you can swap it; default is local OpenAI-compatible llama.cpp through LiteLLM.

## Setup

Needs Python 3.10+, a llama.cpp server, and a GGUF model.

```bash
bash scripts/setup.sh
pip install litellm pyyaml

bash scripts/download_model.sh   # Qwen3-4B into models/llm/
bash scripts/start_llm.sh        # http://127.0.0.1:8080
bash scripts/check_server.sh
```

Then:

```bash
cd src
python main.py
```

Type `exit` or `quit` to stop. Memories stay in the db after you leave.

Set `model.name` in `configs/config.yaml` to whatever llama.cpp is actually serving.

## Config

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

Keep `base_url` on localhost unless you have a reason not to.

## Status

Chat, user-memory extract/store/recall, and persona loading work end to end. Next up is treating persona development more like user memory: actually writing persona memories, and ranking what gets recalled instead of dumping everything into the prompt.
