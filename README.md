# Agent H1 // Neon Console

A small AI agent harness with a neon Streamlit interface. It runs on a **local model through Ollama** by default, and can also use OpenAI or Anthropic models.

The agent can:

- chat with the model you pick
- call tools: list, read and write files in a `workspace/` folder
- keep **long-term memory** in `memory.md`
- use extra tools from **MCP servers** listed in `mcp_servers.json`

The interface adds a chat view, a file workshop (upload, create, edit), a memory editor and a tool registry.

---

## Project layout

```
Agent_harness_H1/
├── harness.py          # the agent: model registry, memory, tools, MCP, agent loop, CLI
├── app.py              # Streamlit neon interface (imports harness.py, no edits needed)
├── mcp_servers.json    # optional MCP servers to launch at startup
├── workspace/          # files the agent can list, read and write
├── memory.md           # created automatically when something is saved
├── pyproject.toml      # dependencies (managed with uv)
└── v0.py ... v4.py     # earlier step-by-step versions of the harness
```

---

## 1. Prerequisites

| Requirement | Why | Check |
|---|---|---|
| Python (version in `.python-version`) | runs the app | `python --version` |
| [uv](https://docs.astral.sh/uv/) | installs dependencies and runs scripts | `uv --version` |
| [Ollama](https://ollama.com/download) | runs the local model | `ollama --version` |
| Node.js (optional) | only if an MCP server is launched with `npx` | `node --version` |

---

## 2. Set up the local AI (Ollama)

### 2.1 Install Ollama

Download it from <https://ollama.com/download> (Windows, macOS, Linux). On Linux you can also run:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 2.2 Start the Ollama server

The desktop app on Windows and macOS starts it automatically. Otherwise run:

```bash
ollama serve
```

Leave that terminal open. The server listens on `http://localhost:11434`.

### 2.3 Download the models

`harness.py` expects these model names by default:

```bash
ollama pull qwen3.5:4b      # used by the "local" model
ollama pull qwen3.5:2b      # used by the "local-small" model (optional)
```

Confirm they are installed:

```bash
ollama list
```

### 2.4 Test that the server answers

```bash
ollama run qwen3.5:4b "say hello"
```

You can also check the OpenAI-compatible endpoint the harness uses:

```bash
curl http://localhost:11434/v1/models
```

### 2.5 Give the model a larger context window (recommended)

The system prompt, memory, tool definitions and chat history all share the model's context window. Ollama's default is small, and small models start ignoring tools when it fills up. Set a larger one **before starting Ollama**:

```bash
# macOS / Linux
export OLLAMA_CONTEXT_LENGTH=8192
ollama serve
```

```powershell
# Windows PowerShell
$env:OLLAMA_CONTEXT_LENGTH = 8192
ollama serve
```

If you use the Ollama desktop app, you can set the context length in its settings instead.

### 2.6 Use a different local model

Pick any model that supports **tool calling** (`ollama list` shows what you have). Then edit the `MODELS` dictionary in `harness.py`:

```python
"local": ModelConfig(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
    model="your-model-name",   # exactly as shown by `ollama list`
),
```

Larger models (7B and up) are noticeably better at choosing tools and filling in arguments.

---

## 3. Install the project

```bash
git clone https://github.com/Abhi-Biswas-AIML/Agent_harness_H1.git
cd Agent_harness_H1

uv sync              # install dependencies from pyproject.toml / uv.lock
uv add streamlit     # add the UI dependency
```

Copy `app.py` into the project root, next to `harness.py`.

---

## 4. Run it

### Neon web interface

```bash
uv run streamlit run app.py
```

Streamlit opens `http://localhost:8501` in your browser.

### Original terminal version

```bash
uv run harness.py
```

---

## 5. Cloud models (optional)

The `gpt` and `claude` entries read API keys from environment variables. Set them **before** starting Streamlit.

```bash
# macOS / Linux
export OPENAI_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"
```

```powershell
# Windows PowerShell
$env:OPENAI_API_KEY = "your-key"
$env:ANTHROPIC_API_KEY = "your-key"
```

Then choose the model in the sidebar. The app shows a warning if the key for the selected model is missing. Never commit keys to the repository.

---

## 6. Add MCP servers (optional)

MCP servers give the agent extra tools. They are read from `mcp_servers.json` at startup. Each server needs both a `command` and an `args` list:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "./workspace"]
    }
  }
}
```

Restart the app after editing the file. Connected tools appear in the **Tools** section with an `MCP` badge, and any startup errors show in the sidebar's **MCP log**.

---

## 7. Using the interface

### Chat

Talk to the agent normally. It decides when to use tools. Under each reply, the **tool calls** expander shows what ran, with arguments, results and timing.

Examples to try:

- `What files are in my workspace?`
- `Create a file called todo.md with a todo list for this week`
- `Read ideas.md and summarize it`
- `Remember that I prefer short answers`

Slash commands work in the chat box:

| Command | What it does |
|---|---|
| `/models` | list configured models |
| `/model <name>` | switch model, for example `/model local-small` |
| `/tools` | list all local and MCP tools |
| `/memory` | show saved memory |
| `/clear` | clear the conversation |

### Workshop

- **Upload:** drop files in and press **Send to workspace**.
- **Create:** enter a file name and content, then press **Create file**.
- **Open, edit, download, delete:** choose a file on the right.

The agent sees the same `workspace/` folder through `list_files`, `read_file` and `write_file`. It reads files as UTF-8 text, so text, markdown, code, CSV and JSON work best. Binary files such as PDFs can be stored and downloaded but not read by the agent.

### Memory

Shows everything in `memory.md`. You can add a fact, edit the raw file, or wipe it. Memory is added to the system prompt, and the app refreshes the prompt after every turn and edit, so new facts apply immediately.

### Tools

A registry of every available tool with its description and parameters, labeled `LOCAL` or `MCP`.

---

## 8. How it works

1. `harness.py` defines a model registry. Every model is just an OpenAI-compatible endpoint, so Ollama, OpenAI and Anthropic share one client.
2. The system prompt includes the contents of `memory.md`.
3. Each user message goes into a loop: the model replies, any tool calls are executed, results are fed back, and this repeats until the model answers without a tool call.
4. `app.py` imports `harness.py`, keeps one background event loop alive so MCP connections persist across Streamlit reruns, and wraps tool calls so the UI can display them.

---

## 9. Troubleshooting

| Problem | Likely cause and fix |
|---|---|
| "Agent call failed" with a connection error | Ollama is not running. Start it with `ollama serve`. |
| Error mentioning model not found | The model is not pulled. Run `ollama pull <name>` and check the name against `ollama list` and `harness.py`. |
| First reply takes very long | Ollama is loading the model into memory. Later replies are faster. |
| Model ignores tools or answers from guesswork | Small models are weak at tool calling. Ask explicitly (`use list_files`), raise the context length (section 2.5), or switch to a larger model. |
| Model forgets things in long chats | Context window is full. Use **Clear conversation** or raise `OLLAMA_CONTEXT_LENGTH`. |
| Warning about a missing API key | Export the key before launching Streamlit (section 5). |
| MCP tools do not appear | Check the sidebar **MCP log**. Make sure `command` and `args` are both set, and that Node.js is installed for `npx` servers. |
| Some styling looks off | Streamlit changes its internal class names between versions. Update Streamlit (`uv add -U streamlit`) or adjust the CSS block in `app.py`. |
| Uploaded file is empty for the agent | The file is probably binary or not UTF-8. Convert it to text first. |

---

## 10. Notes

- `workspace/` and `memory.md` hold personal data. Consider adding `memory.md` to `.gitignore`.
- Whatever the agent writes goes into `workspace/` only. File names are stripped of folder paths in the interface, but the underlying harness tools do not sandbox paths, so avoid running this on untrusted input.

## License

See `LICENSE` (Unlicense).
