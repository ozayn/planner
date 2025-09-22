#!/usr/bin/env python3
"""
Enhanced LLM Fallback System for Venue Discovery
Integrates multiple AI models with automatic fallback
"""

import os
import sys
import requests
import json
import time
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from enum import Enum
# Import centralized environment configuration
from scripts.env_config import ensure_env_loaded, get_api_keys

# Ensure environment is loaded
ensure_env_loaded()

# Setup logging for LLM fallback system
def setup_llm_logging():
    """Setup logging for LLM fallback system"""
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(logs_dir, 'llm_fallback.log')),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger('llm_fallback')

# Setup logging
llm_logger = setup_llm_logging()

class ModelProvider(Enum):
    GROQ = "groq"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    COHERE = "cohere"
    GOOGLE = "google"
    MISTRAL = "mistral"
    HUGGINGFACE = "huggingface"
    DEEPAI = "deepai"
    MOCK = "mock"

@dataclass
class ModelConfig:
    provider: ModelProvider
    api_key: str
    base_url: str
    model_name: str
    max_tokens: int
    temperature: float
    priority: int
    cost_tier: str  # 'free', 'low', 'medium', 'high'

class EnhancedLLMFallback:
    """Enhanced LLM system with multiple model fallbacks"""
    
    def __init__(self, silent: bool = False):
        self.silent = silent
        self.models = self._initialize_models()
        self.usage_stats = {
            'groq': {'requests': 0, 'tokens': 0, 'errors': 0},
            'openai': {'requests': 0, 'tokens': 0, 'errors': 0},
            'anthropic': {'requests': 0, 'tokens': 0, 'errors': 0},
            'cohere': {'requests': 0, 'tokens': 0, 'errors': 0},
            'google': {'requests': 0, 'tokens': 0, 'errors': 0},
            'mistral': {'requests': 0, 'tokens': 0, 'errors': 0},
            'huggingface': {'requests': 0, 'tokens': 0, 'errors': 0}
        }
        
        if not self.silent:
            self._print_model_status()
    
    def _initialize_models(self) -> List[ModelConfig]:
        """Initialize all available models in priority order"""
        models = []
        
        # Get API keys from centralized environment
        api_keys = get_api_keys()
        
        # Google Gemini (NEW HIGHEST PRIORITY - Best balance of quality and cost)
        if api_keys['GOOGLE_API_KEY']:
            models.append(ModelConfig(
                provider=ModelProvider.GOOGLE,
                api_key=api_keys['GOOGLE_API_KEY'],
                base_url='https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent',
                model_name='gemini-1.5-flash',
                max_tokens=2500,
                temperature=0.3,
                priority=1,
                cost_tier='low'
            ))
        
        # Groq (Free tier - fallback after Gemini)
        if api_keys['GROQ_API_KEY']:
            models.append(ModelConfig(
                provider=ModelProvider.GROQ,
                api_key=api_keys['GROQ_API_KEY'],
                base_url='https://api.groq.com/openai/v1/chat/completions',
                model_name='llama-3.3-70b-versatile',
                max_tokens=2500,
                temperature=0.3,
                priority=2,
                cost_tier='free'
            ))
        
        # OpenAI GPT-4 (High quality)
        if api_keys['OPENAI_API_KEY']:
            models.append(ModelConfig(
                provider=ModelProvider.OPENAI,
                api_key=api_keys['OPENAI_API_KEY'],
                base_url='https://api.openai.com/v1/chat/completions',
                model_name='gpt-4-turbo',
                max_tokens=2500,
                temperature=0.3,
                priority=3,
                cost_tier='high'
            ))
            
            # OpenAI GPT-3.5 (Cheaper fallback)
            models.append(ModelConfig(
                provider=ModelProvider.OPENAI,
                api_key=api_keys['OPENAI_API_KEY'],
                base_url='https://api.openai.com/v1/chat/completions',
                model_name='gpt-3.5-turbo',
                max_tokens=2500,
                temperature=0.3,
                priority=4,
                cost_tier='medium'
            ))
        
        # Anthropic Claude (High quality)
        if api_keys['ANTHROPIC_API_KEY']:
            models.append(ModelConfig(
                provider=ModelProvider.ANTHROPIC,
                api_key=api_keys['ANTHROPIC_API_KEY'],
                base_url='https://api.anthropic.com/v1/messages',
                model_name='claude-3-sonnet-20240229',
                max_tokens=2500,
                temperature=0.3,
                priority=5,
                cost_tier='medium'
            ))
        
        # Cohere (Alternative model)
        if api_keys['COHERE_API_KEY']:
            models.append(ModelConfig(
                provider=ModelProvider.COHERE,
                api_key=api_keys['COHERE_API_KEY'],
                base_url='https://api.cohere.ai/v1/generate',
                model_name='command',
                max_tokens=2500,
                temperature=0.3,
                priority=6,
                cost_tier='low'
            ))
        
        # Hugging Face (Free tier with generous limits)
        if api_keys['HUGGINGFACE_API_KEY']:
            models.append(ModelConfig(
                provider=ModelProvider.HUGGINGFACE,
                api_key=api_keys['HUGGINGFACE_API_KEY'],
                base_url='https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium',
                model_name='microsoft/DialoGPT-medium',
                max_tokens=2500,
                temperature=0.3,
                priority=7,
                cost_tier='free'
            ))
            
            # Add another Hugging Face model for better coverage
            models.append(ModelConfig(
                provider=ModelProvider.HUGGINGFACE,
                api_key=api_keys['HUGGINGFACE_API_KEY'],
                base_url='https://api-inference.huggingface.co/models/distilgpt2',
                model_name='distilgpt2',
                max_tokens=2500,
                temperature=0.3,
                priority=8,
                cost_tier='free'
            ))

        # Mistral (European model)
        if api_keys['MISTRAL_API_KEY']:
            models.append(ModelConfig(
                provider=ModelProvider.MISTRAL,
                api_key=api_keys['MISTRAL_API_KEY'],
                base_url='https://api.mistral.ai/v1/chat/completions',
                model_name='mistral-large-latest',
                max_tokens=2500,
                temperature=0.3,
                priority=9,
                cost_tier='medium'
            ))
        
        # Sort by priority
        models.sort(key=lambda x: x.priority)
        
        # Add mock as final fallback
        models.append(ModelConfig(
            provider=ModelProvider.MOCK,
            api_key='',
            base_url='',
            model_name='mock',
            max_tokens=0,
            temperature=0,
            priority=999,
            cost_tier='free'
        ))
        
        return models
    
    def _print_model_status(self):
        """Print available models and their status"""
        print("🤖 Enhanced LLM Fallback System Initialized")
        print("Available models:")
        
        for model in self.models:
            if model.provider != ModelProvider.MOCK:
                status = "✅" if model.api_key else "❌"
                print(f"  {status} {model.provider.value}:{model.model_name} ({model.cost_tier})")
        
        print(f"Total models available: {len([m for m in self.models if m.provider != ModelProvider.MOCK])}")
        print()
    
    def query_with_fallback(self, prompt: str, context: str = "") -> Dict[str, Any]:
        """Query LLM with automatic fallback through multiple models"""
        
        llm_logger.info(f"Starting LLM query with fallback. Prompt length: {len(prompt)}")
        llm_logger.debug(f"Prompt: {prompt[:200]}...")
        
        for model in self.models:
            try:
                if not self.silent:
                    print(f"🔄 Trying {model.provider.value} ({model.model_name})...")
                
                if model.provider == ModelProvider.MOCK:
                    llm_logger.warning("Using mock response as fallback")
                    return self._get_mock_response(prompt, context)
                
                response = self._query_model(model, prompt, context)
                
                if response.get('success'):
                    llm_logger.info(f"Success with {model.provider.value} ({model.model_name})")
                    if not self.silent:
                        print(f"✅ Success with {model.provider.value} ({model.model_name})")
                    
                    # Update usage stats
                    self.usage_stats[model.provider.value]['requests'] += 1
                    self.usage_stats[model.provider.value]['tokens'] += response.get('tokens_used', 0)
                    
                    return response
                else:
                    llm_logger.warning(f"{model.provider.value} failed: {response.get('error', 'Unknown error')}")
                    if not self.silent:
                        print(f"❌ {model.provider.value} failed: {response.get('error', 'Unknown error')}")
                    
                    # Update error stats
                    self.usage_stats[model.provider.value]['errors'] += 1
                    
            except Exception as e:
                llm_logger.error(f"Exception with {model.provider.value}: {str(e)}", exc_info=True)
                if not self.silent:
                    print(f"❌ {model.provider.value} error: {str(e)}")
                
                # Update error stats
                self.usage_stats[model.provider.value]['errors'] += 1
                continue
        
        # If all models fail, return mock response
        llm_logger.error("All LLM models failed, using mock response")
        if not self.silent:
            print("⚠️  All models failed, using mock response")
        return self._get_mock_response(prompt, context)
    
    def _query_model(self, model: ModelConfig, prompt: str, context: str) -> Dict[str, Any]:
        """Query a specific model"""
        
        if model.provider == ModelProvider.GROQ:
            return self._query_groq(model, prompt)
        elif model.provider == ModelProvider.OPENAI:
            return self._query_openai(model, prompt)
        elif model.provider == ModelProvider.ANTHROPIC:
            return self._query_anthropic(model, prompt)
        elif model.provider == ModelProvider.COHERE:
            return self._query_cohere(model, prompt)
        elif model.provider == ModelProvider.GOOGLE:
            return self._query_google(model, prompt)
        elif model.provider == ModelProvider.MISTRAL:
            return self._query_mistral(model, prompt)
        elif model.provider == ModelProvider.HUGGINGFACE:
            return self._query_huggingface(model, prompt)
        else:
            return {'success': False, 'error': 'Unknown provider'}
    
    def _query_groq(self, model: ModelConfig, prompt: str) -> Dict[str, Any]:
        """Query Groq API"""
        headers = {
            'Authorization': f'Bearer {model.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': model.model_name,
            'messages': [
                {'role': 'system', 'content': 'You are a helpful cultural tourism expert. Always respond with valid JSON.'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': model.temperature,
            'max_tokens': model.max_tokens
        }
        
        response = requests.post(model.base_url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            tokens_used = result.get('usage', {}).get('total_tokens', 0)
            return {'success': True, 'content': content, 'provider': 'groq', 'tokens_used': tokens_used}
        else:
            return {'success': False, 'error': f'HTTP {response.status_code}: {response.text}'}
    
    def _query_openai(self, model: ModelConfig, prompt: str) -> Dict[str, Any]:
        """Query OpenAI API"""
        headers = {
            'Authorization': f'Bearer {model.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': model.model_name,
            'messages': [
                {'role': 'system', 'content': 'You are a helpful cultural tourism expert. Always respond with valid JSON.'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': model.temperature,
            'max_tokens': model.max_tokens
        }
        
        response = requests.post(model.base_url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            tokens_used = result.get('usage', {}).get('total_tokens', 0)
            return {'success': True, 'content': content, 'provider': 'openai', 'tokens_used': tokens_used}
        else:
            return {'success': False, 'error': f'HTTP {response.status_code}: {response.text}'}
    
    def _query_anthropic(self, model: ModelConfig, prompt: str) -> Dict[str, Any]:
        """Query Anthropic Claude API"""
        headers = {
            'x-api-key': model.api_key,
            'Content-Type': 'application/json',
            'anthropic-version': '2023-06-01'
        }
        
        data = {
            'model': model.model_name,
            'max_tokens': model.max_tokens,
            'temperature': model.temperature,
            'messages': [
                {'role': 'user', 'content': prompt}
            ]
        }
        
        response = requests.post(model.base_url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            content = result['content'][0]['text']
            tokens_used = result.get('usage', {}).get('total_tokens', 0)
            return {'success': True, 'content': content, 'provider': 'anthropic', 'tokens_used': tokens_used}
        else:
            return {'success': False, 'error': f'HTTP {response.status_code}: {response.text}'}
    
    def _query_cohere(self, model: ModelConfig, prompt: str) -> Dict[str, Any]:
        """Query Cohere API"""
        headers = {
            'Authorization': f'Bearer {model.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': model.model_name,
            'prompt': prompt,
            'max_tokens': model.max_tokens,
            'temperature': model.temperature
        }
        
        response = requests.post(model.base_url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            content = result['generations'][0]['text']
            tokens_used = result.get('meta', {}).get('tokens', {}).get('total_tokens', 0)
            return {'success': True, 'content': content, 'provider': 'cohere', 'tokens_used': tokens_used}
        else:
            return {'success': False, 'error': f'HTTP {response.status_code}: {response.text}'}
    
    def _query_google(self, model: ModelConfig, prompt: str) -> Dict[str, Any]:
        """Query Google Gemini API"""
        headers = {
            'Content-Type': 'application/json'
        }
        
        data = {
            'contents': [{
                'parts': [{'text': prompt}]
            }],
            'generationConfig': {
                'temperature': model.temperature,
                'maxOutputTokens': model.max_tokens
            }
        }
        
        url = f"{model.base_url}?key={model.api_key}"
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            content = result['candidates'][0]['content']['parts'][0]['text']
            tokens_used = result.get('usageMetadata', {}).get('totalTokenCount', 0)
            return {'success': True, 'content': content, 'provider': 'google', 'tokens_used': tokens_used}
        else:
            return {'success': False, 'error': f'HTTP {response.status_code}: {response.text}'}
    
    def _query_mistral(self, model: ModelConfig, prompt: str) -> Dict[str, Any]:
        """Query Mistral API"""
        headers = {
            'Authorization': f'Bearer {model.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': model.model_name,
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'temperature': model.temperature,
            'max_tokens': model.max_tokens
        }
        
        response = requests.post(model.base_url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            tokens_used = result.get('usage', {}).get('total_tokens', 0)
            return {'success': True, 'content': content, 'provider': 'mistral', 'tokens_used': tokens_used}
        else:
            return {'success': False, 'error': f'HTTP {response.status_code}: {response.text}'}
    
    def _query_huggingface(self, model: ModelConfig, prompt: str) -> Dict[str, Any]:
        """Query Hugging Face API"""
        headers = {
            'Authorization': f'Bearer {model.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'inputs': prompt,
            'parameters': {
                'max_length': model.max_tokens,
                'temperature': model.temperature,
                'return_full_text': False
            }
        }
        
        response = requests.post(model.base_url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                content = result[0].get('generated_text', '')
            else:
                content = str(result)
            return {'success': True, 'content': content, 'provider': 'huggingface', 'tokens_used': len(prompt) + len(content)}
        else:
            return {'success': False, 'error': f'HTTP {response.status_code}: {response.text}'}
    
    def _get_mock_response(self, prompt: str, context: str) -> Dict[str, Any]:
        """Return mock response when all models fail"""
        return {
            'success': True,
            'content': '{"venues": [{"name": "Mock Venue", "venue_type": "museum", "description": "Fallback venue"}]}',
            'provider': 'mock',
            'tokens_used': 0
        }
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for all models"""
        return self.usage_stats
    
    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        return [f"{model.provider.value}:{model.model_name}" for model in self.models if model.provider != ModelProvider.MOCK]

# Test the system
if __name__ == '__main__':
    llm = EnhancedLLMFallback()
    
    print("Testing venue discovery with multiple models...")
    prompt = "List 3 museums in Paris that offer tours"
    result = llm.query_with_fallback(prompt)
    
    print(f"\nResult from: {result['provider']}")
    print(f"Content: {result['content'][:200]}...")
    
    print(f"\nUsage stats: {llm.get_usage_stats()}")
