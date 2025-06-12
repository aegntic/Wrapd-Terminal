#!/usr/bin/env python3
# WRAPD: LLM Interface for handling requests to language models

import os
import json
import aiohttp
import asyncio
import time
import logging
from typing import Dict, List, Optional, Union, Any

class LLMInterface:
    """Interface for communicating with language models"""
    
    def __init__(self, config_manager):
        """Initialize the LLM interface
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config = config_manager
        self.logger = logging.getLogger("wrapd.llm")
        
        # Cache for model responses
        self.cache = {}
        self.max_cache_size = self.config.get_int('llm', 'cache_size', 500)
        
        # Dialog history for conversation context
        self.dialog_history = []
        
        # Track model health status
        self.model_health = {}
        
        # Flag to track if Ollama server is available
        self.ollama_available = None
    
    async def get_response(self, prompt, model=None, temperature=None, max_tokens=None):
        """Get a response from the language model
        
        Args:
            prompt (str): User prompt
            model (str, optional): Model to use, overrides config setting
            temperature (float, optional): Temperature, overrides config setting
            max_tokens (int, optional): Maximum tokens, overrides config setting
        
        Returns:
            str: Model response
        """
        # Use defaults from config if not provided
        provider = self.config.get('llm', 'provider', 'local')
        model = model or self.config.get('llm', 'model', 'gemma3:1b')
        temperature = temperature or self.config.get_float('llm', 'temperature', 0.1)
        max_tokens = max_tokens or self.config.get_int('llm', 'max_tokens', 256)
        
        # Check cache if enabled
        cache_enabled = self.config.get_boolean('llm', 'cache_responses', True)
        cache_key = f"{prompt}|{model}|{temperature}|{max_tokens}"
        
        if cache_enabled and cache_key in self.cache:
            self.logger.debug(f"Cache hit for prompt: {prompt[:30]}...")
            return self.cache[cache_key]
        
        try:
            if provider == 'local':
                response = await self._get_local_response(prompt, model, temperature, max_tokens)
            elif provider == 'openrouter':
                response = await self._get_openrouter_response(prompt, model, temperature, max_tokens)
            else:
                self.logger.error(f"Unknown provider: {provider}")
                return f"Error: Unknown provider '{provider}'"
            
            # Update cache if enabled
            if cache_enabled:
                self._update_cache(cache_key, response)
            
            return response
        
        except Exception as e:
            self.logger.error(f"Error getting LLM response: {str(e)}")
            return f"Error: {str(e)}"
    
    async def check_model_health(self, model, provider='local'):
        """Check if a model is healthy and available
        
        Args:
            model (str): Model to check
            provider (str): Provider (local or openrouter)
        
        Returns:
            bool: True if model is healthy, False otherwise
        """
        health_key = f"{provider}:{model}"
        
        # If we've already checked recently, return cached result
        if health_key in self.model_health:
            last_check, status = self.model_health[health_key]
            # Only cache health check results for 5 minutes
            if time.time() - last_check < 300:  # 5 minutes in seconds
                return status
        
        try:
            if provider == 'local':
                # Check if Ollama server is available
                if self.ollama_available is None:
                    self.ollama_available = await self._check_ollama_server()
                
                if not self.ollama_available:
                    self.logger.warning("Ollama server is not available")
                    self.model_health[health_key] = (time.time(), False)
                    return False
                
                # Try to get model info from Ollama
                api_url = f"http://localhost:11434/api/show"
                data = {"name": model}
                
                async with aiohttp.ClientSession() as session:
                    try:
                        async with session.post(api_url, json=data, timeout=2) as response:
                            is_healthy = response.status == 200
                            self.model_health[health_key] = (time.time(), is_healthy)
                            
                            if not is_healthy:
                                self.logger.warning(f"Model {model} is not available: {response.status}")
                            
                            return is_healthy
                    except asyncio.TimeoutError:
                        self.logger.warning(f"Timeout checking model {model}")
                        self.model_health[health_key] = (time.time(), False)
                        return False
            
            elif provider == 'openrouter':
                # For OpenRouter, just check if we have an API key
                api_key = self.config.get_api_key('openrouter')
                is_healthy = bool(api_key)
                self.model_health[health_key] = (time.time(), is_healthy)
                return is_healthy
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking model health: {str(e)}")
            self.model_health[health_key] = (time.time(), False)
            return False
    
    async def _check_ollama_server(self):
        """Check if Ollama server is running
        
        Returns:
            bool: True if server is running, False otherwise
        """
        try:
            # Ping Ollama server
            api_url = "http://localhost:11434/api/version"
            
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(api_url, timeout=2) as response:
                        return response.status == 200
                except asyncio.TimeoutError:
                    self.logger.warning("Ollama server timeout")
                    return False
        except Exception as e:
            self.logger.error(f"Error checking Ollama server: {str(e)}")
            return False
    
    async def _get_local_response(self, prompt, model, temperature, max_tokens):
        """Get response from local LLM through Ollama API
        
        Args:
            prompt (str): User prompt
            model (str): Model to use
            temperature (float): Temperature
            max_tokens (int): Maximum tokens
        
        Returns:
            str: Model response
        """
        # Check model health first
        is_healthy = await self.check_model_health(model, 'local')
        if not is_healthy:
            error_msg = f"Model {model} is not available. Make sure Ollama is running and the model is installed."
            self.logger.error(error_msg)
            return error_msg
            
        api_url = "http://localhost:11434/api/chat"
        
        # Format messages for dialog history
        messages = self.dialog_history.copy()
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=data, timeout=30) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"API error {response.status}: {error_text}")
                
                    result = await response.json()
                    answer = result.get("message", {}).get("content", "")
                    
                    # Update dialog history
                    if answer:
                        self.dialog_history.append({"role": "user", "content": prompt})
                        self.dialog_history.append({"role": "assistant", "content": answer})
                        
                        # Keep history at a reasonable size
                        if len(self.dialog_history) > 10:
                            self.dialog_history = self.dialog_history[-10:]
                    
                    return answer
        except Exception as e:
            self.logger.error(f"Error getting local model response: {str(e)}")
            raise e
    
    async def _get_openrouter_response(self, prompt, model, temperature, max_tokens):
        """Get response from OpenRouter API
        
        Args:
            prompt (str): User prompt
            model (str): Model to use
            temperature (float): Temperature
            max_tokens (int): Maximum tokens
        
        Returns:
            str: Model response
        """
        # Check model health first
        is_healthy = await self.check_model_health(model, 'openrouter')
        if not is_healthy:
            error_msg = "OpenRouter API key not found. Please set up your API key in settings."
            self.logger.error(error_msg)
            return error_msg
            
        api_url = "https://openrouter.ai/api/v1/chat/completions"
        api_key = self.config.get_api_key('openrouter')
        
        if not api_key:
            raise Exception("OpenRouter API key not found. Please set up your API key in settings.")
        
        # Format messages for dialog history
        messages = self.dialog_history.copy()
        messages.append({"role": "user", "content": prompt})
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://wrapd.app",  # Replace with your app's actual domain
            "X-Title": "WRAPD Terminal"
        }
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, headers=headers, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API error {response.status}: {error_text}")
                
                result = await response.json()
                answer = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # Update dialog history
                if answer:
                    self.dialog_history.append({"role": "user", "content": prompt})
                    self.dialog_history.append({"role": "assistant", "content": answer})
                    
                    # Keep history at a reasonable size
                    if len(self.dialog_history) > 10:
                        self.dialog_history = self.dialog_history[-10:]
                
                return answer
    
    def _update_cache(self, key, value):
        """Update the response cache
        
        Args:
            key (str): Cache key
            value (str): Value to cache
        """
        self.cache[key] = value
        
        # Remove oldest entries if cache is too large
        if len(self.cache) > self.max_cache_size:
            oldest_keys = list(self.cache.keys())[:len(self.cache) - self.max_cache_size]
            for old_key in oldest_keys:
                del self.cache[old_key]
    
    def clear_history(self):
        """Clear dialog history"""
        self.dialog_history = []
    
    def clear_cache(self):
        """Clear response cache"""
        self.cache = {}
    
    async def get_available_models(self):
        """Get list of available models
        
        Returns:
            dict: Dictionary of available models by provider
        """
        models = {
            'local': await self._get_local_models(),
            'openrouter': await self._get_openrouter_models()
        }
        return models
    
    async def _get_local_models(self):
        """Get available local models from Ollama
        
        Returns:
            list: List of available models
        """
        # Check if Ollama server is available
        if self.ollama_available is None:
            self.ollama_available = await self._check_ollama_server()
            
        if not self.ollama_available:
            self.logger.warning("Ollama server is not available, returning default models")
            return [
                {"id": "gemma3:1b", "name": "Gemma 3 1B", "provider": "local"},
                {"id": "gemma3:3b", "name": "Gemma 3 3B", "provider": "local"},
                {"id": "phi3:3b", "name": "Phi-3 3B", "provider": "local"},
                {"id": "qwen2:7b", "name": "Qwen2 7B", "provider": "local"}
            ]
            
        try:
            api_url = "http://localhost:11434/api/tags"
            
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(api_url, timeout=2) as response:
                        if response.status != 200:
                            self.logger.error(f"Failed to get local models: {response.status}")
                            return []
                        
                        result = await response.json()
                        models = []
                        
                        for model in result.get("models", []):
                            models.append({
                                "id": model.get("name"),
                                "name": model.get("name"),
                                "provider": "local"
                            })
                        
                        return models
                except asyncio.TimeoutError:
                    self.logger.warning("Ollama server timeout - returning default models")
                    # Return a list of default models even if Ollama is not available
                    return [
                        {"id": "gemma3:1b", "name": "Gemma 3 1B", "provider": "local"},
                        {"id": "gemma3:3b", "name": "Gemma 3 3B", "provider": "local"},
                        {"id": "phi3:3b", "name": "Phi-3 3B", "provider": "local"},
                        {"id": "qwen2:7b", "name": "Qwen2 7B", "provider": "local"}
                    ]
        except Exception as e:
            self.logger.error(f"Error getting local models: {str(e)}")
            # Return a list of default models even if Ollama is not available
            return [
                {"id": "gemma3:1b", "name": "Gemma 3 1B", "provider": "local"},
                {"id": "gemma3:3b", "name": "Gemma 3 3B", "provider": "local"},
                {"id": "phi3:3b", "name": "Phi-3 3B", "provider": "local"},
                {"id": "qwen2:7b", "name": "Qwen2 7B", "provider": "local"}
            ]
    
    async def _get_openrouter_models(self):
        """Get available models from OpenRouter
        
        Returns:
            list: List of available models
        """
        try:
            api_key = self.config.get_api_key('openrouter')
            if not api_key:
                return []
            
            api_url = "https://openrouter.ai/api/v1/models"
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://wrapd.app",  # Replace with your app's actual domain
                "X-Title": "WRAPD Terminal"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, headers=headers) as response:
                    if response.status != 200:
                        self.logger.error(f"Failed to get OpenRouter models: {response.status}")
                        return []
                    
                    result = await response.json()
                    models = []
                    
                    for model in result.get("data", []):
                        models.append({
                            "id": model.get("id"),
                            "name": model.get("name", model.get("id")),
                            "provider": "openrouter",
                            "context_length": model.get("context_length", 4096),
                            "pricing": model.get("pricing", {})
                        })
                    
                    return models
        except Exception as e:
            self.logger.error(f"Error getting OpenRouter models: {str(e)}")
            return []
