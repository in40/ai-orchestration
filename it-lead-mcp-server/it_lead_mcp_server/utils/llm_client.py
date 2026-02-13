"""
Mock LLM Client for IT Lead MCP Server
Provides LLM functionality for enhanced capabilities
"""
import requests
import json
from typing import Dict, Any, Optional


class MockLlmClient:
    """Mock LLM client that interfaces with the LLM provider"""
    
    def __init__(self, llm_provider_url: str, llm_model: str):
        self.llm_provider_url = llm_provider_url
        self.llm_model = llm_model
    
    def call_llm(self, prompt: str, temperature: float = 0.7) -> str:
        """Call the LLM with the given prompt"""
        try:
            headers = {
                "Content-Type": "application/json"
            }

            data = {
                "model": self.llm_model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature
            }

            response = requests.post(self.llm_provider_url, headers=headers, json=data)

            if response.status_code == 200:
                result = response.json()
                # Extract the content from the response
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"]
                else:
                    return "LLM response format not recognized"
            else:
                print(f"LLM API call failed with status {response.status_code}: {response.text}")
                return f"LLM call failed: {response.status_code}"

        except Exception as e:
            print(f"Error calling LLM: {e}")
            return f"LLM call failed: {str(e)}"
    
    def evaluate(self, prompt: str) -> Dict[str, Any]:
        """Evaluate content using the LLM"""
        response = self.call_llm(prompt)
        try:
            # Try to parse as JSON if possible
            return json.loads(response)
        except json.JSONDecodeError:
            # If not JSON, return as text
            return {"response": response, "parsed": False}
    
    def generate(self, prompt: str) -> str:
        """Generate content using the LLM"""
        return self.call_llm(prompt)