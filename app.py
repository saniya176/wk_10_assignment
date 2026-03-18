import json
import os
import re
import time
import uuid
from pathlib import Path
from typing import Generator

import requests
import streamlit as st


APP_DIR = Path(__file__).parent
CHATS_DIR = APP_DIR / "chats"
MEMORY_FILE = APP_DIR / "memory.json"

DEFAULT_MODEL = "meta-llama/Llama-3.2-1B-Instruct"
MAX_TOKENS = 1024
HF_CHAT_URL = "https://router.huggingface.co/v1/chat/completions"


# ---------- Helpers ----------

def load_chat_data(file_path: Path) -> dict:
    if not file_path.exists():
        now = time.time()
        return {
            "id": file_path.stem,
            "title": "New Chat",
            "created_at": now,
            "updated_at": now,
            "messages": [],
        }
    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        now = time.time()
        return {
            "id": data.get("id", file_path.stem),
            "title": data.get("title", "New Chat"),
            "created_at": data.get("created_at", now),
            "updated_at": data.get("updated_at", now),
            "messages": data.get("messages", []),
        }
    except Exception:
        now = time.time()
        return {
            "id": file_path.stem,
            "title": "New Chat",
            "created_at": now,
            "updated_at": now,
            "messages": [],
        }


def save_chat(
    file_path: Path, messages: list[dict], title: str, created_at: float, chat_id: str
) -> None:
    payload = {
        "id": chat_id,
        "title": title,
        "created_at": created_at,
        "updated_at": time.time(),
        "messages": messages,
    }
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def load_memory() -> dict:
    if not MEMORY_FILE.exists():
        save_memory({})
        return {}
    try:
        with MEMORY_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        save_memory({})
        return {}
    except Exception:
        save_memory({})
        return {}


def save_memory(memory: dict) -> None:
    with MEMORY_FILE.open("w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2)


def merge_memory(existing: dict, new_data: dict) -> dict:
    merged = dict(existing)
    for key, value in new_data.items():
        if value in ("", None):
            continue
        merged[key] = value
    return merged


def memory_system_prompt(memory: dict) -> str:
    if not memory:
        return ""
    return (
        "You are a helpful assistant. Use the following user memory to personalize "
        "your responses. If irrelevant, ignore it.\n\n"
        f"User memory (JSON): {json.dumps(memory)}"
    )


def extract_memory_from_message(message: str, token: str) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    prompt = (
        "Given this user message, extract any personal facts or preferences as a JSON "
        "object. If none, return {}. Return only JSON.\n\n"
        f"User message: {message}"
    )
    payload = {
        "model": DEFAULT_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 256,
    }
    response = requests.post(HF_CHAT_URL, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    try:
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}




def hf_chat_completion(messages: list[dict], model: str, token: str) -> str:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": MAX_TOKENS,
    }
    response = requests.post(HF_CHAT_URL, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def hf_chat_completion_stream(
    messages: list[dict], model: str, token: str
) -> Generator[str, None, None]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": MAX_TOKENS,
        "stream": True,
    }
    response = requests.post(
        HF_CHAT_URL, headers=headers, json=payload, timeout=60, stream=True
    )
    response.raise_for_status()

    for raw_line in response.iter_lines(decode_unicode=True):
        if not raw_line:
            continue
        line = raw_line.strip()
        if not line.startswith("data:"):
            continue
        data = line.replace("data:", "", 1).strip()
        if data == "[DONE]":
            break
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            continue
        choices = payload.get("choices") or []
        if not choices:
            continue
        delta = choices[0].get("delta", {}).get("content", "")
        if delta:
            yield delta
            time.sleep(0.02)


# ---------- UI ----------

st.set_page_config(page_title="My AI Chat", layout="wide")

st.title("My AI Chat")


def get_hf_token() -> str | None:
    try:
        token = st.secrets["HF_TOKEN"]
    except Exception:
        token = ""
    if not token or not str(token).strip():
        st.error("Missing HF_TOKEN in .streamlit/secrets.toml")
        return None
    return token

# Sidebar: session management
CHATS_DIR.mkdir(exist_ok=True)

if "session_id" not in st.session_state:
    st.session_state.session_id = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "chat_title" not in st.session_state:
    st.session_state.chat_title = "New Chat"

if "chat_created_at" not in st.session_state:
    st.session_state.chat_created_at = time.time()

if "user_memory" not in st.session_state:
    st.session_state.user_memory = load_memory()


def list_chats() -> list[dict]:
    chats = []
    for file_path in CHATS_DIR.glob("*.json"):
        data = load_chat_data(file_path)
        chats.append(
            {
                "id": file_path.stem,
                "title": data["title"],
                "created_at": data["created_at"],
                "updated_at": data["updated_at"],
                "path": file_path,
            }
        )
    chats.sort(key=lambda c: c["updated_at"], reverse=True)
    return chats


def create_new_chat() -> None:
    chat_id = f"chat_{uuid.uuid4().hex[:8]}"
    created = time.time()
    title = "New Chat"
    st.session_state.session_id = chat_id
    st.session_state.messages = []
    st.session_state.chat_title = title
    st.session_state.chat_created_at = created
    save_chat(CHATS_DIR / f"{chat_id}.json", [], title, created, chat_id)


def load_chat_into_state(chat_id: str) -> None:
    data = load_chat_data(CHATS_DIR / f"{chat_id}.json")
    st.session_state.session_id = chat_id
    st.session_state.messages = data["messages"]
    st.session_state.chat_title = data["title"]
    st.session_state.chat_created_at = data["created_at"]


def delete_chat(chat_id: str) -> None:
    file_path = CHATS_DIR / f"{chat_id}.json"
    if file_path.exists():
        file_path.unlink()
    if st.session_state.session_id == chat_id:
        remaining = list_chats()
        if remaining:
            load_chat_into_state(remaining[0]["id"])
        else:
            st.session_state.session_id = None
            st.session_state.messages = []
            st.session_state.chat_title = "New Chat"
            st.session_state.chat_created_at = time.time()


with st.sidebar:
    st.header("Chats")
    with st.expander("User Memory", expanded=True):
        st.json(st.session_state.user_memory)
        if st.button("Clear Memory"):
            st.session_state.user_memory = {}
            save_memory({})
            st.rerun()

    if st.button("New Chat"):
        create_new_chat()

    chats = list_chats()
    if st.session_state.session_id is None:
        if chats:
            load_chat_into_state(chats[0]["id"])
        else:
            create_new_chat()
            chats = list_chats()

    for chat in chats:
        is_active = chat["id"] == st.session_state.session_id
        timestamp = time.strftime("%b %d %H:%M", time.localtime(chat["updated_at"]))
        with st.container(border=is_active):
            cols = st.columns([0.82, 0.18])
            label = f"{chat['title']} • {timestamp}"
            if cols[0].button(label, key=f"open_{chat['id']}"):
                load_chat_into_state(chat["id"])
            if cols[1].button("✕", key=f"del_{chat['id']}"):
                delete_chat(chat["id"])
                st.rerun()

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
            token = get_hf_token()
            if not token:
                raise ValueError("Missing HF_TOKEN in .streamlit/secrets.toml")
            model = st.secrets.get("HF_MODEL", DEFAULT_MODEL)
            api_messages = list(st.session_state.messages)
            system_prompt = memory_system_prompt(st.session_state.user_memory)
            if system_prompt:
                api_messages = [{"role": "system", "content": system_prompt}] + api_messages
            stream_area = st.empty()
            collected = ""
            for chunk in hf_chat_completion_stream(api_messages, model, token):
                collected += chunk
                stream_area.markdown(collected)
            response_text = collected
        except Exception as exc:
            response_text = f"Error: {exc}"
            st.error(response_text)

    st.session_state.messages.append({"role": "assistant", "content": response_text})

    # Update title from first user message if still default
    if st.session_state.chat_title == "New Chat":
        st.session_state.chat_title = prompt.strip()[:40] or "New Chat"

    # Persist session
    session_file = CHATS_DIR / f"{st.session_state.session_id}.json"
    save_chat(
        session_file,
        st.session_state.messages,
        st.session_state.chat_title,
        st.session_state.chat_created_at,
        st.session_state.session_id,
    )

    # Extract and persist user memory
    try:
        token = get_hf_token()
        if token:
            extracted = extract_memory_from_message(prompt, token)
            if extracted:
                st.session_state.user_memory = merge_memory(
                    st.session_state.user_memory, extracted
                )
            save_memory(st.session_state.user_memory)
    except Exception:
        pass
