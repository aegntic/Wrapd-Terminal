#!/usr/bin/env python3
# WRAPD: Enhanced Ollama API Integration

import aiohttp
import asyncio
import time
import logging
import json
import subprocess
import shutil
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path

from ..utils.error_handling import APIConnectionError, ModelNotAvailableError
from ..utils.retry_logic import RetryHandler

class OllamaAPI:
    """Enhanced Ollama API client with model management and performance monitoring"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.logger = logging.getLogger("wrapd.ollama_api")
        
        self.retry_handler = RetryHandler(max_retries=3, backoff_factor=1.5)
        
        # Performance tracking
        self.request_times: Dict[str, List[float]] = {}
        self.error_counts: Dict[str, int] = {}
        
        # Model installation tracking
        self.installation_progress: Dict[str, Dict[str, Any]] = {}
        
        # Session for connection pooling
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Server status
        self._server_available: Optional[bool] = None
        self._last_health_check: float = 0
        self._health_check_interval = 30  # seconds
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=60, connect=5)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=aiohttp.TCPConnector(limit=5, limit_per_host=3)
            )
        return self._session
    
    async def close(self):
        """Close the aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"
        
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
                    
                    if response.status >= 400:
                        error_text = await response.text()
                        self.error_counts[endpoint] = self.error_counts.get(endpoint, 0) + 1
                        
                        if response.status == 404:
                            raise ModelNotAvailableError(f"Model not found: {error_text}")
                        else:
                            raise APIConnectionError(f"HTTP {response.status}: {error_text}")
                    
                    if response.content_type == 'application/json':
                        return await response.json()
                    else:
                        return {"content": await response.text()}
                        
            except aiohttp.ClientError as e:
                self.error_counts[endpoint] = self.error_counts.get(endpoint, 0) + 1
                raise APIConnectionError(f"Network error: {e}")
        
        return await self.retry_handler.retry_with_backoff(_request)
    
    async def check_server_health(self, force_check: bool = False) -> bool:
        """Check if Ollama server is available"""
        now = time.time()
        
        # Use cached result if recent
        if (not force_check and 
            self._server_available is not None and 
            now - self._last_health_check < self._health_check_interval):
            return self._server_available
        
        try:
            await self._make_request("GET", "/api/version", timeout=aiohttp.ClientTimeout(total=3))
            self._server_available = True
            self.logger.debug("Ollama server is available")
        except Exception as e:
            self._server_available = False
            self.logger.warning(f"Ollama server is not available: {e}")
        
        self._last_health_check = now
        return self._server_available
    
    async def get_installed_models(self) -> List[Dict[str, Any]]:
        """Get list of installed models"""
        try:
            if not await self.check_server_health():
                return []
            
            response = await self._make_request("GET", "/api/tags")
            models = response.get("models", [])
            
            # Enrich model data
            enriched_models = []
            for model in models:
                enriched_model = await self._enrich_installed_model(model)
                enriched_models.append(enriched_model)
            
            self.logger.info(f"Retrieved {len(enriched_models)} installed Ollama models")
            return enriched_models
            
        except Exception as e:
            self.logger.error(f"Failed to get installed models: {e}")
            return []
    
    async def _enrich_installed_model(self, model: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich installed model with additional data"""
        model_name = model.get("name", "")
        
        # Get detailed model info
        try:
            details = await self.get_model_info(model_name)
            model.update(details)
        except Exception as e:
            self.logger.warning(f"Failed to get details for {model_name}: {e}")
        
        # Add performance metrics
        model["performance_metrics"] = await self._get_model_performance(model_name)
        
        # Add resource usage estimates
        model["resource_estimates"] = self._estimate_resource_usage(model)
        
        return model
    
    async def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific model"""
        try:
            response = await self._make_request("POST", "/api/show", json={"name": model_name})
            
            # Parse model info
            info = {
                "name": model_name,
                "description": self._generate_description(model_name, response),
                "parameters": response.get("details", {}).get("parameter_size", ""),
                "quantization": response.get("details", {}).get("quantization_level", ""),
                "family": response.get("details", {}).get("family", ""),
                "format": response.get("details", {}).get("format", ""),
                "size": response.get("size", 0),
                "modified_at": response.get("modified_at", ""),
                "digest": response.get("digest", ""),
                "tags": self._extract_model_tags(model_name),
            }
            
            return info
            
        except Exception as e:
            self.logger.error(f"Failed to get model info for {model_name}: {e}")
            return {"name": model_name, "error": str(e)}
    
    async def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of models available for download"""
        # Since Ollama doesn't provide a public API for browsing models,
        # we'll provide a curated list of popular models
        
        popular_models = [
            {
                "name": "llama3.2:3b",
                "description": "Meta Llama 3.2 3B - Fast and efficient for general tasks",
                "size_estimate": 3 * 1024**3,  # 3GB
                "parameters": "3B",
                "tags": ["llama", "meta", "3b", "general"],
                "category": "General Purpose",
                "recommended": True,
            },
            {
                "name": "llama3.2:1b",
                "description": "Meta Llama 3.2 1B - Ultra-lightweight for resource-constrained environments",
                "size_estimate": 1 * 1024**3,  # 1GB
                "parameters": "1B",
                "tags": ["llama", "meta", "1b", "lightweight"],
                "category": "Lightweight",
                "recommended": True,
            },
            {
                "name": "gemma2:2b",
                "description": "Google Gemma 2 2B - Efficient and capable model for various tasks",
                "size_estimate": 2 * 1024**3,  # 2GB
                "parameters": "2B",
                "tags": ["gemma", "google", "2b", "efficient"],
                "category": "General Purpose",
                "recommended": True,
            },
            {
                "name": "gemma2:9b",
                "description": "Google Gemma 2 9B - Larger model with improved capabilities",
                "size_estimate": 9 * 1024**3,  # 9GB
                "parameters": "9B",
                "tags": ["gemma", "google", "9b", "capable"],
                "category": "High Performance",
                "recommended": False,
            },
            {
                "name": "phi3:3.8b",
                "description": "Microsoft Phi-3 3.8B - Optimized for reasoning and code",
                "size_estimate": 3.8 * 1024**3,  # 3.8GB
                "parameters": "3.8B",
                "tags": ["phi", "microsoft", "3.8b", "reasoning", "code"],
                "category": "Code & Reasoning",
                "recommended": True,
            },
            {
                "name": "qwen2:7b",
                "description": "Alibaba Qwen2 7B - Multilingual model with strong performance",
                "size_estimate": 7 * 1024**3,  # 7GB
                "parameters": "7B",
                "tags": ["qwen", "alibaba", "7b", "multilingual"],
                "category": "Multilingual",
                "recommended": False,
            },
            {
                "name": "codellama:7b",
                "description": "Meta Code Llama 7B - Specialized for code generation",
                "size_estimate": 7 * 1024**3,  # 7GB
                "parameters": "7B",
                "tags": ["codellama", "meta", "7b", "code"],
                "category": "Code Generation",
                "recommended": False,
            },
            {
                "name": "mistral:7b",
                "description": "Mistral 7B - High-quality general purpose model",
                "size_estimate": 7 * 1024**3,  # 7GB
                "parameters": "7B",
                "tags": ["mistral", "7b", "general"],
                "category": "General Purpose",
                "recommended": False,
            },
            {
                "name": "llama3.1:8b",
                "description": "Meta Llama 3.1 8B - Advanced reasoning and instruction following",
                "size_estimate": 8 * 1024**3,  # 8GB
                "parameters": "8B",
                "tags": ["llama", "meta", "8b", "reasoning"],
                "category": "High Performance",
                "recommended": False,
            },
            {
                "name": "neural-chat:7b",
                "description": "Intel Neural Chat 7B - Optimized for conversational AI",
                "size_estimate": 7 * 1024**3,  # 7GB
                "parameters": "7B",
                "tags": ["neural-chat", "intel", "7b", "chat"],
                "category": "Conversational",
                "recommended": False,
            }
        ]
        
        # Check which models are already installed
        installed_models = await self.get_installed_models()
        installed_names = {model.get("name", "") for model in installed_models}
        
        # Mark models as installed
        for model in popular_models:
            model["is_installed"] = model["name"] in installed_names
            model["install_command"] = f"ollama pull {model['name']}"
        
        return popular_models
    
    async def install_model(self, model_name: str, progress_callback=None) -> bool:
        """Install a model using Ollama"""
        try:
            self.logger.info(f"Starting installation of model: {model_name}")
            
            # Initialize progress tracking
            self.installation_progress[model_name] = {
                "status": "starting",
                "progress": 0.0,
                "message": "Preparing to download...",
                "start_time": time.time()
            }
            
            # Use ollama pull command
            if await self._install_model_via_cli(model_name, progress_callback):
                self.installation_progress[model_name]["status"] = "completed"
                self.installation_progress[model_name]["progress"] = 100.0
                self.installation_progress[model_name]["message"] = "Installation completed"
                return True
            else:
                self.installation_progress[model_name]["status"] = "failed"
                self.installation_progress[model_name]["message"] = "Installation failed"
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to install model {model_name}: {e}")
            self.installation_progress[model_name]["status"] = "failed"
            self.installation_progress[model_name]["message"] = f"Error: {e}"
            return False
    
    async def _install_model_via_cli(self, model_name: str, progress_callback=None) -> bool:
        """Install model using CLI command"""
        try:
            # Check if ollama command is available
            if not shutil.which("ollama"):
                raise APIConnectionError("Ollama CLI not found in PATH")
            
            # Run ollama pull command
            process = subprocess.Popen(
                ["ollama", "pull", model_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Monitor progress
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                
                if output:
                    # Parse progress from output
                    progress_info = self._parse_install_progress(output.strip())
                    
                    if model_name in self.installation_progress:
                        self.installation_progress[model_name].update(progress_info)
                    
                    if progress_callback:
                        await progress_callback(model_name, progress_info)
                
                # Small delay to prevent excessive CPU usage
                await asyncio.sleep(0.1)
            
            # Check final result
            return_code = process.poll()
            if return_code == 0:
                self.logger.info(f"Successfully installed model: {model_name}")
                return True
            else:
                stderr_output = process.stderr.read()
                self.logger.error(f"Failed to install model {model_name}: {stderr_output}")
                return False
                
        except Exception as e:
            self.logger.error(f"CLI installation failed for {model_name}: {e}")
            return False
    
    def _parse_install_progress(self, output: str) -> Dict[str, Any]:
        """Parse installation progress from CLI output"""
        progress_info = {
            "message": output,
            "progress": 0.0,
            "status": "downloading"
        }
        
        # Look for percentage indicators
        if "%" in output:
            try:
                # Extract percentage
                import re
                match = re.search(r'(\d+(?:\.\d+)?)%', output)
                if match:
                    progress_info["progress"] = float(match.group(1))
            except ValueError:
                pass
        
        # Look for status indicators
        if "pulling" in output.lower():
            progress_info["status"] = "downloading"
        elif "verifying" in output.lower():
            progress_info["status"] = "verifying"
        elif "success" in output.lower():
            progress_info["status"] = "completed"
            progress_info["progress"] = 100.0
        elif "error" in output.lower() or "failed" in output.lower():
            progress_info["status"] = "failed"
        
        return progress_info
    
    async def uninstall_model(self, model_name: str) -> bool:
        """Uninstall a model"""
        try:
            # Use ollama rm command
            process = subprocess.run(
                ["ollama", "rm", model_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if process.returncode == 0:
                self.logger.info(f"Successfully uninstalled model: {model_name}")
                return True
            else:
                self.logger.error(f"Failed to uninstall model {model_name}: {process.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to uninstall model {model_name}: {e}")
            return False
    
    async def _get_model_performance(self, model_name: str) -> Dict[str, Any]:
        """Get performance metrics for a model"""
        # Try to get recent performance data
        if model_name in self.request_times:
            times = self.request_times[model_name]
            if times:
                return {
                    "average_response_time": sum(times) / len(times),
                    "fastest_response": min(times),
                    "slowest_response": max(times),
                    "total_requests": len(times),
                    "error_count": self.error_counts.get(model_name, 0)
                }
        
        return {
            "average_response_time": 0.0,
            "fastest_response": 0.0,
            "slowest_response": 0.0,
            "total_requests": 0,
            "error_count": 0
        }
    
    def _estimate_resource_usage(self, model: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate resource usage for a model"""
        size_bytes = model.get("size", 0)
        size_gb = size_bytes / (1024**3) if size_bytes else 0
        
        # Estimate memory usage (typically 1.2-1.5x model size)
        memory_gb = size_gb * 1.3
        
        # Estimate based on model name/size
        model_name = model.get("name", "").lower()
        
        if "1b" in model_name:
            cpu_cores = 2
            memory_gb = max(memory_gb, 4)
        elif any(size in model_name for size in ["2b", "3b"]):
            cpu_cores = 4
            memory_gb = max(memory_gb, 6)
        elif "7b" in model_name:
            cpu_cores = 6
            memory_gb = max(memory_gb, 12)
        elif any(size in model_name for size in ["8b", "9b"]):
            cpu_cores = 8
            memory_gb = max(memory_gb, 16)
        else:
            cpu_cores = 4
            memory_gb = max(memory_gb, 8)
        
        return {
            "disk_space_gb": size_gb,
            "memory_usage_gb": memory_gb,
            "recommended_cpu_cores": cpu_cores,
            "gpu_memory_gb": 0,  # Most models run on CPU by default
        }
    
    def _generate_description(self, model_name: str, model_info: Dict) -> str:
        """Generate a description for a model"""
        # Use provided description or generate based on name
        desc = model_info.get("description", "")
        if desc:
            return desc
        
        # Generate description based on model name
        name_lower = model_name.lower()
        
        if "llama" in name_lower:
            if "3.2" in name_lower:
                return "Meta's Llama 3.2 - Latest iteration with improved efficiency"
            elif "3.1" in name_lower:
                return "Meta's Llama 3.1 - Advanced reasoning and instruction following"
            else:
                return "Meta's Llama model - Open-source language model"
        elif "gemma" in name_lower:
            return "Google's Gemma model - Lightweight and efficient"
        elif "phi" in name_lower:
            return "Microsoft's Phi model - Optimized for reasoning tasks"
        elif "qwen" in name_lower:
            return "Alibaba's Qwen model - Multilingual capabilities"
        elif "mistral" in name_lower:
            return "Mistral model - High-quality general purpose"
        elif "codellama" in name_lower:
            return "Meta's Code Llama - Specialized for code generation"
        else:
            return f"Language model: {model_name}"
    
    def _extract_model_tags(self, model_name: str) -> List[str]:
        """Extract tags from model name"""
        tags = []
        name_lower = model_name.lower()
        
        # Family tags
        families = ["llama", "gemma", "phi", "qwen", "mistral", "codellama"]
        for family in families:
            if family in name_lower:
                tags.append(family)
                break
        
        # Size tags
        sizes = ["1b", "2b", "3b", "7b", "8b", "9b", "13b", "30b", "70b"]
        for size in sizes:
            if size in name_lower:
                tags.append(size)
                break
        
        # Capability tags
        if "code" in name_lower:
            tags.append("code")
        if "chat" in name_lower:
            tags.append("chat")
        if "instruct" in name_lower:
            tags.append("instruct")
        
        return tags
    
    def get_installation_progress(self, model_name: str) -> Dict[str, Any]:
        """Get installation progress for a model"""
        return self.installation_progress.get(model_name, {})
    
    def get_all_installation_progress(self) -> Dict[str, Dict[str, Any]]:
        """Get installation progress for all models"""
        return self.installation_progress.copy()
    
    async def test_model_performance(self, model_name: str, test_prompt: str = None) -> Dict[str, Any]:
        """Test model performance with a sample request"""
        if test_prompt is None:
            test_prompt = "Say 'Hello' to test the model."
        
        try:
            test_data = {
                "model": model_name,
                "prompt": test_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 10
                }
            }
            
            start_time = time.time()
            response = await self._make_request("POST", "/api/generate", json=test_data)
            end_time = time.time()
            
            response_time = end_time - start_time
            response_content = response.get("response", "")
            
            # Calculate tokens per second (estimate)
            # Ollama doesn't provide exact token counts, so we estimate
            estimated_tokens = len(response_content.split()) * 1.3  # Rough estimate
            tokens_per_second = estimated_tokens / response_time if response_time > 0 else 0
            
            return {
                "model_name": model_name,
                "response_time": response_time,
                "tokens_per_second": tokens_per_second,
                "response_content": response_content,
                "estimated_tokens": estimated_tokens,
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "model_name": model_name,
                "error": str(e),
                "success": False,
                "timestamp": datetime.now().isoformat()
            }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the API client"""
        return {
            "request_times": self.request_times.copy(),
            "error_counts": self.error_counts.copy(),
            "server_available": self._server_available,
            "last_health_check": self._last_health_check,
            "session_active": self._session is not None and not self._session.closed,
            "installation_progress": self.installation_progress.copy()
        }