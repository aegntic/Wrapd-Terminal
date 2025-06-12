#!/usr/bin/env python3
# WRAPD: Enhanced OpenRouter API Integration

import aiohttp
import asyncio
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from ..utils.error_handling import APIConnectionError, RateLimitError, ModelNotAvailableError
from ..utils.retry_logic import RetryHandler

class OpenRouterAPI:
    """Enhanced OpenRouter API client with real-time pricing and performance monitoring"""
    
    def __init__(self, config_manager):
        self.config = config_manager
        self.logger = logging.getLogger("wrapd.openrouter_api")
        
        self.base_url = "https://openrouter.ai/api/v1"
        self.retry_handler = RetryHandler(max_retries=3, backoff_factor=2)
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
        
        # Performance tracking
        self.request_times: Dict[str, List[float]] = {}
        self.error_counts: Dict[str, int] = {}
        
        # Session for connection pooling
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=aiohttp.TCPConnector(limit=10, limit_per_host=5)
            )
        return self._session
    
    async def close(self):
        """Close the aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with API key"""
        api_key = self.config.get_api_key('openrouter')
        if not api_key:
            raise APIConnectionError("OpenRouter API key not found")
        
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://wrapd.app",
            "X-Title": "WRAPD Terminal"
        }
    
    async def _rate_limit(self):
        """Enforce rate limiting"""
        now = time.time()
        time_since_last = now - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last)
        
        self.last_request_time = time.time()
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with error handling and retry logic"""
        await self._rate_limit()
        
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
        kwargs['headers'] = headers
        
        async def _request():
            session = await self._get_session()
            start_time = time.time()
            
            try:
                async with session.request(method, url, **kwargs) as response:
                    request_time = time.time() - start_time
                    
                    # Track performance
                    if endpoint not in self.request_times:
                        self.request_times[endpoint] = []
                    self.request_times[endpoint].append(request_time)
                    
                    # Keep only recent measurements
                    if len(self.request_times[endpoint]) > 50:
                        self.request_times[endpoint] = self.request_times[endpoint][-50:]
                    
                    if response.status == 429:
                        # Rate limited
                        retry_after = response.headers.get('Retry-After', '60')
                        self.logger.warning(f"Rate limited, retry after {retry_after}s")
                        raise RateLimitError(f"Rate limited, retry after {retry_after} seconds")
                    
                    if response.status >= 400:
                        error_text = await response.text()
                        self.error_counts[endpoint] = self.error_counts.get(endpoint, 0) + 1
                        raise APIConnectionError(f"HTTP {response.status}: {error_text}")
                    
                    return await response.json()
                    
            except aiohttp.ClientError as e:
                self.error_counts[endpoint] = self.error_counts.get(endpoint, 0) + 1
                raise APIConnectionError(f"Network error: {e}")
        
        return await self.retry_handler.retry_with_backoff(_request)
    
    async def get_models_with_pricing(self) -> List[Dict[str, Any]]:
        """Get all available models with real-time pricing"""
        try:
            response = await self._make_request("GET", "/models")
            models = response.get("data", [])
            
            # Enrich with additional data
            enriched_models = []
            for model in models:
                enriched_model = await self._enrich_model_data(model)
                enriched_models.append(enriched_model)
            
            self.logger.info(f"Retrieved {len(enriched_models)} OpenRouter models")
            return enriched_models
            
        except Exception as e:
            self.logger.error(f"Failed to get OpenRouter models: {e}")
            raise
    
    async def _enrich_model_data(self, model: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich model data with additional information"""
        model_id = model.get("id", "")
        
        # Add inferred capabilities
        model["supports_images"] = self._supports_images(model_id, model)
        model["supports_function_calling"] = self._supports_function_calling(model_id, model)
        model["supports_streaming"] = True  # Most models support streaming
        model["supports_json_mode"] = self._supports_json_mode(model_id, model)
        
        # Add performance estimates
        model["estimated_response_time"] = self._estimate_response_time(model_id)
        model["popularity_rank"] = self._get_popularity_rank(model_id)
        
        # Add cost efficiency score
        model["cost_efficiency"] = self._calculate_cost_efficiency(model)
        
        return model
    
    def _supports_images(self, model_id: str, model_data: Dict) -> bool:
        """Determine if model supports image inputs"""
        # Check model description and capabilities
        description = model_data.get("description", "").lower()
        model_lower = model_id.lower()
        
        # Known vision models
        vision_indicators = [
            "vision", "visual", "image", "multimodal", "mm",
            "gpt-4-vision", "gpt-4o", "claude-3", "gemini-pro-vision"
        ]
        
        return any(indicator in model_lower or indicator in description 
                  for indicator in vision_indicators)
    
    def _supports_function_calling(self, model_id: str, model_data: Dict) -> bool:
        """Determine if model supports function calling"""
        # Most recent models support function calling
        model_lower = model_id.lower()
        
        # Models known to support function calling
        function_models = [
            "gpt-3.5", "gpt-4", "claude-3", "gemini", "mistral", "llama-3"
        ]
        
        return any(model in model_lower for model in function_models)
    
    def _supports_json_mode(self, model_id: str, model_data: Dict) -> bool:
        """Determine if model supports JSON mode"""
        model_lower = model_id.lower()
        
        # Models known to support JSON mode
        json_models = ["gpt-3.5", "gpt-4", "claude-3"]
        
        return any(model in model_lower for model in json_models)
    
    def _estimate_response_time(self, model_id: str) -> float:
        """Estimate response time based on model characteristics"""
        model_lower = model_id.lower()
        
        # Rough estimates based on model size and provider
        if "gpt-3.5" in model_lower:
            return 1.5
        elif "gpt-4" in model_lower:
            if "turbo" in model_lower:
                return 2.0
            else:
                return 5.0
        elif "claude-3-haiku" in model_lower:
            return 1.0
        elif "claude-3-sonnet" in model_lower:
            return 2.5
        elif "claude-3-opus" in model_lower:
            return 8.0
        elif "gemini" in model_lower:
            return 2.0
        elif "llama" in model_lower:
            if "70b" in model_lower:
                return 6.0
            elif "13b" in model_lower:
                return 3.0
            else:
                return 2.0
        else:
            return 3.0  # Default estimate
    
    def _get_popularity_rank(self, model_id: str) -> int:
        """Get popularity rank based on known usage patterns"""
        # This would ideally come from OpenRouter's popularity metrics
        # For now, provide estimates based on well-known models
        
        popularity_map = {
            "openai/gpt-4o": 100,
            "openai/gpt-4-turbo": 95,
            "anthropic/claude-3-sonnet": 90,
            "openai/gpt-3.5-turbo": 85,
            "anthropic/claude-3-haiku": 80,
            "google/gemini-pro": 75,
            "meta-llama/llama-3-70b-instruct": 70,
            "mistralai/mistral-7b-instruct": 65,
            "anthropic/claude-3-opus": 90,
        }
        
        return popularity_map.get(model_id, 50)  # Default to middle rank
    
    def _calculate_cost_efficiency(self, model: Dict[str, Any]) -> float:
        """Calculate cost efficiency score (performance per dollar)"""
        pricing = model.get("pricing", {})
        input_price = float(pricing.get("prompt", 1.0))
        
        if input_price == 0:
            return 1.0  # Free models get max efficiency
        
        # Rough performance estimates (would be better with real benchmarks)
        model_id = model.get("id", "").lower()
        
        if "gpt-4o" in model_id:
            performance = 0.95
        elif "claude-3-sonnet" in model_id:
            performance = 0.90
        elif "gpt-3.5" in model_id:
            performance = 0.80
        elif "claude-3-haiku" in model_id:
            performance = 0.75
        elif "gemini" in model_id:
            performance = 0.85
        else:
            performance = 0.70
        
        # Efficiency = performance / cost (normalized)
        efficiency = performance / (input_price * 1000)  # Scale price for comparison
        return min(efficiency, 1.0)
    
    async def get_model_details(self, model_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific model"""
        try:
            # OpenRouter doesn't have a specific endpoint for model details
            # So we get the model from the list and add real-time status
            models = await self.get_models_with_pricing()
            
            for model in models:
                if model.get("id") == model_id:
                    # Add real-time status check
                    model["availability_status"] = await self._check_model_availability(model_id)
                    model["current_queue_time"] = await self._get_queue_time(model_id)
                    return model
            
            raise ModelNotAvailableError(f"Model {model_id} not found")
            
        except Exception as e:
            self.logger.error(f"Failed to get model details for {model_id}: {e}")
            raise
    
    async def _check_model_availability(self, model_id: str) -> str:
        """Check real-time model availability"""
        try:
            # Make a small test request to check availability
            test_data = {
                "model": model_id,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 1
            }
            
            start_time = time.time()
            await self._make_request("POST", "/chat/completions", json=test_data)
            response_time = time.time() - start_time
            
            if response_time < 2.0:
                return "online"
            elif response_time < 5.0:
                return "slow"
            else:
                return "degraded"
                
        except RateLimitError:
            return "rate_limited"
        except APIConnectionError:
            return "offline"
        except Exception:
            return "unknown"
    
    async def _get_queue_time(self, model_id: str) -> float:
        """Estimate current queue time for model"""
        # This would require specific OpenRouter metrics
        # For now, provide estimates based on model popularity
        
        popularity = self._get_popularity_rank(model_id)
        
        if popularity > 90:
            return 2.0  # High demand models
        elif popularity > 70:
            return 1.0  # Medium demand
        else:
            return 0.5  # Low demand
    
    async def test_model_performance(self, model_id: str, test_prompt: str = None) -> Dict[str, Any]:
        """Test model performance with a sample request"""
        if test_prompt is None:
            test_prompt = "Respond with just 'OK' to confirm you're working."
        
        try:
            test_data = {
                "model": model_id,
                "messages": [{"role": "user", "content": test_prompt}],
                "max_tokens": 10,
                "temperature": 0.1
            }
            
            start_time = time.time()
            response = await self._make_request("POST", "/chat/completions", json=test_data)
            end_time = time.time()
            
            response_time = end_time - start_time
            
            # Extract response content
            content = ""
            if "choices" in response and response["choices"]:
                content = response["choices"][0].get("message", {}).get("content", "")
            
            # Calculate tokens per second
            usage = response.get("usage", {})
            total_tokens = usage.get("total_tokens", 0)
            tokens_per_second = total_tokens / response_time if response_time > 0 else 0
            
            return {
                "model_id": model_id,
                "response_time": response_time,
                "tokens_per_second": tokens_per_second,
                "response_content": content,
                "usage": usage,
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "model_id": model_id,
                "error": str(e),
                "success": False,
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_usage_stats(self) -> Dict[str, Any]:
        """Get API usage statistics"""
        # OpenRouter doesn't provide this in the public API
        # Return local statistics instead
        return {
            "total_requests": sum(len(times) for times in self.request_times.values()),
            "average_response_times": {
                endpoint: sum(times) / len(times)
                for endpoint, times in self.request_times.items()
                if times
            },
            "error_counts": self.error_counts.copy(),
            "endpoints_used": list(self.request_times.keys())
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the API client"""
        return {
            "request_times": self.request_times.copy(),
            "error_counts": self.error_counts.copy(),
            "last_request_time": self.last_request_time,
            "session_active": self._session is not None and not self._session.closed
        }