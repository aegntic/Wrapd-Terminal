#!/usr/bin/env python3
# WRAPD: Model Information Data Structure

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import json

@dataclass
class ModelPricing:
    """Pricing information for a model"""
    input_price_per_1m: float = 0.0
    output_price_per_1m: float = 0.0
    currency: str = "USD"
    
    def get_estimated_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate estimated cost for given token usage"""
        input_cost = (input_tokens / 1_000_000) * self.input_price_per_1m
        output_cost = (output_tokens / 1_000_000) * self.output_price_per_1m
        return input_cost + output_cost

@dataclass
class ModelCapabilities:
    """Model capabilities and features"""
    context_length: int = 4096
    supports_images: bool = False
    supports_function_calling: bool = False
    supports_streaming: bool = True
    supports_json_mode: bool = False
    max_output_tokens: int = 4096
    
@dataclass
class ModelPerformance:
    """Performance metrics for a model"""
    response_time_avg: float = 0.0
    response_time_p95: float = 0.0
    availability_score: float = 1.0
    throughput_tokens_per_sec: float = 0.0
    reliability_score: float = 1.0
    popularity_score: int = 0
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class LocalModelInfo:
    """Information specific to local models (Ollama)"""
    size_gb: float = 0.0
    memory_usage_gb: float = 0.0
    download_url: str = ""
    is_installed: bool = False
    install_command: str = ""
    model_file_path: str = ""
    quantization: str = ""
    
@dataclass 
class ModelInfo:
    """Complete model information container"""
    # Basic identification
    id: str
    name: str
    provider: str
    description: str = ""
    
    # Capabilities and specifications
    capabilities: ModelCapabilities = field(default_factory=ModelCapabilities)
    
    # Pricing (primarily for OpenRouter)
    pricing: ModelPricing = field(default_factory=ModelPricing)
    
    # Performance metrics
    performance: ModelPerformance = field(default_factory=ModelPerformance)
    
    # Local model specific info
    local_info: Optional[LocalModelInfo] = None
    
    # Metadata
    version: str = ""
    tags: List[str] = field(default_factory=list)
    category: str = ""
    organization: str = ""
    homepage_url: str = ""
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # User-specific data
    is_favorite: bool = False
    usage_count: int = 0
    last_used: Optional[datetime] = None
    user_rating: Optional[int] = None  # 1-5 stars
    user_notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'provider': self.provider,
            'description': self.description,
            'capabilities': {
                'context_length': self.capabilities.context_length,
                'supports_images': self.capabilities.supports_images,
                'supports_function_calling': self.capabilities.supports_function_calling,
                'supports_streaming': self.capabilities.supports_streaming,
                'supports_json_mode': self.capabilities.supports_json_mode,
                'max_output_tokens': self.capabilities.max_output_tokens,
            },
            'pricing': {
                'input_price_per_1m': self.pricing.input_price_per_1m,
                'output_price_per_1m': self.pricing.output_price_per_1m,
                'currency': self.pricing.currency,
            },
            'performance': {
                'response_time_avg': self.performance.response_time_avg,
                'response_time_p95': self.performance.response_time_p95,
                'availability_score': self.performance.availability_score,
                'throughput_tokens_per_sec': self.performance.throughput_tokens_per_sec,
                'reliability_score': self.performance.reliability_score,
                'popularity_score': self.performance.popularity_score,
                'last_updated': self.performance.last_updated.isoformat(),
            },
            'local_info': {
                'size_gb': self.local_info.size_gb if self.local_info else 0.0,
                'memory_usage_gb': self.local_info.memory_usage_gb if self.local_info else 0.0,
                'download_url': self.local_info.download_url if self.local_info else "",
                'is_installed': self.local_info.is_installed if self.local_info else False,
                'install_command': self.local_info.install_command if self.local_info else "",
                'model_file_path': self.local_info.model_file_path if self.local_info else "",
                'quantization': self.local_info.quantization if self.local_info else "",
            } if self.local_info else None,
            'version': self.version,
            'tags': self.tags,
            'category': self.category,
            'organization': self.organization,
            'homepage_url': self.homepage_url,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_favorite': self.is_favorite,
            'usage_count': self.usage_count,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'user_rating': self.user_rating,
            'user_notes': self.user_notes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelInfo':
        """Create ModelInfo from dictionary"""
        # Parse capabilities
        cap_data = data.get('capabilities', {})
        capabilities = ModelCapabilities(
            context_length=cap_data.get('context_length', 4096),
            supports_images=cap_data.get('supports_images', False),
            supports_function_calling=cap_data.get('supports_function_calling', False),
            supports_streaming=cap_data.get('supports_streaming', True),
            supports_json_mode=cap_data.get('supports_json_mode', False),
            max_output_tokens=cap_data.get('max_output_tokens', 4096),
        )
        
        # Parse pricing
        price_data = data.get('pricing', {})
        pricing = ModelPricing(
            input_price_per_1m=price_data.get('input_price_per_1m', 0.0),
            output_price_per_1m=price_data.get('output_price_per_1m', 0.0),
            currency=price_data.get('currency', 'USD'),
        )
        
        # Parse performance
        perf_data = data.get('performance', {})
        performance = ModelPerformance(
            response_time_avg=perf_data.get('response_time_avg', 0.0),
            response_time_p95=perf_data.get('response_time_p95', 0.0),
            availability_score=perf_data.get('availability_score', 1.0),
            throughput_tokens_per_sec=perf_data.get('throughput_tokens_per_sec', 0.0),
            reliability_score=perf_data.get('reliability_score', 1.0),
            popularity_score=perf_data.get('popularity_score', 0),
            last_updated=datetime.fromisoformat(perf_data.get('last_updated', datetime.now().isoformat())),
        )
        
        # Parse local info
        local_data = data.get('local_info')
        local_info = None
        if local_data:
            local_info = LocalModelInfo(
                size_gb=local_data.get('size_gb', 0.0),
                memory_usage_gb=local_data.get('memory_usage_gb', 0.0),
                download_url=local_data.get('download_url', ''),
                is_installed=local_data.get('is_installed', False),
                install_command=local_data.get('install_command', ''),
                model_file_path=local_data.get('model_file_path', ''),
                quantization=local_data.get('quantization', ''),
            )
        
        return cls(
            id=data['id'],
            name=data['name'],
            provider=data['provider'],
            description=data.get('description', ''),
            capabilities=capabilities,
            pricing=pricing,
            performance=performance,
            local_info=local_info,
            version=data.get('version', ''),
            tags=data.get('tags', []),
            category=data.get('category', ''),
            organization=data.get('organization', ''),
            homepage_url=data.get('homepage_url', ''),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get('updated_at', datetime.now().isoformat())),
            is_favorite=data.get('is_favorite', False),
            usage_count=data.get('usage_count', 0),
            last_used=datetime.fromisoformat(data['last_used']) if data.get('last_used') else None,
            user_rating=data.get('user_rating'),
            user_notes=data.get('user_notes', ''),
        )
    
    def get_display_name(self) -> str:
        """Get formatted display name"""
        if self.organization:
            return f"{self.organization}/{self.name}"
        return self.name
    
    def get_cost_per_1k_tokens(self) -> str:
        """Get formatted cost per 1K tokens"""
        if self.pricing.input_price_per_1m == 0:
            return "Free"
        
        cost_1k = self.pricing.input_price_per_1m / 1000
        if cost_1k < 0.001:
            return f"${cost_1k:.6f}"
        elif cost_1k < 0.01:
            return f"${cost_1k:.4f}"
        else:
            return f"${cost_1k:.3f}"
    
    def get_performance_rating(self) -> str:
        """Get human-readable performance rating"""
        avg_score = (self.performance.availability_score + 
                    self.performance.reliability_score) / 2
        
        if avg_score >= 0.95:
            return "Excellent"
        elif avg_score >= 0.85:
            return "Good"
        elif avg_score >= 0.70:
            return "Fair"
        else:
            return "Poor"
    
    def is_compatible_with_task(self, required_context: int = 0, 
                               needs_images: bool = False,
                               needs_functions: bool = False) -> bool:
        """Check if model is compatible with task requirements"""
        if required_context > self.capabilities.context_length:
            return False
        if needs_images and not self.capabilities.supports_images:
            return False
        if needs_functions and not self.capabilities.supports_function_calling:
            return False
        return True
    
    def get_similarity_score(self, other: 'ModelInfo') -> float:
        """Calculate similarity score with another model (0-1)"""
        score = 0.0
        
        # Provider similarity
        if self.provider == other.provider:
            score += 0.2
        
        # Context length similarity
        context_ratio = min(self.capabilities.context_length, other.capabilities.context_length) / \
                       max(self.capabilities.context_length, other.capabilities.context_length)
        score += context_ratio * 0.3
        
        # Capability similarity
        cap_matches = 0
        cap_total = 4
        if self.capabilities.supports_images == other.capabilities.supports_images:
            cap_matches += 1
        if self.capabilities.supports_function_calling == other.capabilities.supports_function_calling:
            cap_matches += 1
        if self.capabilities.supports_streaming == other.capabilities.supports_streaming:
            cap_matches += 1
        if self.capabilities.supports_json_mode == other.capabilities.supports_json_mode:
            cap_matches += 1
        score += (cap_matches / cap_total) * 0.3
        
        # Price similarity (if both have pricing)
        if (self.pricing.input_price_per_1m > 0 and other.pricing.input_price_per_1m > 0):
            price_ratio = min(self.pricing.input_price_per_1m, other.pricing.input_price_per_1m) / \
                         max(self.pricing.input_price_per_1m, other.pricing.input_price_per_1m)
            score += price_ratio * 0.2
        else:
            score += 0.1
        
        return min(score, 1.0)