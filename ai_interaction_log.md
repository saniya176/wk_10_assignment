### Task: Task 1 - Part A API Setup
**Prompt:** "Implement Task 1 Part A requirements for page setup and API connection, then update this log."
**AI Suggestion:** Updated `app.py` to use `st.set_page_config(page_title="My AI Chat", layout="wide")`, load `HF_TOKEN` via `st.secrets["HF_TOKEN"]`, show a clear error if missing, send a hardcoded "Hello!" to the HF chat endpoint, and display the response with graceful API error handling.
**My Modifications & Reflections:** Changes applied directly in code; keep token in `.streamlit/secrets.toml` and verify the API test shows a response.

### Task: Task 1 - Part B Multi-Turn UI
**Prompt:** "Implement Task 1 Part B: replace the hardcoded test with a real multi-turn chat UI using Streamlit chat components, store history in session_state, send full history to the API, and keep input fixed at the bottom."
**AI Suggestion:** Removed the Part A hardcoded test section and kept the Streamlit chat interface: `st.chat_message` renders history, `st.chat_input` collects user input, full `st.session_state.messages` is sent on each request, and missing token errors are shown in-app without crashing.
**My Modifications & Reflections:** Updated `app.py` accordingly; chat UI now satisfies Part B requirements with native Streamlit elements.

### Task: Task 1 - Part C Chat Management
**Prompt:** "Implement Task 1 Part C: add sidebar chat management with new chat, list with title+timestamp, active highlight, switching, and delete per chat, then update this log."
**AI Suggestion:** Added sidebar chat management using native Streamlit: `New Chat` button creates a fresh chat and saves it, sidebar lists chats from `chats/*.json` with title and last-updated timestamp, active chat is highlighted via bordered containers, clicking a chat loads it, and ✕ deletes a chat with safe fallback if the active one is removed.
**My Modifications & Reflections:** Updated `app.py` and saved metadata per chat; chat list now supports create/switch/delete with active highlighting.

### Task: Task 1 - Part D Chat Persistence
**Prompt:** "Implement Task 1 Part D: ensure each chat saves to its own JSON file with id/title/messages, load chats on startup, support resume, and delete files on delete. Then update this log."
**AI Suggestion:** Added explicit `id` field to each chat JSON, ensured chat metadata is loaded from disk and listed in the sidebar on startup, persisted chats on each exchange, and delete now removes the corresponding JSON file while safely switching to another chat or empty state.
**My Modifications & Reflections:** Updated `app.py` so each chat file includes `id` along with title/timestamps/messages; persistence now meets Part D requirements.

### Task: Task 2 - Response Streaming
**Prompt:** "Update Task 2 to resolve streaming errors and ensure stable incremental output."
**AI Suggestion:** Implemented streaming with SSE parsing, guarded empty chunks, and ensured the UI updates incrementally with a visible delay.
**My Modifications & Reflections:** Streaming now renders reliably without index/type errors, and responses save correctly to history.

### Task: Task 3 - User Memory
**Prompt:** "Fix memory extraction so memory.json updates reliably and handle non-JSON model output."
**AI Suggestion:** Initialize memory.json to {}, always persist after each response, and add a JSON-extraction fallback for imperfect model output.
**My Modifications & Reflections:** Memory now persists across runs and displays in the sidebar; clear/reset works as expected.

