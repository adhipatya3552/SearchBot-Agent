import os
import httpx
from dotenv import load_dotenv

load_dotenv()

class ElasticMCPClient:
    """
    Connects to Elastic Agent Builder's MCP endpoint.
    This is what officially qualifies the project for the Elastic track.
    """

    def __init__(self):
        self.kibana_url = os.getenv("KIBANA_URL", "").rstrip("/")
        self.api_key    = os.getenv("ELASTIC_API_KEY")
        self.headers    = {
            "Authorization": f"ApiKey {self.api_key}",
            "Content-Type":  "application/json",
            "kbn-xsrf":      "true"
        }

    def search_via_mcp(self, query: str) -> dict:
        """Call Elastic Agent Builder search tool via MCP"""
        try:
            response = httpx.post(
                f"{self.kibana_url}/api/agent_builder/mcp",
                headers=self.headers,
                json={
                    "tool":  "search_documents",
                    "input": {"query": query}
                },
                timeout=15.0
            )

            if response.status_code == 200:
                return {"status": "success", "data": response.json()}
            else:
                return {"status": "fallback", "reason": response.text}

        except Exception as e:
            return {"status": "error", "reason": str(e)}

    def get_agent_info(self) -> dict:
        """Get info about the Elastic Agent Builder instance"""
        try:
            response = httpx.get(
                f"{self.kibana_url}/api/agent_builder/agents",
                headers=self.headers,
                timeout=10.0
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}

# Single instance used across the app
elastic_mcp = ElasticMCPClient()