import os
import time
from google import genai
from google.genai import types
from google.genai import errors
from dotenv import load_dotenv
from search import hybrid_search
from ingest import list_documents

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ─── System Prompt ──────────────────────────────────────────────────
SYSTEM_PROMPT = """You are SearchBot, an intelligent AI document assistant.

Your job is to help users find accurate information from their uploaded documents.

Rules you must always follow:
1. ONLY answer based on the document excerpts provided to you.
2. ALWAYS cite your source at the end of every answer.
   Format: [Source: filename.pdf, Page X]
3. If the answer is NOT in the provided excerpts, say:
   "I couldn't find this information in your uploaded documents."
4. If multiple documents are involved, compare them clearly.
5. Keep answers clear, concise, and well-structured.
6. Never make up information or use your own knowledge.
7. If a question is vague, ask the user to clarify.
"""

def format_context(search_results: list) -> str:
    """Turn search results into readable context for Gemini"""
    if not search_results:
        return "No relevant information found in the uploaded documents."

    context = "DOCUMENT EXCERPTS FOUND:\n"
    context += "=" * 60 + "\n\n"

    for i, r in enumerate(search_results, 1):
        context += f"Excerpt {i}:\n"
        context += f"Document : {r['doc_name']}\n"
        context += f"Page     : {r['page_num']}\n"
        context += f"Content  : {r['content']}\n"
        context += "-" * 60 + "\n\n"

    return context


class SearchBotAgent:
    """Main agent class that combines Gemini + Elasticsearch"""

    def __init__(self):
        self.chat = client.chats.create(
            model="gemini-2.5-flash-lite",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.1,
                max_output_tokens=1024
            )
        )

    def ask(self, question: str) -> str:
        """
        Main pipeline:
        1. Search Elasticsearch for relevant chunks
        2. Build prompt with search results as context
        3. Send to Gemini for reasoning
        4. Return cited answer
        """

        # Step 1: Search documents
        search_results = hybrid_search(question, top_k=6)
        context        = format_context(search_results)

        # Step 2: Build message with context injected
        message = f"""User Question: {question}

{context}

Please answer the user's question using ONLY the above excerpts.
Cite which document and page number your answer comes from."""

        # Step 3: Send to Gemini with retry logic for rate limits
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.chat.send_message(message)
                return response.text

            except errors.APIError as e:
                # Retry on rate limit (429) errors
                if e.code == 429 and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 15  # 15s, 30s, 45s
                    print(f"⏳ Rate limited, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(wait_time)
                    continue
                return f"❌ Error generating response: {e.message}"
            except Exception as e:
                return f"❌ Error generating response: {str(e)}"

    def reset(self):
        """Clear conversation history"""
        self.chat = client.chats.create(
            model="gemini-2.5-flash-lite",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.1,
                max_output_tokens=1024
            )
        )
        print("Chat history cleared")

    def get_docs(self) -> list:
        """Return list of indexed documents"""
        return list_documents()


# Single agent instance for the whole app
agent = SearchBotAgent()