#!/usr/bin/env python3
# WRAPD: Advanced Model Filtering and Search

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable
from enum import Enum
import re
from .model_info import ModelInfo

class SortOrder(Enum):
    """Sort order options"""
    ASCENDING = "asc"
    DESCENDING = "desc"

class SortField(Enum):
    """Available sort fields"""
    NAME = "name"
    PROVIDER = "provider"
    PRICE_INPUT = "price_input"
    PRICE_OUTPUT = "price_output"
    CONTEXT_LENGTH = "context_length"
    RESPONSE_TIME = "response_time"
    POPULARITY = "popularity"
    LAST_USED = "last_used"
    RATING = "rating"
    CREATED_AT = "created_at"

@dataclass
class ModelFilter:
    """Advanced filtering options for model search"""
    
    # Text search
    search_query: str = ""
    search_fields: List[str] = field(default_factory=lambda: ["name", "description", "tags"])
    
    # Provider filtering
    providers: List[str] = field(default_factory=list)
    exclude_providers: List[str] = field(default_factory=list)
    
    # Pricing filters
    max_input_price: Optional[float] = None
    max_output_price: Optional[float] = None
    min_input_price: Optional[float] = None
    min_output_price: Optional[float] = None
    free_only: bool = False
    
    # Capability filters
    min_context_length: Optional[int] = None
    max_context_length: Optional[int] = None
    supports_images: Optional[bool] = None
    supports_function_calling: Optional[bool] = None
    supports_streaming: Optional[bool] = None
    supports_json_mode: Optional[bool] = None
    
    # Performance filters
    min_availability: Optional[float] = None
    min_reliability: Optional[float] = None
    max_response_time: Optional[float] = None
    
    # User-specific filters
    favorites_only: bool = False
    used_only: bool = False
    min_rating: Optional[int] = None
    
    # Local model filters
    installed_only: bool = False
    max_size_gb: Optional[float] = None
    
    # Availability filters
    available_only: bool = True
    
    # Tag filters
    include_tags: List[str] = field(default_factory=list)
    exclude_tags: List[str] = field(default_factory=list)
    
    # Category filters
    categories: List[str] = field(default_factory=list)
    organizations: List[str] = field(default_factory=list)
    
    # Sorting
    sort_field: SortField = SortField.NAME
    sort_order: SortOrder = SortOrder.ASCENDING
    
    def matches(self, model: ModelInfo) -> bool:
        """Check if a model matches all filter criteria"""
        
        # Text search
        if self.search_query and not self._matches_search(model):
            return False
        
        # Provider filters
        if self.providers and model.provider not in self.providers:
            return False
        if self.exclude_providers and model.provider in self.exclude_providers:
            return False
        
        # Pricing filters
        if self.free_only and model.pricing.input_price_per_1m > 0:
            return False
        if self.max_input_price is not None and model.pricing.input_price_per_1m > self.max_input_price:
            return False
        if self.min_input_price is not None and model.pricing.input_price_per_1m < self.min_input_price:
            return False
        if self.max_output_price is not None and model.pricing.output_price_per_1m > self.max_output_price:
            return False
        if self.min_output_price is not None and model.pricing.output_price_per_1m < self.min_output_price:
            return False
        
        # Capability filters
        if self.min_context_length is not None and model.capabilities.context_length < self.min_context_length:
            return False
        if self.max_context_length is not None and model.capabilities.context_length > self.max_context_length:
            return False
        if self.supports_images is not None and model.capabilities.supports_images != self.supports_images:
            return False
        if self.supports_function_calling is not None and model.capabilities.supports_function_calling != self.supports_function_calling:
            return False
        if self.supports_streaming is not None and model.capabilities.supports_streaming != self.supports_streaming:
            return False
        if self.supports_json_mode is not None and model.capabilities.supports_json_mode != self.supports_json_mode:
            return False
        
        # Performance filters
        if self.min_availability is not None and model.performance.availability_score < self.min_availability:
            return False
        if self.min_reliability is not None and model.performance.reliability_score < self.min_reliability:
            return False
        if self.max_response_time is not None and model.performance.response_time_avg > self.max_response_time:
            return False
        
        # User-specific filters
        if self.favorites_only and not model.is_favorite:
            return False
        if self.used_only and model.usage_count == 0:
            return False
        if self.min_rating is not None and (model.user_rating is None or model.user_rating < self.min_rating):
            return False
        
        # Local model filters
        if self.installed_only:
            if not model.local_info or not model.local_info.is_installed:
                return False
        if self.max_size_gb is not None and model.local_info:
            if model.local_info.size_gb > self.max_size_gb:
                return False
        
        # Availability filter
        if self.available_only and model.performance.availability_score < 0.5:
            return False
        
        # Tag filters
        model_tags_lower = [tag.lower() for tag in model.tags]
        if self.include_tags:
            for tag in self.include_tags:
                if tag.lower() not in model_tags_lower:
                    return False
        if self.exclude_tags:
            for tag in self.exclude_tags:
                if tag.lower() in model_tags_lower:
                    return False
        
        # Category filters
        if self.categories and model.category not in self.categories:
            return False
        if self.organizations and model.organization not in self.organizations:
            return False
        
        return True
    
    def _matches_search(self, model: ModelInfo) -> bool:
        """Check if model matches text search query"""
        if not self.search_query:
            return True
        
        query_lower = self.search_query.lower()
        
        # Search in specified fields
        for field in self.search_fields:
            field_value = ""
            
            if field == "name":
                field_value = model.name.lower()
            elif field == "description":
                field_value = model.description.lower()
            elif field == "tags":
                field_value = " ".join(model.tags).lower()
            elif field == "organization":
                field_value = model.organization.lower()
            elif field == "category":
                field_value = model.category.lower()
            elif field == "id":
                field_value = model.id.lower()
            
            # Support regex search for advanced users
            if query_lower.startswith("regex:"):
                try:
                    pattern = query_lower[6:]  # Remove "regex:" prefix
                    if re.search(pattern, field_value):
                        return True
                except re.error:
                    # Fall back to simple search if regex is invalid
                    if query_lower[6:] in field_value:
                        return True
            else:
                # Simple substring search
                if query_lower in field_value:
                    return True
        
        return False
    
    def get_sort_key(self, model: ModelInfo) -> Any:
        """Get sort key for a model based on sort field"""
        if self.sort_field == SortField.NAME:
            return model.name.lower()
        elif self.sort_field == SortField.PROVIDER:
            return model.provider.lower()
        elif self.sort_field == SortField.PRICE_INPUT:
            return model.pricing.input_price_per_1m
        elif self.sort_field == SortField.PRICE_OUTPUT:
            return model.pricing.output_price_per_1m
        elif self.sort_field == SortField.CONTEXT_LENGTH:
            return model.capabilities.context_length
        elif self.sort_field == SortField.RESPONSE_TIME:
            return model.performance.response_time_avg
        elif self.sort_field == SortField.POPULARITY:
            return model.performance.popularity_score
        elif self.sort_field == SortField.LAST_USED:
            return model.last_used or model.created_at
        elif self.sort_field == SortField.RATING:
            return model.user_rating or 0
        elif self.sort_field == SortField.CREATED_AT:
            return model.created_at
        else:
            return model.name.lower()
    
    def apply(self, models: List[ModelInfo]) -> List[ModelInfo]:
        """Apply filter and sort to list of models"""
        # Filter models
        filtered_models = [model for model in models if self.matches(model)]
        
        # Sort models
        reverse = (self.sort_order == SortOrder.DESCENDING)
        sorted_models = sorted(filtered_models, key=self.get_sort_key, reverse=reverse)
        
        return sorted_models
    
    def get_active_filter_count(self) -> int:
        """Get count of active filters (for UI display)"""
        count = 0
        
        if self.search_query:
            count += 1
        if self.providers:
            count += 1
        if self.exclude_providers:
            count += 1
        if self.max_input_price is not None or self.min_input_price is not None:
            count += 1
        if self.max_output_price is not None or self.min_output_price is not None:
            count += 1
        if self.free_only:
            count += 1
        if self.min_context_length is not None or self.max_context_length is not None:
            count += 1
        if self.supports_images is not None:
            count += 1
        if self.supports_function_calling is not None:
            count += 1
        if self.supports_streaming is not None:
            count += 1
        if self.supports_json_mode is not None:
            count += 1
        if self.min_availability is not None:
            count += 1
        if self.min_reliability is not None:
            count += 1
        if self.max_response_time is not None:
            count += 1
        if self.favorites_only:
            count += 1
        if self.used_only:
            count += 1
        if self.min_rating is not None:
            count += 1
        if self.installed_only:
            count += 1
        if self.max_size_gb is not None:
            count += 1
        if not self.available_only:  # Only count if disabled (non-default)
            count += 1
        if self.include_tags:
            count += 1
        if self.exclude_tags:
            count += 1
        if self.categories:
            count += 1
        if self.organizations:
            count += 1
        
        return count
    
    def clear_filters(self):
        """Reset all filters to defaults"""
        self.search_query = ""
        self.providers = []
        self.exclude_providers = []
        self.max_input_price = None
        self.max_output_price = None
        self.min_input_price = None
        self.min_output_price = None
        self.free_only = False
        self.min_context_length = None
        self.max_context_length = None
        self.supports_images = None
        self.supports_function_calling = None
        self.supports_streaming = None
        self.supports_json_mode = None
        self.min_availability = None
        self.min_reliability = None
        self.max_response_time = None
        self.favorites_only = False
        self.used_only = False
        self.min_rating = None
        self.installed_only = False
        self.max_size_gb = None
        self.available_only = True
        self.include_tags = []
        self.exclude_tags = []
        self.categories = []
        self.organizations = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for persistence"""
        return {
            'search_query': self.search_query,
            'search_fields': self.search_fields,
            'providers': self.providers,
            'exclude_providers': self.exclude_providers,
            'max_input_price': self.max_input_price,
            'max_output_price': self.max_output_price,
            'min_input_price': self.min_input_price,
            'min_output_price': self.min_output_price,
            'free_only': self.free_only,
            'min_context_length': self.min_context_length,
            'max_context_length': self.max_context_length,
            'supports_images': self.supports_images,
            'supports_function_calling': self.supports_function_calling,
            'supports_streaming': self.supports_streaming,
            'supports_json_mode': self.supports_json_mode,
            'min_availability': self.min_availability,
            'min_reliability': self.min_reliability,
            'max_response_time': self.max_response_time,
            'favorites_only': self.favorites_only,
            'used_only': self.used_only,
            'min_rating': self.min_rating,
            'installed_only': self.installed_only,
            'max_size_gb': self.max_size_gb,
            'available_only': self.available_only,
            'include_tags': self.include_tags,
            'exclude_tags': self.exclude_tags,
            'categories': self.categories,
            'organizations': self.organizations,
            'sort_field': self.sort_field.value,
            'sort_order': self.sort_order.value,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelFilter':
        """Create ModelFilter from dictionary"""
        filter_obj = cls()
        
        for key, value in data.items():
            if key == 'sort_field':
                filter_obj.sort_field = SortField(value)
            elif key == 'sort_order':
                filter_obj.sort_order = SortOrder(value)
            elif hasattr(filter_obj, key):
                setattr(filter_obj, key, value)
        
        return filter_obj

class ModelSearchEngine:
    """Advanced search engine for models"""
    
    def __init__(self):
        self.search_history: List[str] = []
        self.max_history = 20
    
    def search(self, models: List[ModelInfo], filter_obj: ModelFilter) -> List[ModelInfo]:
        """Perform search with given filter"""
        # Add search query to history
        if filter_obj.search_query and filter_obj.search_query not in self.search_history:
            self.search_history.insert(0, filter_obj.search_query)
            self.search_history = self.search_history[:self.max_history]
        
        return filter_obj.apply(models)
    
    def get_search_suggestions(self, models: List[ModelInfo], partial_query: str) -> List[str]:
        """Get search suggestions based on partial query"""
        if not partial_query:
            return self.search_history[:5]
        
        suggestions = set()
        partial_lower = partial_query.lower()
        
        # Add matching items from search history
        for query in self.search_history:
            if partial_lower in query.lower():
                suggestions.add(query)
        
        # Add matching model names
        for model in models:
            if partial_lower in model.name.lower():
                suggestions.add(model.name)
        
        # Add matching tags
        for model in models:
            for tag in model.tags:
                if partial_lower in tag.lower():
                    suggestions.add(tag)
        
        # Add matching organizations
        for model in models:
            if model.organization and partial_lower in model.organization.lower():
                suggestions.add(model.organization)
        
        return sorted(list(suggestions))[:10]
    
    def get_popular_searches(self, models: List[ModelInfo]) -> List[str]:
        """Get popular search terms based on model data"""
        popular_terms = []
        
        # Get most common organizations
        org_counts = {}
        for model in models:
            if model.organization:
                org_counts[model.organization] = org_counts.get(model.organization, 0) + 1
        
        # Add top organizations
        for org, count in sorted(org_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            popular_terms.append(org)
        
        # Add capability-based searches
        popular_terms.extend([
            "supports images",
            "function calling", 
            "free",
            "fast",
            "large context"
        ])
        
        return popular_terms