# 🔍 SearchBot — AI Document Intelligence Agent

> Upload any documents. Ask anything. Get accurate answers with citations.
> Built for the **Google Cloud Rapid Agent Hackathon** — Elastic Track.

## 🚀 Live Demo
**[Try SearchBot Live →](https://searchbot-agent.streamlit.app)**

## ✨ What It Does
- Upload multiple documents (PDF, TXT, DOCX, CSV, MD)
- Ask questions in plain English — no commands, no syntax
- Get precise answers with exact source citations (document + page/offset number)
- Reason across multiple documents simultaneously
- Multi-turn conversation — remembers context of your questions

## 🏗️ Architecture

User → Streamlit UI → FastAPI Backend → Hybrid Search (Elastic) → Gemini 2.5 Flash Lite → Answer with Citations

## 🛠️ Tech Stack
| Component       | Technology                          |
|----------------|-------------------------------------|
| AI Model        | Google Gemini 2.5 Flash Lite        |
| Embeddings      | Gemini text-embedding-004           |
| Search Engine   | Elasticsearch (Elastic Cloud)       |
| MCP Integration | Elastic Agent Builder MCP Server    |
| Backend         | FastAPI + Python                    |
| Frontend        | Streamlit                           |
| Backend Host    | Render.com                          |
| Frontend Host   | Streamlit Cloud                     |

## 🌍 Real-World Use Cases
- **Law firms** → Search across hundreds of case files instantly
- **Hospitals** → Query patient records, policies, and guidelines
- **Universities** → Students search through research papers and notes
- **Companies** → Employees find answers in internal documents

## 📦 Local Setup

```bash
# Clone the repository
git clone https://github.com/adhipatya3552/SearchBot-Agent.git
cd SearchBot-Agent

# Set up local environment variables
cp .env.example .env
# Open .env and fill in your real keys

# Run the FastAPI backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# In a separate terminal, run the Streamlit frontend
cd ../frontend
pip install -r requirements.txt
streamlit run app.py
```

## 💰 Monetization
- SaaS subscription: ₹499/month per organization
- API access for enterprises
- White-label licensing

## 📄 License
Apache 2.0 — see [LICENSE](LICENSE)