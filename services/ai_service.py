# -*- coding: utf-8 -*-
"""
AI Service - Ollama Integration for Prism V2
Phase 3.1: Auto-Tagging (LLaVA Vision Model)

Provides:
- Image analysis and auto-tagging via Ollama LLaVA
- Note summarization (text-based)
- Ollama status checking
"""

import os
import base64
import json
import requests
from typing import Optional, List, Dict, Any
from flask import current_app

# Default configuration
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_VISION_MODEL = "llava"  # or "bakllava", "llava:13b"
DEFAULT_TEXT_MODEL = "llama3.2"  # For text-only tasks (fallback)


def get_available_text_model() -> str:
    """Get the first available text model from Ollama"""
    try:
        response = requests.get(f"{DEFAULT_OLLAMA_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_names = [m.get('name', '') for m in models]
            
            # Prefer llama, then gemma, then mistral
            for name in model_names:
                if name.startswith('llama') and 'llava' not in name:
                    return name
            for name in model_names:
                if name.startswith('gemma'):
                    return name
            for name in model_names:
                if name.startswith('mistral') or name.startswith('ministral'):
                    return name
            # Fallback: return any non-vision model
            for name in model_names:
                if 'llava' not in name and 'bakllava' not in name:
                    return name
    except:
        pass
    return DEFAULT_TEXT_MODEL

class OllamaClient:
    """Client for interacting with Ollama API"""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.environ.get('OLLAMA_URL', DEFAULT_OLLAMA_URL)
        self.timeout = 120  # Longer timeout for model inference
    
    def is_available(self) -> bool:
        """Check if Ollama server is running"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def list_models(self) -> List[Dict[str, Any]]:
        """Get list of available models"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('models', [])
            return []
        except requests.RequestException:
            return []
    
    def has_model(self, model_name: str) -> bool:
        """Check if a specific model is available"""
        models = self.list_models()
        return any(m.get('name', '').startswith(model_name) for m in models)
    
    def generate(self, prompt: str, model: str = DEFAULT_TEXT_MODEL, 
                 images: Optional[List[str]] = None) -> Optional[str]:
        """
        Generate response from Ollama
        
        Args:
            prompt: The text prompt
            model: Model name (e.g., 'llava', 'llama3.2')
            images: List of base64-encoded images (for vision models)
        
        Returns:
            Generated text response or None if failed
        """
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False
            }
            
            if images:
                payload["images"] = images
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('response', '').strip()
            else:
                print(f"[AI] Ollama error: {response.status_code} - {response.text}")
                return None
                
        except requests.RequestException as e:
            print(f"[AI] Request failed: {e}")
            return None


def image_to_base64(image_path: str) -> Optional[str]:
    """Convert image file to base64 string"""
    try:
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        print(f"[AI] Failed to read image: {e}")
        return None


def analyze_image_for_tags(image_path: str, 
                           model: str = DEFAULT_VISION_MODEL,
                           language: str = "en") -> Dict[str, Any]:
    """
    Analyze image and return suggested tags
    
    Args:
        image_path: Path to image file
        model: Vision model to use
        language: Response language ('en' or 'zh')
    
    Returns:
        {
            'success': bool,
            'tags': List[str],
            'description': str,
            'error': Optional[str]
        }
    """
    client = OllamaClient()
    
    # Check Ollama availability
    if not client.is_available():
        return {
            'success': False,
            'tags': [],
            'description': '',
            'error': 'Ollama server is not running. Please start Ollama first.'
        }
    
    # Check model availability
    if not client.has_model(model):
        return {
            'success': False,
            'tags': [],
            'description': '',
            'error': f'Model "{model}" is not installed. Run: ollama pull {model}'
        }
    
    # Convert image to base64
    image_b64 = image_to_base64(image_path)
    if not image_b64:
        return {
            'success': False,
            'tags': [],
            'description': '',
            'error': 'Failed to read image file.'
        }
    
    # Build prompt based on language
    if language == "zh":
        prompt = """請分析這張圖片並回傳：
1. 5-10個描述性標籤（用逗號分隔）
2. 一句簡短描述

請用以下JSON格式回覆：
{"tags": ["tag1", "tag2", ...], "description": "圖片描述"}

只回覆JSON，不要其他文字。"""
    else:
        prompt = """Analyze this image and return:
1. 5-10 descriptive tags (comma-separated)
2. A brief description (one sentence)

Reply in this JSON format only:
{"tags": ["tag1", "tag2", ...], "description": "image description"}

Only return JSON, no other text."""
    
    # Call Ollama
    response = client.generate(prompt, model=model, images=[image_b64])
    
    if not response:
        return {
            'success': False,
            'tags': [],
            'description': '',
            'error': 'No response from AI model.'
        }
    
    # Parse JSON response
    try:
        # Try to extract JSON from response (model might include other text)
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            json_str = response[json_start:json_end]
            result = json.loads(json_str)
            return {
                'success': True,
                'tags': result.get('tags', []),
                'description': result.get('description', ''),
                'error': None
            }
    except json.JSONDecodeError:
        pass
    
    # Fallback: try to extract tags manually
    tags = [t.strip() for t in response.split(',') if t.strip()][:10]
    return {
        'success': True,
        'tags': tags,
        'description': response[:200],
        'error': None
    }


def summarize_note(content: str, 
                   model: str = DEFAULT_TEXT_MODEL,
                   max_length: int = 100) -> Dict[str, Any]:
    """
    Generate AI summary for note content
    
    Args:
        content: Note text content
        model: Text model to use
        max_length: Maximum summary length
    
    Returns:
        {
            'success': bool,
            'summary': str,
            'error': Optional[str]
        }
    """
    client = OllamaClient()
    
    if not client.is_available():
        return {
            'success': False,
            'summary': '',
            'error': 'Ollama server is not running.'
        }
    
    # Truncate content if too long
    content_truncated = content[:4000] if len(content) > 4000 else content
    
    prompt = f"""Summarize the following text in {max_length} words or less:

{content_truncated}

Summary:"""
    
    response = client.generate(prompt, model=model)
    
    if response:
        return {
            'success': True,
            'summary': response[:500],  # Limit length
            'error': None
        }
    else:
        return {
            'success': False,
            'summary': '',
            'error': 'Failed to generate summary.'
        }


def get_ollama_status() -> Dict[str, Any]:
    """Get Ollama server status and available models"""
    client = OllamaClient()
    
    if not client.is_available():
        return {
            'available': False,
            'models': [],
            'vision_ready': False,
            'text_ready': False,
            'error': 'Ollama server is not running at ' + client.base_url
        }
    
    models = client.list_models()
    model_names = [m.get('name', '') for m in models]
    
    # Check for vision and text models
    vision_ready = any(name.startswith(('llava', 'bakllava')) for name in model_names)
    text_ready = any(name.startswith(('llama', 'mistral', 'qwen')) for name in model_names)
    
    return {
        'available': True,
        'models': model_names,
        'vision_ready': vision_ready,
        'text_ready': text_ready,
        'error': None
    }


def extract_tags_from_text(content: str, 
                           model: str = None,
                           max_tags: int = 10) -> Dict[str, Any]:
    """
    Extract tags from text content using AI
    
    Args:
        content: Text content to analyze
        model: Text model to use (auto-detect if None)
        max_tags: Maximum number of tags to return
    
    Returns:
        {
            'success': bool,
            'tags': List[str],
            'error': Optional[str]
        }
    """
    # Auto-detect available model if not specified
    if model is None:
        model = get_available_text_model()
    
    client = OllamaClient()
    
    if not client.is_available():
        return {
            'success': False,
            'tags': [],
            'error': 'Ollama server is not running.'
        }
    
    # Truncate content if too long
    content_truncated = content[:3000] if len(content) > 3000 else content
    
    prompt = f"""請從以下文字中提取 5-10 個描述性標籤（關鍵詞）。
標籤應該是名詞或形容詞，能夠概括文章主題、地點、食物類型等。

文字內容：
{content_truncated}

請用以下 JSON 格式回覆：
{{"tags": ["標籤1", "標籤2", "標籤3", ...]}}

只回覆 JSON，不要其他文字。"""
    
    response = client.generate(prompt, model=model)
    
    if not response:
        return {
            'success': False,
            'tags': [],
            'error': 'No response from AI model.'
        }
    
    # Parse JSON response
    try:
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            json_str = response[json_start:json_end]
            result = json.loads(json_str)
            tags = result.get('tags', [])
            # Filter and limit tags
            tags = [t.strip() for t in tags if t.strip() and len(t.strip()) > 1][:max_tags]
            return {
                'success': True,
                'tags': tags,
                'error': None
            }
    except json.JSONDecodeError:
        pass
    
    # Fallback: try to extract comma-separated tags
    tags = [t.strip() for t in response.split(',') if t.strip() and len(t.strip()) > 1][:max_tags]
    return {
        'success': len(tags) > 0,
        'tags': tags,
        'error': None if tags else 'Failed to parse response'
    }
