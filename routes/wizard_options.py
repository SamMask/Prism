# -*- coding: utf-8 -*-
"""
Wizard Options API Routes - Inspiration Wizard Configuration CRUD
Local Insight v1.6.6 - Wizard Word Bank Management

Endpoints:
- GET  /api/wizard-options                       讀取完整配置
- POST /api/wizard-options/dimension/<key>       新增靈感詞
- DELETE /api/wizard-options/dimension/<key>/<idx> 刪除靈感詞
"""

import json
import os
from flask import Blueprint, request, jsonify, current_app

wizard_options_bp = Blueprint('wizard_options', __name__, url_prefix='/api')

# 配置檔路徑
CONFIG_FILE = 'static/config/wizard_options.json'


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

@wizard_options_bp.route('/wizard-options', methods=['GET'])
def get_wizard_options():
    """
    取得完整 Wizard 配置檔
    Response: { status, data: { version, dimensions, technicalSpecs, ... } }
    """
    try:
        config = load_config()
        if config is None:
            return jsonify({
                'status': 'error',
                'message': 'Wizard configuration file not found'
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
# POST - 新增靈感詞到指定維度
# ===================================================================

@wizard_options_bp.route('/wizard-options/dimension/<dimension_key>', methods=['POST'])
def add_wizard_option(dimension_key):
    """
    新增靈感詞到指定維度
    Request: { value: "New inspiration text" }
    Response: { status, data: { index, option } }
    """
    try:
        data = request.get_json()
        if not data or 'value' not in data:
            return jsonify({
                'status': 'error',
                'message': 'value is required'
            }), 400
        
        new_value = data['value'].strip()
        if not new_value:
            return jsonify({
                'status': 'error',
                'message': 'value cannot be empty'
            }), 400
        
        config = load_config()
        if config is None:
            return jsonify({
                'status': 'error',
                'message': 'Configuration file not found'
            }), 404
        
        # 檢查維度是否存在
        if dimension_key not in config.get('dimensions', {}):
            return jsonify({
                'status': 'error',
                'message': f'Dimension "{dimension_key}" not found'
            }), 404
        
        dimension = config['dimensions'][dimension_key]
        options = dimension.get('options', [])
        
        # 檢查重複
        if new_value in options:
            return jsonify({
                'status': 'error',
                'message': 'This option already exists'
            }), 400
        
        # 新增選項
        options.append(new_value)
        dimension['options'] = options
        save_config(config)
        
        return jsonify({
            'status': 'success',
            'data': {
                'index': len(options) - 1,
                'option': new_value
            }
        }), 201
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ===================================================================
# DELETE - 刪除指定靈感詞
# ===================================================================

@wizard_options_bp.route('/wizard-options/dimension/<dimension_key>/<int:index>', methods=['DELETE'])
def delete_wizard_option(dimension_key, index):
    """
    刪除指定維度中的靈感詞
    Response: { status, data: { deleted } }
    """
    try:
        config = load_config()
        if config is None:
            return jsonify({
                'status': 'error',
                'message': 'Configuration file not found'
            }), 404
        
        # 檢查維度是否存在
        if dimension_key not in config.get('dimensions', {}):
            return jsonify({
                'status': 'error',
                'message': f'Dimension "{dimension_key}" not found'
            }), 404
        
        dimension = config['dimensions'][dimension_key]
        options = dimension.get('options', [])
        
        # 檢查索引範圍
        if index < 0 or index >= len(options):
            return jsonify({
                'status': 'error',
                'message': f'Index {index} out of range (0-{len(options)-1})'
            }), 400
        
        # 刪除選項
        deleted = options.pop(index)
        dimension['options'] = options
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
