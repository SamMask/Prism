# -*- coding: utf-8 -*-
"""
Notes Helpers - 共用解析函數
Local Insight v1.0

將 SQL 結果解析為 Python 物件的函數，
支援 JSON 格式和舊版 GROUP_CONCAT 格式的向後相容。
"""

import json
from typing import List, Dict, Any, Optional


def parse_tags_json(tags_data: Optional[str]) -> List[Dict[str, Any]]:
    """
    解析標籤資料 (v1.0: JSON 格式)
    
    Args:
        tags_data: JSON 陣列字串，如 '[{"id":1,"name":"tag1"}]'
        
    Returns:
        標籤字典列表，如 [{'id': 1, 'name': 'tag1'}]
    """
    if not tags_data:
        return []
    
    try:
        tags = json.loads(tags_data)
        # 確保每個項目都有 id 和 name
        return [
            {'id': int(t.get('id', 0)), 'name': str(t.get('name', ''))}
            for t in tags if t.get('name')
        ]
    except (json.JSONDecodeError, TypeError):
        return []


def parse_urls_json(urls_data: Optional[str]) -> List[str]:
    """
    解析網址資料 (v1.0: JSON 格式)
    
    Args:
        urls_data: JSON 陣列字串，如 '["http://a.com","http://b.com"]'
        
    Returns:
        網址字串列表
    """
    if not urls_data:
        return []
    
    try:
        urls = json.loads(urls_data)
        return [str(u) for u in urls if u]
    except (json.JSONDecodeError, TypeError):
        return []


def parse_tags_legacy(tags_str: Optional[str]) -> List[Dict[str, Any]]:
    """
    解析標籤資料 (v0.x: GROUP_CONCAT 格式，向後相容)
    
    Args:
        tags_str: 舊格式字串，如 '1:tag1||2:tag2'
        
    Returns:
        標籤字典列表
    """
    if not tags_str:
        return []
    
    tags = []
    for tag_str in tags_str.split('||'):
        if ':' in tag_str:
            try:
                tag_id, tag_name = tag_str.split(':', 1)
                tags.append({'id': int(tag_id), 'name': tag_name})
            except (ValueError, TypeError):
                continue
    return tags


def parse_urls_legacy(urls_str: Optional[str]) -> List[str]:
    """
    解析網址資料 (v0.x: GROUP_CONCAT 格式，向後相容)
    
    Args:
        urls_str: 舊格式字串，如 'http://a.com||http://b.com'
        
    Returns:
        網址字串列表
    """
    if not urls_str:
        return []
    
    return [url for url in urls_str.split('||') if url]
