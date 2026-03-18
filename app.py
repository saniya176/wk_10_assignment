import json
import os
import time
import uuid
from pathlib import Path

import requests
import streamlit as st


APP_DIR = Path(__file__).parent
CHATS_DIR = APP_DIR / "chats"
LOG_FILE = APP_DIR / "ai_interaction_log.md"

DEFAULT_MODEL = "mistralai/Mistral-7B-Instruct-v0.2"
HF_CHAT_URL = "https://router.huggingface.co/v1/chat/completions"


# ---------- Helpers ----------

def load_chat(file_path: Path) -> list[dict]:
    if not file_path.exists():
        return []
    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("messages", [])
    except Exception:
        return []


def save_chat(file_path: Path, messages: list[dict]) -> None:
    payload = {
        "updated_at": time.time(),
        "messages": messages,
    }
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def log_interaction(user_text: str, assistant_text: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    entry = (
        f"\n## {timestamp}\n"
        f"**User:** {user_text}\n\n"
        f"**Assistant:** {assistant_text}\n"
    )
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(entry)


def hf_chat_completion(messages: list[dict], model: str, token: str) -> str:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 512,
    }
    response = requests.post(HF_CHAT_URL, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


# ---------- UI ----------

st.set_page_config(page_title="ChatGPT Clone", page_icon="C")

st.title("ChatGPT Clone")

# Sidebar: session management
CHATS_DIR.mkdir(exist_ok=True)

chat_files = sorted(CHATS_DIR.glob("*.json"), key=os.path.getmtime, reverse=True)
chat_labels = [f.stem for f in chat_files]

if "session_id" not in st.session_state:
    st.session_state.session_id = None

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.header("Sessions")

    new_chat = st.button("+ New Chat")
    selected = st.selectbox(
        "Open session",
        options=["(current)"] + chat_labels,
        index=0,
    )

    if new_chat:
        st.session_state.session_id = f"chat_{uuid.uuid4().hex[:8]}"
        st.session_state.messages = []

    if selected != "(current)":
        st.session_state.session_id = selected
        st.session_state.messages = load_chat(CHATS_DIR / f"{selected}.json")

if st.session_state.session_id is None:
    st.session_state.session_id = f"chat_{uuid.uuid4().hex[:8]}"

# Display existing messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Ask something...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            token = st.secrets.get("HF_TOKEN", "")
            if not token:
                raise ValueError("Missing HF_TOKEN in .streamlit/secrets.toml")
            model = st.secrets.get("HF_MODEL", DEFAULT_MODEL)
            response_text = hf_chat_completion(st.session_state.messages, model, token)
            st.markdown(response_text)
        except Exception as exc:
            response_text = f"Error: {exc}"
            st.error(response_text)

    st.session_state.messages.append({"role": "assistant", "content": response_text})

    # Persist session
    session_file = CHATS_DIR / f"{st.session_state.session_id}.json"
    save_chat(session_file, st.session_state.messages)

    # Log interaction
    log_interaction(prompt, response_text)
