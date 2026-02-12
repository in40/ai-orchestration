import os
import asyncio
import httpx
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class LMStudioClient:
    """
    Asynchronous client for interacting with LM Studio API.
    
    This client handles communication with the LM Studio server for generating
    responses using local language models.
    """
    
    def __init__(self):
        # Read configuration from environment variables
        self.host = os.getenv('LMSTUDIO_HOST', 'localhost')
        self.port = os.getenv('LMSTUDIO_PORT', '1234')
        self.timeout = int(os.getenv('LMSTUDIO_TIMEOUT', '120'))
        
        # Construct the base URL for the LM Studio API
        self.base_url = f"http://{self.host}:{self.port}/v1"
        
        # Create HTTP client with timeout
        self.client = httpx.AsyncClient(timeout=self.timeout)
        
    async def check_health(self) -> Dict[str, Any]:
        """
        Check connectivity to LM Studio and return available models.
        
        Returns:
            Dictionary containing status and available models
        """
        try:
            response = await self.client.get(f"{self.base_url}/models")
            response.raise_for_status()
            
            data = response.json()
            models = [model['id'] for model in data.get('data', [])]
            
            return {
                "status": "ok",
                "models": models,
                "reachable": True
            }
        except Exception as e:
            logger.warning(f"LM Studio health check failed: {str(e)}")
            return {
                "status": "error",
                "models": [],
                "reachable": False,
                "error": str(e)
            }
    
    async def list_models(self) -> list:
        """
        List all available models from LM Studio.
        
        Returns:
            List of model IDs
        """
        try:
            response = await self.client.get(f"{self.base_url}/models")
            response.raise_for_status()
            
            data = response.json()
            return [model['id'] for model in data.get('data', [])]
        except Exception as e:
            logger.error(f"Failed to list models: {str(e)}")
            return []
    
    async def generate(
        self, 
        prompt: str, 
        max_tokens: int = 512, 
        temperature: float = 0.7,
        model: Optional[str] = None
    ) -> str:
        """
        Generate a response from the LM Studio API.
        
        Args:
            prompt: The input prompt for generation
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (0.0-2.0)
            model: Specific model to use (if None, uses default)
        
        Returns:
            Generated text response
        """
        # Prepare the request payload
        payload = {
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False  # We're not using streaming for simplicity
        }
        
        # Use specific model if provided
        if model:
            payload["model"] = model
        
        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            return data['choices'][0]['message']['content']
        
        except httpx.TimeoutException:
            logger.error("LM Studio API request timed out")
            raise Exception("LM Studio API request timed out")
        except httpx.RequestError as e:
            logger.error(f"LM Studio API request error: {str(e)}")
            raise Exception(f"LM Studio API request error: {str(e)}")
        except KeyError as e:
            logger.error(f"Unexpected response format from LM Studio API: {str(e)}")
            raise Exception(f"Unexpected response format from LM Studio API: {str(e)}")
        except Exception as e:
            logger.error(f"Unknown error during LM Studio API call: {str(e)}")
            raise Exception(f"Unknown error during LM Studio API call: {str(e)}")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Example usage and testing
async def main():
    client = LMStudioClient()
    
    # Test health check
    health = await client.check_health()
    print("Health check:", health)
    
    # Test model listing
    models = await client.list_models()
    print("Available models:", models)
    
    # Test generation (only if models are available)
    if models:
        try:
            response = await client.generate("Say hello in a friendly way.")
            print("Generated response:", response)
        except Exception as e:
            print(f"Generation failed: {str(e)}")
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())