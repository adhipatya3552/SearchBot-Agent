import streamlit as st
import requests
import os

# ─── Config ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SearchBot",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Backend URL — change this after Render deployment
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")

# Initialize file uploader state to clear it on indexing success
if "file_uploader_key" not in st.session_state:
    st.session_state["file_uploader_key"] = 0

@st.cache_data(ttl=15)
def get_indexed_documents(api_url: str) -> list:
    try:
        r = requests.get(f"{api_url}/documents", timeout=5)
        if r.status_code == 200:
            return r.json().get("documents", [])
    except Exception:
        pass
    return []

# ─── Custom Styling ──────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Space Grotesk', sans-serif;
    }
    .hero-title {
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(135deg, #FF6B6B, #4ECDC4, #45B7D1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        line-height: 1.2;
    }
    .hero-sub {
        font-size: 1.15rem;
        color: #888;
        margin-bottom: 2rem;
    }
    .stat-box {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border: 1px solid #0f3460;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        color: white;
    }
    .doc-tag {
        display: inline-block;
        background: #e8f4ff;
        border: 1px solid #4ECDC4;
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 0.82rem;
        color: #0071c5;
        margin: 3px;
    }
    .answer-box {
        background: rgb(14, 17, 23);
        border-left: 4px solid #4ECDC4;
        padding: 16px 20px;
        border-radius: 8px;
        margin-top: 8px;
        color: #e0e0e0;
    }
    .stChatMessage {
        border-radius: 16px !important;
    }
    div[data-testid="stFileUploadDropzone"] {
        border: 2px dashed #4ECDC4 !important;
        border-radius: 12px !important;
    }
    [data-testid="stSidebarContent"] {
        padding-bottom: 2rem !important;
    }
    [data-testid="stSidebarContent"] [data-testid="stVerticalBlock"] {
        gap: 1.5rem !important;
    }
    [data-testid="stSidebarContent"] div[data-testid="stMarkdown"] hr {
        margin-top: 0.75rem !important;
        margin-bottom: 0.75rem !important;
    }
</style>
""", unsafe_allow_html=True)

# ─── Sidebar ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📁 Documents")
    st.caption("Upload documents to start asking questions")
    st.divider()

    # File uploader
    uploaded = st.file_uploader(
        "Drop files here",
        type=["pdf", "txt", "docx", "csv", "md"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        key=f"uploader_{st.session_state['file_uploader_key']}"
    )

    if uploaded:
        if st.button("⚡ Index Documents", type="primary", use_container_width=True):
            bar = st.progress(0, text="Starting...")
            success_count = 0

            for i, f in enumerate(uploaded):
                base_pct = int((i / len(uploaded)) * 100)
                next_pct = int(((i + 1) / len(uploaded)) * 100)
                try:
                    r = requests.post(
                        f"{API_URL}/upload",
                        files={"file": (f.name, f.getvalue(), "application/octet-stream")},
                        timeout=120,
                        stream=True
                    )
                    if r.status_code == 200:
                        import json
                        for line in r.iter_lines():
                            if line:
                                data = json.loads(line.decode("utf-8"))
                                if data.get("type") == "progress":
                                    current = data["current"]
                                    total = data["total"]
                                    pct = base_pct + int((current / total) * (next_pct - base_pct))
                                    bar.progress(
                                        pct,
                                        text=f"Indexing {f.name} (Chunk {current}/{total})..."
                                    )
                                elif data.get("type") == "complete":
                                    st.success(f"✅ {f.name} ({data.get('chunks_indexed')} chunks)")
                                    success_count += 1
                                elif data.get("type") == "error":
                                    st.error(f"❌ {f.name}: {data.get('message')}")
                    else:
                        st.error(f"❌ {f.name}: Error code {r.status_code}")
                except Exception as e:
                    st.error(f"❌ {f.name}: {e}")

            bar.progress(100, text="Done!")
            if success_count > 0:
                st.cache_data.clear()
                st.session_state["file_uploader_key"] += 1
                st.balloons()
                st.rerun()

    st.divider()

    # Show indexed documents
    st.markdown("### 📚 Indexed Documents")
    try:
        docs = get_indexed_documents(API_URL)
        if docs:
            for doc in docs:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(
                        f'<span class="doc-tag">📄 {doc[:25]}{"..." if len(doc) > 25 else ""}</span>',
                        unsafe_allow_html=True
                    )
                with col2:
                    if st.button("✕", key=f"del_{doc}",
                                 help=f"Remove {doc}"):
                        try:
                            requests.delete(
                                f"{API_URL}/documents/{doc}",
                                timeout=10
                            )
                            st.cache_data.clear()
                            st.rerun()
                        except Exception:
                            st.error("Delete failed")


        else:
            st.info("📭 No documents yet.\nUpload some files above!")
    except Exception:
        st.warning("⚠️ Backend not reachable.\nMake sure it's running.")

    st.divider()

    # Reset button
    if st.button("🔄 Clear Conversation", use_container_width=True):
        try:
            requests.post(f"{API_URL}/reset", timeout=10)
        except Exception:
            pass
        st.session_state.messages = []
        st.rerun()

# ─── Main Area ───────────────────────────────────────────────────────
st.markdown('<div class="hero-title">🔍 SearchBot</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-sub">Ask anything about your documents in plain English. '
    'Powered by <b>Gemini</b> + <b>Elasticsearch</b>.</div>',
    unsafe_allow_html=True
)

# Example questions
with st.expander("💡 Try these example questions"):
    examples = [
        "What is the main topic of the uploaded document?",
        "Summarize the key findings",
        "What are the important dates mentioned?",
        "What does the document say about [your topic]?",
        "Compare the information across all documents"
    ]
    cols = st.columns(2)
    for i, ex in enumerate(examples):
        with cols[i % 2]:
            if st.button(ex, key=f"ex_{i}", use_container_width=True):
                st.session_state["pending"] = ex

st.divider()

# ─── Chat ────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# Show chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"],
                         avatar="🧑‍💻" if msg["role"] == "user" else "🤖"):
        st.markdown(msg["content"])

# Get input — either from example button or typed
question = st.session_state.pop("pending", None) or \
           st.chat_input("Ask a question about your documents...")

if question:
    # Show user message
    st.session_state.messages.append({
        "role":    "user",
        "content": question
    })
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(question)

    # Get answer from agent
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("🔍 Searching documents..."):
            try:
                r = requests.post(
                    f"{API_URL}/ask",
                    json={"question": question},
                    timeout=60
                )
                if r.status_code == 200:
                    answer = r.json()["answer"]
                    st.markdown(
                        f'<div class="answer-box">{answer}</div>',
                        unsafe_allow_html=True
                    )
                    st.session_state.messages.append({
                        "role":    "assistant",
                        "content": answer
                    })
                else:
                    err = r.json().get("detail", "Unknown error")
                    st.error(f"Error: {err}")

            except requests.exceptions.Timeout:
                st.error("⏱️ Request timed out. Try again.")
            except requests.exceptions.ConnectionError:
                st.error("🔌 Cannot connect to backend. Is it running?")
            except Exception as e:
                st.error(f"Something went wrong: {e}")