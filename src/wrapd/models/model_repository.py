#!/usr/bin/env python3
# WRAPD: Central Model Repository with Enhanced Caching

import os
import json
import asyncio
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from pathlib import Path

from .model_info import ModelInfo, ModelCapabilities, ModelPricing, ModelPerformance, LocalModelInfo
from .model_filter import ModelFilter, ModelSearchEngine
from ..utils.error_handling import ModelSelectionError, APIConnectionError, ModelNotAvailableError

class ModelCache:
    """Intelligent caching system with TTL and persistence"""
    
    def __init__(self, cache_dir: str):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Memory cache for fast access
        self.memory_cache: Dict[str, List[ModelInfo]] = {}
        self.cache_timestamps: Dict[str, datetime] = {}
        
        # TTL settings (in minutes)
        self.ttl_models = 60  # Model list cache for 1 hour
        self.ttl_pricing = 5  # Pricing cache for 5 minutes
        self.ttl_performance = 15  # Performance metrics cache for 15 minutes
        
        self.logger = logging.getLogger("wrapd.model_cache")
    
    async def get_cached_models(self, provider: str) -> Optional[List[ModelInfo]]:
        """Get cached models for provider"""
        # Check memory cache first
        if provider in self.memory_cache:
            timestamp = self.cache_timestamps.get(provider)
            if timestamp and self._is_cache_valid(timestamp, self.ttl_models):
                self.logger.debug(f"Memory cache hit for {provider}")
                return self.memory_cache[provider]
        
        # Check disk cache
        cache_file = self.cache_dir / f"{provider}_models.json"
        if cache_file.exists():
            try:
                stat = cache_file.stat()
                file_time = datetime.fromtimestamp(stat.st_mtime)
                
                if self._is_cache_valid(file_time, self.ttl_models):
                    with open(cache_file, 'r') as f:
                        data = json.load(f)
                    
                    models = [ModelInfo.from_dict(model_data) for model_data in data]
                    
                    # Update memory cache
                    self.memory_cache[provider] = models
                    self.cache_timestamps[provider] = file_time
                    
                    self.logger.debug(f"Disk cache hit for {provider}")
                    return models
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                self.logger.warning(f"Failed to load cache for {provider}: {e}")
                # Remove invalid cache file
                cache_file.unlink(missing_ok=True)
        
        return None
    
    async def cache_models(self, provider: str, models: List[ModelInfo]):
        """Cache models for provider"""
        # Update memory cache
        self.memory_cache[provider] = models
        self.cache_timestamps[provider] = datetime.now()
        
        # Update disk cache
        cache_file = self.cache_dir / f"{provider}_models.json"
        try:
            data = [model.to_dict() for model in models]
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.debug(f"Cached {len(models)} models for {provider}")
        except Exception as e:
            self.logger.error(f"Failed to cache models for {provider}: {e}")
    
    def invalidate_cache(self, provider: str = None):
        """Invalidate cache for provider or all providers"""
        if provider:
            # Clear specific provider
            self.memory_cache.pop(provider, None)
            self.cache_timestamps.pop(provider, None)
            
            cache_file = self.cache_dir / f"{provider}_models.json"
            cache_file.unlink(missing_ok=True)
        else:
            # Clear all caches
            self.memory_cache.clear()
            self.cache_timestamps.clear()
            
            for cache_file in self.cache_dir.glob("*_models.json"):
                cache_file.unlink(missing_ok=True)
    
    def _is_cache_valid(self, timestamp: datetime, ttl_minutes: int) -> bool:
        """Check if cache is still valid based on TTL"""
        return datetime.now() - timestamp < timedelta(minutes=ttl_minutes)
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache statistics"""
        cache_info = {
            'memory_cache_size': len(self.memory_cache),
            'providers_cached': list(self.memory_cache.keys()),
            'cache_timestamps': {
                provider: timestamp.isoformat() 
                for provider, timestamp in self.cache_timestamps.items()
            }
        }
        
        # Add disk cache info
        disk_files = list(self.cache_dir.glob("*_models.json"))
        cache_info['disk_cache_files'] = len(disk_files)
        cache_info['total_cache_size_mb'] = sum(
            f.stat().st_size for f in disk_files
        ) / (1024 * 1024)
        
        return cache_info

class ModelRepository:
    """Central repository for managing model data from multiple providers"""
    
    def __init__(self, config_manager, cache_dir: str = None):
        self.config = config_manager
        self.logger = logging.getLogger("wrapd.model_repository")
        
        # Initialize cache
        if cache_dir is None:
            cache_dir = os.path.expanduser("~/.wrapd/cache")
        self.cache = ModelCache(cache_dir)
        
        # Initialize search engine
        self.search_engine = ModelSearchEngine()
        
        # Import API classes (will be implemented separately)
        from ..api.openrouter_api import OpenRouterAPI
        from ..api.ollama_api import OllamaAPI
        
        self.openrouter_api = OpenRouterAPI(config_manager)
        self.ollama_api = OllamaAPI()
        
        # Model data
        self.models: Dict[str, List[ModelInfo]] = {}
        self.last_update: Dict[str, datetime] = {}
        
        # Performance tracking
        self.response_times: Dict[str, List[float]] = {}
        self.error_counts: Dict[str, int] = {}
    
    async def get_all_models(self, force_refresh: bool = False) -> Dict[str, List[ModelInfo]]:
        """Get all models from all providers"""
        providers = ['openrouter', 'ollama']
        all_models = {}
        
        for provider in providers:
            try:
                models = await self.get_models_by_provider(provider, force_refresh)
                all_models[provider] = models
            except Exception as e:
                self.logger.error(f"Failed to get models from {provider}: {e}")
                # Try to get cached models as fallback
                cached_models = await self.cache.get_cached_models(provider)
                if cached_models:
                    all_models[provider] = cached_models
                else:
                    all_models[provider] = []
        
        return all_models
    
    async def get_models_by_provider(self, provider: str, force_refresh: bool = False) -> List[ModelInfo]:
        """Get models from specific provider"""
        # Check cache first unless force refresh
        if not force_refresh:
            cached_models = await self.cache.get_cached_models(provider)
            if cached_models:
                return cached_models
        
        # Fetch fresh data
        try:
            if provider == 'openrouter':
                models = await self._fetch_openrouter_models()
            elif provider == 'ollama':
                models = await self._fetch_ollama_models()
            else:
                raise ModelSelectionError(f"Unknown provider: {provider}")
            
            # Cache the results
            await self.cache.cache_models(provider, models)
            
            # Update local storage
            self.models[provider] = models
            self.last_update[provider] = datetime.now()
            
            return models
            
        except Exception as e:
            self.logger.error(f"Failed to fetch models from {provider}: {e}")
            
            # Try to return cached data as fallback
            cached_models = await self.cache.get_cached_models(provider)
            if cached_models:
                self.logger.info(f"Returning cached models for {provider}")
                return cached_models
            
            # Return empty list if no cache available
            return []
    
    async def _fetch_openrouter_models(self) -> List[ModelInfo]:
        """Fetch models from OpenRouter API"""
        try:
            raw_models = await self.openrouter_api.get_models_with_pricing()
            models = []
            
            for raw_model in raw_models:
                # Parse OpenRouter model data
                model_info = ModelInfo(
                    id=raw_model.get('id', ''),
                    name=raw_model.get('name', raw_model.get('id', '')),
                    provider='openrouter',
                    description=raw_model.get('description', ''),
                    version=raw_model.get('version', ''),
                    organization=self._extract_organization(raw_model.get('id', '')),
                    category=self._categorize_model(raw_model),
                    tags=self._extract_tags(raw_model),
                )
                
                # Set capabilities
                model_info.capabilities = ModelCapabilities(
                    context_length=raw_model.get('context_length', 4096),
                    supports_images=raw_model.get('supports_images', False),
                    supports_function_calling=raw_model.get('supports_function_calling', False),
                    supports_streaming=raw_model.get('supports_streaming', True),
                    supports_json_mode=raw_model.get('supports_json_mode', False),
                    max_output_tokens=raw_model.get('max_output_tokens', 4096),
                )
                
                # Set pricing
                pricing_data = raw_model.get('pricing', {})
                model_info.pricing = ModelPricing(
                    input_price_per_1m=float(pricing_data.get('prompt', 0)),
                    output_price_per_1m=float(pricing_data.get('completion', 0)),
                    currency='USD',
                )
                
                # Set performance metrics
                model_info.performance = ModelPerformance(
                    availability_score=1.0,  # Assume available unless proven otherwise
                    popularity_score=raw_model.get('rank', 0),
                    last_updated=datetime.now(),
                )
                
                models.append(model_info)
            
            return models
            
        except Exception as e:
            self.logger.error(f"Failed to fetch OpenRouter models: {e}")
            raise APIConnectionError(f"OpenRouter API error: {e}")
    
    async def _fetch_ollama_models(self) -> List[ModelInfo]:
        """Fetch models from Ollama API"""
        try:
            # Get installed models
            installed_models = await self.ollama_api.get_installed_models()
            
            # Get available models for download
            available_models = await self.ollama_api.get_available_models()
            
            models = []
            
            # Process installed models
            for raw_model in installed_models:
                model_info = self._create_ollama_model_info(raw_model, True)
                models.append(model_info)
            
            # Process available models (not installed)
            for raw_model in available_models:
                # Skip if already installed
                if any(m.id == raw_model.get('name', '') for m in models):
                    continue
                
                model_info = self._create_ollama_model_info(raw_model, False)
                models.append(model_info)
            
            return models
            
        except Exception as e:
            self.logger.error(f"Failed to fetch Ollama models: {e}")
            # Return default models if Ollama is not available
            return self._get_default_ollama_models()
    
    def _create_ollama_model_info(self, raw_model: Dict, is_installed: bool) -> ModelInfo:
        """Create ModelInfo from Ollama model data"""
        model_id = raw_model.get('name', '')
        
        model_info = ModelInfo(
            id=model_id,
            name=raw_model.get('name', model_id),
            provider='ollama',
            description=raw_model.get('description', ''),
            version=raw_model.get('version', ''),
            organization=self._extract_organization(model_id),
            category=self._categorize_model(raw_model),
            tags=raw_model.get('tags', []),
        )
        
        # Set local model info
        size_gb = raw_model.get('size', 0) / (1024**3) if raw_model.get('size') else 0
        model_info.local_info = LocalModelInfo(
            size_gb=size_gb,
            memory_usage_gb=size_gb * 1.2,  # Estimate memory usage
            is_installed=is_installed,
            install_command=f"ollama pull {model_id}",
            quantization=self._extract_quantization(model_id),
        )
        
        # Set capabilities (estimate based on model name)
        context_length = self._estimate_context_length(model_id)
        model_info.capabilities = ModelCapabilities(
            context_length=context_length,
            supports_streaming=True,
            max_output_tokens=min(context_length // 2, 4096),
        )
        
        # Set performance (estimate)
        model_info.performance = ModelPerformance(
            availability_score=1.0 if is_installed else 0.5,
            last_updated=datetime.now(),
        )
        
        return model_info
    
    def _get_default_ollama_models(self) -> List[ModelInfo]:
        """Get default Ollama models when API is not available"""
        default_models = [
            {
                'name': 'llama3.2:3b',
                'description': 'Meta Llama 3.2 3B parameter model',
                'size': 3 * 1024**3,  # 3GB
                'tags': ['llama', 'meta', '3b'],
            },
            {
                'name': 'gemma2:2b',
                'description': 'Google Gemma 2 2B parameter model',
                'size': 2 * 1024**3,  # 2GB
                'tags': ['gemma', 'google', '2b'],
            },
            {
                'name': 'phi3:3.8b',
                'description': 'Microsoft Phi-3 3.8B parameter model',
                'size': 3.8 * 1024**3,  # 3.8GB
                'tags': ['phi', 'microsoft', '3.8b'],
            },
            {
                'name': 'qwen2:7b',
                'description': 'Alibaba Qwen2 7B parameter model',
                'size': 7 * 1024**3,  # 7GB
                'tags': ['qwen', 'alibaba', '7b'],
            },
        ]
        
        models = []
        for raw_model in default_models:
            model_info = self._create_ollama_model_info(raw_model, False)
            models.append(model_info)
        
        return models
    
    async def get_model_by_id(self, model_id: str, provider: str = None) -> Optional[ModelInfo]:
        """Get specific model by ID"""
        if provider:
            models = await self.get_models_by_provider(provider)
            for model in models:
                if model.id == model_id:
                    return model
        else:
            # Search all providers
            all_models = await self.get_all_models()
            for provider_models in all_models.values():
                for model in provider_models:
                    if model.id == model_id:
                        return model
        
        return None
    
    async def search_models(self, query: str = "", filter_obj: ModelFilter = None) -> List[ModelInfo]:
        """Search models with advanced filtering"""
        if filter_obj is None:
            filter_obj = ModelFilter()
        
        # Set search query
        if query:
            filter_obj.search_query = query
        
        # Get all models
        all_models_dict = await self.get_all_models()
        all_models = []
        for provider_models in all_models_dict.values():
            all_models.extend(provider_models)
        
        # Apply search and filtering
        return self.search_engine.search(all_models, filter_obj)
    
    async def get_recommendations(self, user_context: Dict[str, Any] = None) -> List[Tuple[ModelInfo, float]]:
        """Get model recommendations based on user context"""
        # This will be implemented in the recommendation engine
        all_models_dict = await self.get_all_models()
        all_models = []
        for provider_models in all_models_dict.values():
            all_models.extend(provider_models)
        
        # Simple recommendation for now (will be enhanced)
        recommendations = []
        for model in all_models[:10]:  # Top 10 models
            score = 0.5  # Base score
            
            # Boost score for favorites
            if model.is_favorite:
                score += 0.3
            
            # Boost score for frequently used models
            if model.usage_count > 0:
                score += min(model.usage_count * 0.1, 0.3)
            
            # Boost score for high-rated models
            if model.user_rating:
                score += (model.user_rating - 3) * 0.1  # Scale from 1-5 to -0.2 to 0.2
            
            recommendations.append((model, min(score, 1.0)))
        
        # Sort by score descending
        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations
    
    def _extract_organization(self, model_id: str) -> str:
        """Extract organization from model ID"""
        if '/' in model_id:
            return model_id.split('/')[0]
        return ''
    
    def _categorize_model(self, raw_model: Dict) -> str:
        """Categorize model based on its properties"""
        model_id = raw_model.get('id', '').lower()
        name = raw_model.get('name', '').lower()
        
        if 'gpt' in model_id or 'gpt' in name:
            return 'GPT Family'
        elif 'claude' in model_id or 'claude' in name:
            return 'Claude Family'
        elif 'llama' in model_id or 'llama' in name:
            return 'Llama Family'
        elif 'gemma' in model_id or 'gemma' in name:
            return 'Gemma Family'
        elif 'phi' in model_id or 'phi' in name:
            return 'Phi Family'
        elif 'qwen' in model_id or 'qwen' in name:
            return 'Qwen Family'
        else:
            return 'Other'
    
    def _extract_tags(self, raw_model: Dict) -> List[str]:
        """Extract tags from model data"""
        tags = []
        model_id = raw_model.get('id', '').lower()
        
        # Add size-based tags
        if 'instruct' in model_id:
            tags.append('instruct')
        if 'chat' in model_id:
            tags.append('chat')
        if 'code' in model_id:
            tags.append('code')
        if 'vision' in model_id:
            tags.append('vision')
        
        # Add parameter size tags
        for size in ['1b', '2b', '3b', '7b', '8b', '13b', '30b', '70b']:
            if size in model_id:
                tags.append(size)
                break
        
        return tags
    
    def _extract_quantization(self, model_id: str) -> str:
        """Extract quantization from model ID"""
        if 'q4' in model_id.lower():
            return 'Q4'
        elif 'q8' in model_id.lower():
            return 'Q8'
        elif 'fp16' in model_id.lower():
            return 'FP16'
        else:
            return 'Default'
    
    def _estimate_context_length(self, model_id: str) -> int:
        """Estimate context length based on model ID"""
        model_lower = model_id.lower()
        
        # Common context lengths for known models
        if 'llama' in model_lower:
            if '3.2' in model_lower:
                return 131072  # 128k
            else:
                return 4096
        elif 'gemma' in model_lower:
            return 8192
        elif 'phi' in model_lower:
            return 4096
        elif 'qwen' in model_lower:
            return 32768
        else:
            return 4096  # Default
    
    async def track_model_usage(self, model_id: str, provider: str):
        """Track model usage for recommendations"""
        model = await self.get_model_by_id(model_id, provider)
        if model:
            model.usage_count += 1
            model.last_used = datetime.now()
            
            # Update cache
            if provider in self.models:
                for i, cached_model in enumerate(self.models[provider]):
                    if cached_model.id == model_id:
                        self.models[provider][i] = model
                        break
    
    async def update_model_performance(self, model_id: str, response_time: float, success: bool):
        """Update model performance metrics"""
        # Track response times
        if model_id not in self.response_times:
            self.response_times[model_id] = []
        
        self.response_times[model_id].append(response_time)
        
        # Keep only recent measurements (last 100)
        if len(self.response_times[model_id]) > 100:
            self.response_times[model_id] = self.response_times[model_id][-100:]
        
        # Track errors
        if not success:
            self.error_counts[model_id] = self.error_counts.get(model_id, 0) + 1
        
        # Update model performance metrics
        for provider_models in self.models.values():
            for model in provider_models:
                if model.id == model_id:
                    # Update average response time
                    model.performance.response_time_avg = sum(self.response_times[model_id]) / len(self.response_times[model_id])
                    
                    # Update reliability score
                    total_requests = len(self.response_times[model_id])
                    error_count = self.error_counts.get(model_id, 0)
                    model.performance.reliability_score = max(0.0, 1.0 - (error_count / total_requests))
                    
                    model.performance.last_updated = datetime.now()
                    break
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache information"""
        return self.cache.get_cache_info()
    
    def clear_cache(self, provider: str = None):
        """Clear cache for provider or all providers"""
        self.cache.invalidate_cache(provider)