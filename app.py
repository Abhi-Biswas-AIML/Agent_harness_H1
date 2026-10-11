"""
Neon Streamlit interface for Agent_harness_H1.

Place this file next to harness.py (repo root) and run:

    uv add streamlit
    uv run streamlit run app.py

It imports harness.py as-is (no edits needed) and reuses:
  - run_agent / messages / MODELS / model_name   (agent loop + model switching)
  - TOOL_SCHEMAS / LOCAL_TOOLS / connect_mcp      (local + MCP tools)
  - load_memory / save_memory / MEMORY_FILE       (long-term memory)
  - WORKSPACE                                     (files the agent can read/write)
"""

import asyncio
import json
import threading
import time
from contextlib import AsyncExitStack, redirect_stdout
from io import StringIO
from pathlib import Path

import streamlit as st

import harness

st.set_page_config(page_title="Agent H1 // Neon Console", page_icon="⚡", layout="wide")

harness.WORKSPACE.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Neon theme
# ---------------------------------------------------------------------------
NEON_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Rajdhani:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --bg0: #05030f;
  --bg1: #0b0720;
  --panel: rgba(18, 12, 44, 0.72);
  --cyan: #00f0ff;
  --magenta: #ff2bd6;
  --violet: #8a5bff;
  --lime: #b6ff3c;
  --text: #e9e4ff;
  --muted: #8f86c4;
}

.stApp {
  background:
    radial-gradient(900px 500px at 8% -10%, rgba(255, 43, 214, 0.18), transparent 60%),
    radial-gradient(900px 600px at 100% 0%, rgba(0, 240, 255, 0.14), transparent 60%),
    radial-gradient(700px 500px at 50% 120%, rgba(138, 91, 255, 0.20), transparent 60%),
    linear-gradient(180deg, var(--bg0), var(--bg1));
  color: var(--text);
  font-family: 'Rajdhani', sans-serif;
}
/* faint perspective grid */
.stApp::before {
  content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;
  background-image:
    linear-gradient(rgba(0,240,255,0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,240,255,0.045) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: linear-gradient(180deg, rgba(0,0,0,0.9), transparent 85%);
}
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1.6rem; max-width: 1100px; position: relative; z-index: 1; }

html, body, p, span, label, li, div { font-family: 'Rajdhani', sans-serif; }
p, li, label, .stMarkdown { font-size: 1.08rem; }
code, pre, textarea { font-family: 'JetBrains Mono', monospace !important; }

/* hero */
.hero { padding: 0.4rem 0 0.8rem 0; }
.hero h1 {
  font-family: 'Orbitron', sans-serif; font-weight: 900; font-size: 2.6rem; letter-spacing: 0.06em;
  margin: 0; line-height: 1.1;
  background: linear-gradient(90deg, var(--cyan), var(--violet) 45%, var(--magenta));
  -webkit-background-clip: text; background-clip: text; color: transparent;
  filter: drop-shadow(0 0 14px rgba(0, 240, 255, 0.45)) drop-shadow(0 0 28px rgba(255, 43, 214, 0.25));
}
.hero p { color: var(--muted); margin: 0.3rem 0 0 0; font-size: 1.1rem; }

/* stat chips */
.stats { display: flex; gap: 0.7rem; flex-wrap: wrap; margin: 0.9rem 0 0.4rem 0; }
.stat {
  background: var(--panel); border: 1px solid rgba(0, 240, 255, 0.35); border-radius: 12px;
  padding: 0.45rem 0.9rem; box-shadow: 0 0 14px rgba(0, 240, 255, 0.12), inset 0 0 12px rgba(0, 240, 255, 0.05);
}
.stat b { font-family: 'Orbitron', sans-serif; color: var(--cyan); text-shadow: 0 0 8px var(--cyan); font-size: 1.15rem; }
.stat span { color: var(--muted); margin-left: 0.5rem; }
.stat.m { border-color: rgba(255, 43, 214, 0.4); box-shadow: 0 0 14px rgba(255, 43, 214, 0.14); }
.stat.m b { color: var(--magenta); text-shadow: 0 0 8px var(--magenta); }
.stat.l { border-color: rgba(182, 255, 60, 0.4); box-shadow: 0 0 14px rgba(182, 255, 60, 0.12); }
.stat.l b { color: var(--lime); text-shadow: 0 0 8px var(--lime); }

/* section headings */
h2, h3, h4 { font-family: 'Orbitron', sans-serif !important; letter-spacing: 0.05em; color: var(--cyan) !important;
  text-shadow: 0 0 10px rgba(0, 240, 255, 0.5); }
h3 { font-size: 1.15rem !important; }

/* nav radio -> pills */
div[role="radiogroup"] { gap: 0.5rem; flex-wrap: wrap; }
div[role="radiogroup"] > label {
  background: var(--panel); border: 1px solid rgba(138, 91, 255, 0.45); border-radius: 999px;
  padding: 0.3rem 1.1rem; cursor: pointer; transition: all .18s ease;
}
div[role="radiogroup"] > label > div:first-child { display: none; }
div[role="radiogroup"] > label p { font-family: 'Orbitron', sans-serif; font-size: 0.82rem; letter-spacing: 0.08em; margin: 0; }
div[role="radiogroup"] > label:hover { border-color: var(--cyan); box-shadow: 0 0 14px rgba(0, 240, 255, 0.35); }
div[role="radiogroup"] > label:has(input:checked) {
  background: linear-gradient(90deg, rgba(0, 240, 255, 0.22), rgba(255, 43, 214, 0.22));
  border-color: var(--cyan); box-shadow: 0 0 18px rgba(0, 240, 255, 0.45), inset 0 0 10px rgba(255, 43, 214, 0.2);
}

/* chat bubbles */
[data-testid="stChatMessage"] {
  background: var(--panel); border: 1px solid rgba(138, 91, 255, 0.4); border-radius: 16px;
  padding: 0.9rem 1.1rem; margin-bottom: 0.7rem; backdrop-filter: blur(8px);
  box-shadow: 0 0 16px rgba(138, 91, 255, 0.15);
}
[data-testid="stChatMessage"]:has(img[alt*="user"]), [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
  border-color: rgba(255, 43, 214, 0.5); box-shadow: 0 0 16px rgba(255, 43, 214, 0.18);
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
  border-color: rgba(0, 240, 255, 0.5); box-shadow: 0 0 16px rgba(0, 240, 255, 0.16);
}
[data-testid="stChatInput"] {
  background: rgba(10, 6, 30, 0.9); border: 1px solid var(--cyan); border-radius: 14px;
  box-shadow: 0 0 20px rgba(0, 240, 255, 0.35);
}
[data-testid="stChatInput"] textarea { color: var(--text); }
[data-testid="stBottom"] > div { background: transparent; }

/* buttons */
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
  background: linear-gradient(135deg, rgba(0, 240, 255, 0.16), rgba(255, 43, 214, 0.16));
  color: var(--text); border: 1px solid var(--cyan); border-radius: 10px;
  font-family: 'Orbitron', sans-serif; font-size: 0.78rem; letter-spacing: 0.08em;
  transition: all .18s ease; box-shadow: 0 0 10px rgba(0, 240, 255, 0.25);
}
.stButton > button:hover, .stDownloadButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover {
  border-color: var(--magenta); color: #fff; box-shadow: 0 0 20px rgba(255, 43, 214, 0.55); transform: translateY(-1px);
}
.stButton > button:focus-visible { outline: 2px solid var(--lime); outline-offset: 2px; }

/* inputs */
.stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"] > div {
  background: rgba(10, 6, 30, 0.85) !important; color: var(--text) !important;
  border: 1px solid rgba(138, 91, 255, 0.55) !important; border-radius: 10px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus { border-color: var(--cyan) !important; box-shadow: 0 0 14px rgba(0, 240, 255, 0.4) !important; }

/* uploader */
[data-testid="stFileUploaderDropzone"] {
  background: rgba(10, 6, 30, 0.7); border: 2px dashed var(--magenta); border-radius: 14px;
  box-shadow: 0 0 18px rgba(255, 43, 214, 0.2);
}

/* expanders / forms / code */
[data-testid="stExpander"], [data-testid="stForm"] {
  background: var(--panel); border: 1px solid rgba(138, 91, 255, 0.4) !important; border-radius: 14px;
}
[data-testid="stCodeBlock"], pre { background: rgba(5, 3, 15, 0.9) !important; border: 1px solid rgba(0, 240, 255, 0.25); border-radius: 10px; }

/* sidebar */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(14, 8, 38, 0.97), rgba(6, 3, 20, 0.97));
  border-right: 1px solid rgba(0, 240, 255, 0.35); box-shadow: 0 0 30px rgba(0, 240, 255, 0.12);
}

/* cards */
.card {
  background: var(--panel); border: 1px solid rgba(138, 91, 255, 0.4); border-radius: 14px;
  padding: 0.8rem 1rem; margin-bottom: 0.7rem;
}
.card .name { font-family: 'JetBrains Mono', monospace; color: var(--cyan); text-shadow: 0 0 8px rgba(0, 240, 255, 0.6); font-size: 1rem; }
.card .desc { color: var(--text); margin-top: 0.2rem; }
.badge { font-family: 'Orbitron', sans-serif; font-size: 0.65rem; letter-spacing: 0.1em; padding: 0.12rem 0.55rem; border-radius: 999px; margin-left: 0.6rem; }
.badge.local { color: var(--lime); border: 1px solid var(--lime); box-shadow: 0 0 8px rgba(182, 255, 60, 0.5); }
.badge.mcp { color: var(--magenta); border: 1px solid var(--magenta); box-shadow: 0 0 8px rgba(255, 43, 214, 0.5); }
.fact { border-left: 3px solid var(--magenta); padding: 0.35rem 0.8rem; margin: 0.35rem 0; background: rgba(255, 43, 214, 0.06); border-radius: 0 10px 10px 0; }
.status-dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; background: var(--lime); box-shadow: 0 0 10px var(--lime); margin-right: 0.5rem; }

::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-thumb { background: linear-gradient(var(--cyan), var(--magenta)); border-radius: 8px; }

@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>
"""
st.markdown(NEON_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Runtime: keeps one long-lived asyncio loop alive so MCP sessions survive
# Streamlit reruns, and records every tool call for the UI.
# ---------------------------------------------------------------------------
class Runtime:
    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self.ready = threading.Event()
        self.mcp_log = ""
        self.events: list[dict] = []
        self._patch_call_tool()
        self.thread = threading.Thread(target=self._thread_main, daemon=True)
        self.thread.start()
        self.ready.wait(timeout=60)

    def _patch_call_tool(self) -> None:
        original = harness.call_tool
        events = self.events

        async def logged(name, args):
            start = time.time()
            try:
                result = await original(name, args)
            except Exception as e:  # surface in UI, then let the harness see it
                events.append({"name": name, "args": args, "result": f"error: {e}", "secs": time.time() - start})
                raise
            events.append({"name": name, "args": args, "result": str(result), "secs": time.time() - start})
            return result

        harness.call_tool = logged  # run_agent looks this up at call time

    def _thread_main(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._lifespan())

    async def _lifespan(self) -> None:
        # Everything MCP lives inside this single task, so its context managers
        # are entered and exited by the same task for the app's whole lifetime.
        async with AsyncExitStack() as stack:
            buf = StringIO()
            try:
                with redirect_stdout(buf):
                    await harness.connect_mcp(stack)
            except Exception as e:
                buf.write(f"[mcp] startup error: {e}\n")
            self.mcp_log = buf.getvalue().strip()
            self.ready.set()
            await asyncio.Event().wait()

    def run(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result()


@st.cache_resource(show_spinner="Booting harness and connecting MCP servers...")
def get_runtime() -> Runtime:
    return Runtime()


rt = get_runtime()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def refresh_system_prompt() -> None:
    """Keep the system prompt's memory block in sync with memory.md."""
    harness.messages[0]["content"] = harness.SYSTEM_PROMPT.format(memory=harness.load_memory())


def memory_facts() -> list[str]:
    if not harness.MEMORY_FILE.is_file():
        return []
    return [ln[2:].strip() if ln.startswith("- ") else ln.strip()
            for ln in harness.MEMORY_FILE.read_text(encoding="utf-8").splitlines() if ln.strip()]


def workspace_files() -> list[Path]:
    return sorted(p for p in harness.WORKSPACE.iterdir() if p.is_file())


def safe_name(name: str) -> str:
    return Path(name.strip()).name  # blocks ../ path tricks


def render_tool_calls(calls: list[dict]) -> None:
    if not calls:
        return
    with st.expander(f"⚡ {len(calls)} tool call{'s' if len(calls) != 1 else ''}"):
        for c in calls:
            origin = "local" if c["name"] in harness.LOCAL_TOOLS else "mcp"
            st.markdown(
                f"<div class='card'><span class='name'>{c['name']}</span>"
                f"<span class='badge {origin}'>{origin.upper()}</span>"
                f"<span style='color:#8f86c4;float:right'>{c['secs']:.2f}s</span></div>",
                unsafe_allow_html=True,
            )
            st.code(json.dumps(c["args"], indent=2, ensure_ascii=False), language="json")
            st.code(c["result"][:1500] + ("..." if len(c["result"]) > 1500 else ""), language="text")


def run_command(line: str) -> str:
    """Slash commands from the CLI harness, rendered as markdown."""
    cmd, _, arg = line.partition(" ")
    arg = arg.strip()
    if cmd == "/models":
        rows = [f"- {'**▶**' if n == harness.model_name else '&nbsp;&nbsp;'} `{n}` → {c.model} ({c.base_url})"
                for n, c in harness.MODELS.items()]
        return "\n".join(rows)
    if cmd == "/model":
        if arg in harness.MODELS:
            harness.model_name = arg
            return f"Switched to `{arg}` ({harness.MODELS[arg].model})"
        return f"Unknown model `{arg}`. Try /models"
    if cmd == "/tools":
        rows = []
        for s in harness.TOOL_SCHEMAS:
            fn = s["function"]
            origin = "local" if fn["name"] in harness.LOCAL_TOOLS else "mcp"
            rows.append(f"- `[{origin}]` **{fn['name']}**: {(fn.get('description') or '')[:80]}")
        return "\n".join(rows)
    if cmd == "/memory":
        return harness.load_memory()
    if cmd == "/clear":
        reset_conversation()
        return "Conversation cleared."
    return "Commands: `/models` `/model <name>` `/tools` `/memory` `/clear`"


def reset_conversation() -> None:
    refresh_system_prompt()
    del harness.messages[1:]
    st.session_state.ui_history = []


def ask_agent(prompt: str) -> tuple[str, list[dict], str | None]:
    """Run one agent turn. Returns (answer, tool_calls, error)."""
    start_len = len(harness.messages)
    start_events = len(rt.events)
    try:
        answer = rt.run(harness.run_agent(prompt))
        err = None
    except Exception as e:
        del harness.messages[start_len:]  # roll back the half-finished turn
        answer, err = "", f"{type(e).__name__}: {e}"
    calls = rt.events[start_events:]
    refresh_system_prompt()
    return answer, calls, err


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
st.session_state.setdefault("ui_history", [])
st.session_state.setdefault("uploader_key", 0)
st.session_state.setdefault("queued_prompt", None)


def queue(prompt: str) -> None:
    st.session_state.queued_prompt = prompt


# ---------------------------------------------------------------------------
# Sidebar: model + status
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### MODEL")
    names = list(harness.MODELS)
    choice = st.selectbox("Active model", names, index=names.index(harness.model_name), label_visibility="collapsed")
    harness.model_name = choice
    cfg = harness.MODELS[choice]
    st.caption(f"`{cfg.model}`  \n{cfg.base_url}")
    if "api.openai.com" in cfg.base_url or "anthropic.com" in cfg.base_url:
        if not cfg.api_key:
            env = "OPENAI_API_KEY" if "openai" in cfg.base_url else "ANTHROPIC_API_KEY"
            st.warning(f"`{env}` is not set. Export it before launching Streamlit.")
    else:
        st.caption("Local model: make sure Ollama is running.")

    st.markdown("### LINK STATUS")
    st.markdown("<span class='status-dot'></span>Harness online", unsafe_allow_html=True)
    if rt.mcp_log:
        with st.expander("MCP log"):
            st.code(rt.mcp_log, language="text")

    st.markdown("### SESSION")
    if st.button("Clear conversation", use_container_width=True):
        reset_conversation()
        st.rerun()
    st.caption("Slash commands work in chat: /models /model /tools /memory /clear")

# ---------------------------------------------------------------------------
# Hero + stats
# ---------------------------------------------------------------------------
n_files = len(workspace_files())
n_facts = len(memory_facts())
n_mcp = sum(1 for s in harness.TOOL_SCHEMAS if s["function"]["name"] not in harness.LOCAL_TOOLS)
n_turns = sum(1 for m in st.session_state.ui_history if m["role"] == "user")

st.markdown(
    f"""
<div class="hero">
  <h1>AGENT H1 // NEON CONSOLE</h1>
  <p>Tools, MCP servers, long-term memory and your workspace in one place.</p>
</div>
<div class="stats">
  <div class="stat"><b>{len(harness.TOOL_SCHEMAS)}</b><span>tools ({n_mcp} MCP)</span></div>
  <div class="stat m"><b>{n_facts}</b><span>memories</span></div>
  <div class="stat l"><b>{n_files}</b><span>workspace files</span></div>
  <div class="stat"><b>{n_turns}</b><span>messages this session</span></div>
</div>
""",
    unsafe_allow_html=True,
)

view = st.radio("Section", ["💬 Chat", "🗂 Workshop", "🧠 Memory", "🛠 Tools"],
                horizontal=True, label_visibility="collapsed")

# ---------------------------------------------------------------------------
# CHAT
# ---------------------------------------------------------------------------
if view == "💬 Chat":
    for m in st.session_state.ui_history:
        with st.chat_message(m["role"], avatar="🧑‍💻" if m["role"] == "user" else "🤖"):
            if m.get("error"):
                st.error(m["error"])
            st.markdown(m["content"])
            render_tool_calls(m.get("tools", []))

    if not st.session_state.ui_history:
        st.markdown("#### Try one")
        c1, c2, c3 = st.columns(3)
        c1.button("📂 What's in my workspace?", on_click=queue, args=("What files are in my workspace?",), use_container_width=True)
        c2.button("🧠 What do you remember?", on_click=queue, args=("What do you remember about me?",), use_container_width=True)
        c3.button("✍️ Make a todo file", on_click=queue,
                  args=("Create a file called todo.md with a starter todo list for this week.",), use_container_width=True)

    prompt = st.chat_input("Talk to the agent, or type /tools, /memory, /models ...")
    if not prompt and st.session_state.queued_prompt:
        prompt, st.session_state.queued_prompt = st.session_state.queued_prompt, None

    if prompt:
        prompt = prompt.strip()
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(prompt)
        st.session_state.ui_history.append({"role": "user", "content": prompt})

        with st.chat_message("assistant", avatar="🤖"):
            if prompt.startswith("/"):
                out = run_command(prompt)
                st.markdown(out)
                st.session_state.ui_history.append({"role": "assistant", "content": out})
            else:
                with st.spinner(f"{harness.MODELS[harness.model_name].model} is thinking..."):
                    answer, calls, err = ask_agent(prompt)
                if err:
                    st.error(f"Agent call failed. {err}")
                    st.caption("Check that the model server is running and the API key is set.")
                    st.session_state.ui_history.append(
                        {"role": "assistant", "content": "_(no response)_", "error": err})
                else:
                    st.markdown(answer or "_(empty response)_")
                    render_tool_calls(calls)
                    st.session_state.ui_history.append(
                        {"role": "assistant", "content": answer or "_(empty response)_", "tools": calls})
        # Refresh the stat chips if this turn changed files or memory.
        last_tools = st.session_state.ui_history[-1].get("tools") or []
        if prompt.startswith("/clear") or any(c["name"] in ("write_file", "save_memory") for c in last_tools):
            st.rerun()

# ---------------------------------------------------------------------------
# WORKSHOP (workspace files)
# ---------------------------------------------------------------------------
elif view == "🗂 Workshop":
    left, right = st.columns([1, 1.25], gap="large")

    with left:
        st.markdown("### UPLOAD")
        uploads = st.file_uploader(
            "Drop files into the workspace", accept_multiple_files=True,
            key=f"uploader_{st.session_state.uploader_key}",
        )
        if uploads and st.button("Send to workspace", use_container_width=True):
            for up in uploads:
                (harness.WORKSPACE / safe_name(up.name)).write_bytes(up.getvalue())
            st.session_state.uploader_key += 1
            st.toast(f"Uploaded {len(uploads)} file(s)", icon="⚡")
            st.rerun()
        st.caption("The agent reads files as UTF-8 text, so text, markdown, code, CSV and JSON work best.")

        st.markdown("### CREATE")
        with st.form("create_file", clear_on_submit=True):
            new_name = st.text_input("File name", placeholder="ideas.md")
            new_body = st.text_area("Content", height=180, placeholder="Write something...")
            if st.form_submit_button("Create file", use_container_width=True):
                name = safe_name(new_name)
                if not name:
                    st.error("Give the file a name.")
                else:
                    harness.write_file(name, new_body)
                    st.toast(f"Created {name}", icon="✨")
                    st.rerun()

    with right:
        st.markdown("### WORKSPACE")
        files = workspace_files()
        if not files:
            st.info("The workspace is empty. Upload a file or create one, or ask the agent to write something.")
        else:
            picked = st.selectbox("Open file", [f.name for f in files])
            path = harness.WORKSPACE / picked
            raw = path.read_bytes()
            st.caption(f"{len(raw):,} bytes")
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = None

            if text is None:
                st.warning("Binary file. It can be downloaded here, but the agent can't read it as text.")
            else:
                edited = st.text_area("Content", text, height=320, key=f"edit_{picked}_{len(raw)}")
                if st.button("Save changes", use_container_width=True):
                    path.write_text(edited, encoding="utf-8")
                    st.toast(f"Saved {picked}", icon="💾")
                    st.rerun()

            d1, d2 = st.columns(2)
            d1.download_button("Download", raw, file_name=picked, use_container_width=True)
            if d2.button("Delete file", use_container_width=True):
                path.unlink(missing_ok=True)
                st.toast(f"Deleted {picked}", icon="🗑")
                st.rerun()

            with st.expander("All files"):
                for f in files:
                    st.markdown(f"<div class='card'><span class='name'>{f.name}</span>"
                                f"<span style='color:#8f86c4;float:right'>{f.stat().st_size:,} B</span></div>",
                                unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# MEMORY
# ---------------------------------------------------------------------------
elif view == "🧠 Memory":
    left, right = st.columns([1.2, 1], gap="large")

    with left:
        st.markdown("### LONG-TERM MEMORY")
        facts = memory_facts()
        if not facts:
            st.info("Nothing saved yet. Tell the agent something lasting about you, or add a fact here.")
        for f in facts:
            st.markdown(f"<div class='fact'>{f}</div>", unsafe_allow_html=True)
        st.caption(f"Stored in `{harness.MEMORY_FILE.name}` and injected into the system prompt.")

    with right:
        st.markdown("### ADD A FACT")
        with st.form("add_fact", clear_on_submit=True):
            fact = st.text_input("Fact", placeholder="Prefers short answers")
            if st.form_submit_button("Save to memory", use_container_width=True) and fact.strip():
                harness.save_memory(fact.strip())
                refresh_system_prompt()
                st.toast("Memory saved", icon="🧠")
                st.rerun()

        st.markdown("### EDIT RAW FILE")
        raw_mem = harness.MEMORY_FILE.read_text(encoding="utf-8") if harness.MEMORY_FILE.is_file() else ""
        new_mem = st.text_area("memory.md", raw_mem, height=200, label_visibility="collapsed", key=f"mem_{len(raw_mem)}")
        m1, m2 = st.columns(2)
        if m1.button("Save edits", use_container_width=True):
            harness.MEMORY_FILE.write_text(new_mem, encoding="utf-8")
            refresh_system_prompt()
            st.toast("Memory file updated", icon="💾")
            st.rerun()
        if m2.button("Wipe memory", use_container_width=True):
            harness.MEMORY_FILE.unlink(missing_ok=True)
            refresh_system_prompt()
            st.toast("Memory wiped", icon="🗑")
            st.rerun()

# ---------------------------------------------------------------------------
# TOOLS
# ---------------------------------------------------------------------------
else:
    st.markdown("### TOOL REGISTRY")
    st.caption("Local tools plus everything discovered from mcp_servers.json. The model calls these on its own during chat.")
    for s in harness.TOOL_SCHEMAS:
        fn = s["function"]
        origin = "local" if fn["name"] in harness.LOCAL_TOOLS else "mcp"
        st.markdown(
            f"<div class='card'><span class='name'>{fn['name']}</span><span class='badge {origin}'>{origin.upper()}</span>"
            f"<div class='desc'>{fn.get('description') or ''}</div></div>",
            unsafe_allow_html=True,
        )
        with st.expander("parameters"):
            st.code(json.dumps(fn.get("parameters", {}), indent=2), language="json")
    if n_mcp == 0:
        st.info("No MCP tools connected. Add servers to mcp_servers.json and restart the app.")
