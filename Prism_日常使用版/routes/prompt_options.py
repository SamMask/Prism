# -*- coding: utf-8 -*-
"""
Prompt Options API Routes - Configuration CRUD
Local Insight v1.6.5 - Prompt Builder Advanced Features

Endpoints:
- GET  /api/prompt-options                     讀取完整配置
- POST /api/prompt-options/category/<key>      新增選項
- PUT  /api/prompt-options/category/<key>/<idx> 修改選項
- DELETE /api/prompt-options/category/<key>/<idx> 刪除選項
- POST /api/prompt-options/template            儲存當前狀態為模板
"""

import json
import os
from flask import Blueprint, request, jsonify, current_app

prompt_options_bp = Blueprint('prompt_options', __name__, url_prefix='/api')

# 配置檔路徑
CONFIG_FILE = 'static/config/prompt_options.json'


def get_config_path():
    """取得配置檔完整路徑"""
    return os.path.join(current_app.root_path, CONFIG_FILE)


def load_config():
    """載入配置檔"""
    config_path = get_config_path()
    if not os.path.exists(config_path):
        return None
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_config(config):
    """儲存配置檔"""
    config_path = get_config_path()
    
    # 更新時間戳
    from datetime import datetime
    config['lastUpdated'] = datetime.now().strftime('%Y-%m-%d')
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


# ===================================================================
# GET - 讀取配置
# ===================================================================

@prompt_options_bp.route('/prompt-options', methods=['GET'])
def get_options():
    """
    取得完整配置檔
    Response: { status, data: { version, categories, quickTemplates, ... } }
    """
    try:
        config = load_config()
        if config is None:
            return jsonify({
                'status': 'error',
                'message': 'Configuration file not found'
            }), 404
        
        return jsonify({
            'status': 'success',
            'data': config
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ===================================================================
# POST - 新增選項到指定類別
# ===================================================================

@prompt_options_bp.route('/prompt-options/category/<category_key>', methods=['POST'])
def add_option(category_key):
    """
    新增選項到指定類別
    Request: { value: "New Option" } 或 { key, display, output } (i18n 格式)
    Response: { status, data: { index } }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Request body is required'
            }), 400
        
        config = load_config()
        if config is None:
            return jsonify({
                'status': 'error',
                'message': 'Configuration file not found'
            }), 404
        
        # 檢查類別是否存在
        if category_key not in config.get('categories', {}):
            return jsonify({
                'status': 'error',
                'message': f'Category "{category_key}" not found'
            }), 404
        
        category = config['categories'][category_key]
        options = category.get('options', [])
        
        # 決定新增的格式 (純文字 或 i18n 物件)
        if 'value' in data:
            # 純文字格式
            new_option = data['value'].strip()
            if not new_option:
                return jsonify({
                    'status': 'error',
                    'message': 'Option value cannot be empty'
                }), 400
            
            # 檢查重複
            if new_option in options:
                return jsonify({
                    'status': 'error',
                    'message': 'Option already exists'
                }), 400
                
        elif 'display' in data and 'output' in data:
            # i18n 格式
            new_option = {
                'key': data.get('key', data['output'].lower().replace(' ', '_')),
                'display': data['display'].strip(),
                'output': data['output'].strip()
            }
            if not new_option['display'] or not new_option['output']:
                return jsonify({
                    'status': 'error',
                    'message': 'Display and output are required'
                }), 400
        else:
            return jsonify({
                'status': 'error',
                'message': 'Invalid format. Use { value } or { display, output }'
            }), 400
        
        # 新增選項
        options.append(new_option)
        category['options'] = options
        save_config(config)
        
        return jsonify({
            'status': 'success',
            'data': {
                'index': len(options) - 1,
                'option': new_option
            }
        }), 201
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ===================================================================
# PUT - 修改指定選項
# ===================================================================

@prompt_options_bp.route('/prompt-options/category/<category_key>/<int:index>', methods=['PUT'])
def update_option(category_key, index):
    """
    修改指定類別中的選項
    Request: { value: "Updated Option" } 或 { key, display, output }
    Response: { status }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Request body is required'
            }), 400
        
        config = load_config()
        if config is None:
            return jsonify({
                'status': 'error',
                'message': 'Configuration file not found'
            }), 404
        
        # 檢查類別是否存在
        if category_key not in config.get('categories', {}):
            return jsonify({
                'status': 'error',
                'message': f'Category "{category_key}" not found'
            }), 404
        
        category = config['categories'][category_key]
        options = category.get('options', [])
        
        # 檢查索引範圍
        if index < 0 or index >= len(options):
            return jsonify({
                'status': 'error',
                'message': f'Index {index} out of range (0-{len(options)-1})'
            }), 400
        
        # 決定更新的格式
        if 'value' in data:
            new_value = data['value'].strip()
            if not new_value:
                return jsonify({
                    'status': 'error',
                    'message': 'Option value cannot be empty'
                }), 400
            options[index] = new_value
            
        elif 'display' in data or 'output' in data:
            # i18n 格式更新
            current = options[index] if isinstance(options[index], dict) else {}
            options[index] = {
                'key': data.get('key', current.get('key', '')),
                'display': data.get('display', current.get('display', '')).strip(),
                'output': data.get('output', current.get('output', '')).strip()
            }
        else:
            return jsonify({
                'status': 'error',
                'message': 'Invalid format'
            }), 400
        
        category['options'] = options
        save_config(config)
        
        return jsonify({
            'status': 'success',
            'data': {
                'option': options[index]
            }
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ===================================================================
# DELETE - 刪除指定選項
# ===================================================================

@prompt_options_bp.route('/prompt-options/category/<category_key>/<int:index>', methods=['DELETE'])
def delete_option(category_key, index):
    """
    刪除指定類別中的選項
    Response: { status, data: { deleted } }
    """
    try:
        config = load_config()
        if config is None:
            return jsonify({
                'status': 'error',
                'message': 'Configuration file not found'
            }), 404
        
        # 檢查類別是否存在
        if category_key not in config.get('categories', {}):
            return jsonify({
                'status': 'error',
                'message': f'Category "{category_key}" not found'
            }), 404
        
        category = config['categories'][category_key]
        options = category.get('options', [])
        
        # 檢查索引範圍
        if index < 0 or index >= len(options):
            return jsonify({
                'status': 'error',
                'message': f'Index {index} out of range (0-{len(options)-1})'
            }), 400
        
        # 刪除選項
        deleted = options.pop(index)
        category['options'] = options
        save_config(config)
        
        return jsonify({
            'status': 'success',
            'data': {
                'deleted': deleted
            }
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ===================================================================
# POST - 儲存當前狀態為模板
# ===================================================================

@prompt_options_bp.route('/prompt-options/template', methods=['POST'])
def save_template():
    """
    儲存當前表單狀態為快速模板
    Request: {
        id: "my-template",
        name: "🎨 我的模板",
        preset: {
            style: "Cinematic",
            lighting: "Natural Light",
            ...
        }
    }
    Response: { status, data: { index } }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Request body is required'
            }), 400
        
        # 驗證必要欄位
        if not data.get('name'):
            return jsonify({
                'status': 'error',
                'message': 'name is required'
            }), 400
        
        # preset 可為空字典，允許無預設值的模板
        preset = data.get('preset', {})
        
        config = load_config()
        if config is None:
            return jsonify({
                'status': 'error',
                'message': 'Configuration file not found'
            }), 404
        
        # 建立模板物件
        template_id = data.get('id') or data['name'].lower().replace(' ', '-').replace(':', '')
        
        new_template = {
            'id': template_id,
            'name': data['name'],
            'preset': preset,
            'isCustom': True  # Mark as user-created template (can be deleted)
        }
        
        templates = config.get('quickTemplates', [])
        
        # 檢查 ID 是否已存在 (若存在則更新)
        existing_index = next(
            (i for i, t in enumerate(templates) if t.get('id') == template_id),
            None
        )
        
        if existing_index is not None:
            templates[existing_index] = new_template
            action = 'updated'
        else:
            templates.append(new_template)
            action = 'created'
        
        config['quickTemplates'] = templates
        save_config(config)
        
        return jsonify({
            'status': 'success',
            'data': {
                'action': action,
                'template': new_template,
                'index': existing_index if existing_index is not None else len(templates) - 1
            }
        }), 201 if action == 'created' else 200
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ===================================================================
# DELETE - 刪除模板
# ===================================================================

@prompt_options_bp.route('/prompt-options/template/<template_id>', methods=['DELETE'])
def delete_template(template_id):
    """
    刪除指定模板
    Response: { status, data: { deleted } }
    """
    try:
        config = load_config()
        if config is None:
            return jsonify({
                'status': 'error',
                'message': 'Configuration file not found'
            }), 404
        
        templates = config.get('quickTemplates', [])
        
        # 找到模板
        template_index = next(
            (i for i, t in enumerate(templates) if t.get('id') == template_id),
            None
        )
        
        if template_index is None:
            return jsonify({
                'status': 'error',
                'message': f'Template "{template_id}" not found'
            }), 404
        
        deleted = templates.pop(template_index)
        config['quickTemplates'] = templates
        save_config(config)
        
        return jsonify({
            'status': 'success',
            'data': {
                'deleted': deleted
            }
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
