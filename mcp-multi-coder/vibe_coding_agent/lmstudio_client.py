"""
LM Studio Client Layer
Hardened client with retry, circuit breaker, and structured output support
"""
import os
import asyncio
import logging
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
from pathlib import Path
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from openai import AsyncOpenAI
import json
import re

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class LMResponse:
    """Data class for LM Studio responses"""
    content: str
    model: str
    usage: Dict[str, int]
    reasoning: Optional[str] = None
    raw_response: Optional[Dict] = None

class CircuitBreaker:
    """Simple circuit breaker implementation"""
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def can_execute(self) -> bool:
        import time
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if (time.time() - self.last_failure_time) >= self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"
    
    def record_failure(self):
        import time
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
    
    def get_state(self) -> str:
        return self.state

class LMStudioClient:
    """Hardened LM Studio client with retry, circuit breaker, and structured output support"""
    
    def __init__(self):
        self.base_url = os.getenv("LM_STUDIO_URL", "http://asus-tus:1234/v1")
        self.model = os.getenv("LM_STUDIO_MODEL", "qwen3-4b")
        self.timeout = float(os.getenv("LM_STUDIO_TIMEOUT", "60"))
        self.max_retries = int(os.getenv("LM_STUDIO_MAX_RETRIES", "3"))
        
        # Initialize HTTP client with connection pooling
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout=self.timeout),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
        
        # Initialize OpenAI client for compatibility
        self.openai_client = AsyncOpenAI(
            base_url=self.base_url,
            api_key="not-needed-for-lm-studio"  # LM Studio doesn't require API key
        )
        
        # Initialize circuit breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "5")),
            recovery_timeout=int(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "60"))
        )
        
        # Model capabilities cache
        self._model_capabilities = None
        self._models_cache = None
        
        # Setup retry decorator
        self._retry_decorator = retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=4, max=10),
            retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True
        )
    
    async def initialize(self):
        """Initialize the client by fetching model information"""
        try:
            models = await self._fetch_available_models()
            if not models:
                logger.warning("Could not fetch available models from LM Studio")
                return
            
            # Check if preferred model is available
            available_models = [model.id for model in models]
            if self.model not in available_models:
                logger.warning(f"Preferred model {self.model} not available. Available: {available_models}")
                
                # Fallback to any available model
                if available_models:
                    self.model = available_models[0]
                    logger.info(f"Falling back to model: {self.model}")
            
            logger.info(f"LM Studio client initialized with model: {self.model}")
            
        except Exception as e:
            logger.error(f"Failed to initialize LM Studio client: {str(e)}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    async def _fetch_available_models(self):
        """Fetch available models from LM Studio"""
        if self._models_cache is not None:
            return self._models_cache
            
        try:
            response = await self.http_client.get(f"{self.base_url}/models")
            response.raise_for_status()
            data = response.json()
            
            # Cache the models
            self._models_cache = data.get("data", [])
            return self._models_cache
        except Exception as e:
            logger.error(f"Failed to fetch models: {str(e)}")
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on LM Studio connection"""
        try:
            if not self.circuit_breaker.can_execute():
                return {
                    "connected": False,
                    "model_loaded": False,
                    "model_name": self.model,
                    "error": f"Circuit breaker is OPEN (state: {self.circuit_breaker.get_state()})"
                }
            
            # Test with a simple completion
            test_response = await self.chat_completion(
                prompt="Say 'health check' in one word",
                max_tokens=5
            )
            
            return {
                "connected": True,
                "model_loaded": True,
                "model_name": self.model,
                "response_time": getattr(test_response, 'response_time', 'unknown'),
                "circuit_breaker_state": self.circuit_breaker.get_state()
            }
        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.error(f"Health check failed: {str(e)}")
            return {
                "connected": False,
                "model_loaded": False,
                "model_name": self.model,
                "error": str(e)
            }
    
    async def validate_json_schema(self, schema: Dict[str, Any]) -> bool:
        """Validate JSON schema depth and property count"""
        def check_depth(obj, current_depth=0):
            if current_depth > 10:  # Max depth of 10
                return False
            if isinstance(obj, dict):
                if len(obj.get('properties', {})) > 100:  # Max 100 properties
                    return False
                for key, value in obj.items():
                    if key == 'properties' and isinstance(value, dict):
                        if not all(check_depth(v, current_depth + 1) for v in value.values()):
                            return False
                    elif isinstance(value, (dict, list)):
                        if not check_depth(value, current_depth + 1):
                            return False
            elif isinstance(obj, list):
                if not all(check_depth(item, current_depth + 1) for item in obj):
                    return False
            return True
        
        return check_depth(schema)
    
    async def chat_completion(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None, 
        response_format: Optional[Dict] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7
    ) -> LMResponse:
        """Perform chat completion with retry and circuit breaker"""
        if not self.circuit_breaker.can_execute():
            raise Exception(f"Circuit breaker is OPEN: {self.circuit_breaker.get_state()}")
        
        try:
            # Validate prompt length
            if len(prompt) > 100000:  # 100k character limit
                logger.warning("Prompt exceeds 100k character limit, truncating")
                prompt = prompt[:100000]
            
            # Prepare messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Prepare request parameters
            params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            }
            
            if max_tokens:
                params["max_tokens"] = max_tokens
            
            # Add response format if provided and valid
            if response_format:
                if await self.validate_json_schema(response_format):
                    params["response_format"] = response_format
                else:
                    logger.warning("Invalid JSON schema, ignoring response_format")
            
            # Make the API call
            response = await self.openai_client.chat.completions.create(**params)
            
            # Extract content and usage
            content = response.choices[0].message.content
            usage = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0
            }
            
            # Check if model supports reasoning (look for reasoning indicators in model name)
            reasoning = None
            if any(reason in self.model.lower() for reason in ['reasoning', 'r1', 'deepseek']):
                # Extract reasoning if present in response
                reasoning_match = re.search(r'<reasoning>(.*?)</reasoning>', content, re.DOTALL)
                if reasoning_match:
                    reasoning = reasoning_match.group(1)
                    # Remove reasoning tags from main content
                    content = re.sub(r'<reasoning>.*?</reasoning>', '', content, flags=re.DOTALL).strip()
            
            self.circuit_breaker.record_success()
            
            return LMResponse(
                content=content,
                model=response.model,
                usage=usage,
                reasoning=reasoning,
                raw_response=response.model_dump() if hasattr(response, 'model_dump') else response.dict()
            )
            
        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.error(f"Chat completion failed: {str(e)}")
            raise
    
    async def extract_reasoning_blocks(self, text: str) -> list:
        """Extract reasoning blocks from text if model supports reasoning"""
        reasoning_blocks = re.findall(r'<reasoning>(.*?)</reasoning>', text, re.DOTALL)
        return reasoning_blocks
    
    async def close(self):
        """Close the HTTP client"""
        await self.http_client.aclose()
    
    def __del__(self):
        """Cleanup on deletion"""
        try:
            # Try to close the client if it's still open
            if hasattr(self, 'http_client') and not self.http_client.is_closed:
                # This is a workaround since we can't properly await in __del__
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.close())
                except RuntimeError:
                    # No event loop running, use asyncio.run if safe
                    pass
        except:
            pass

# Global client instance
_lm_client = None

async def get_lm_client() -> LMStudioClient:
    """Get or create the global LM Studio client instance"""
    global _lm_client
    if _lm_client is None:
        _lm_client = LMStudioClient()
        await _lm_client.initialize()
    return _lm_client