# -*- coding: utf-8 -*-
"""
Routes Package - Blueprint 模組註冊
Local Insight v1.0
 
v1.0 Changes:
- notes 模組拆分為 notes/ 子目錄
"""

from flask import Blueprint

# Notes Blueprint (從子模組導入)
from .notes import notes_bp

# Tags Blueprint
tags_bp = Blueprint('tags', __name__, url_prefix='/api')

# Categories Blueprint
categories_bp = Blueprint('categories', __name__, url_prefix='/api')

# Export Blueprint
export_bp = Blueprint('export', __name__, url_prefix='/api')

# Upload Blueprint
upload_bp = Blueprint('upload', __name__, url_prefix='/api')

# Cleanup Blueprint (v0.8)
cleanup_bp = Blueprint('cleanup', __name__, url_prefix='/api')

# System Blueprint (v0.8.9 - VACUUM, Stats)
system_bp = Blueprint('system', __name__, url_prefix='/api')


def register_blueprints(app):
    """
    註冊所有 Blueprint 到 Flask App
    """
    # 導入路由模組 (避免循環導入)
    # notes 已在上方導入，其他模組仍需在此導入
    from . import tags, categories, export, upload, cleanup, system
    from .prompt_options import prompt_options_bp
    from .wizard_options import wizard_options_bp
    from .ai import ai_bp  # V2 Phase 3: AI Routes
    from .attachments import attachments_bp  # V2 Phase 3.4: Attachments
    from .search import search_bp  # V2 Phase 3.2: Semantic Search
    
    app.register_blueprint(notes_bp)
    app.register_blueprint(tags_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(cleanup_bp)
    app.register_blueprint(prompt_options_bp)
    app.register_blueprint(wizard_options_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(ai_bp, url_prefix='/api')  # V2 Phase 3
    app.register_blueprint(attachments_bp, url_prefix='/api')  # V2 Phase 3.4
    app.register_blueprint(search_bp, url_prefix='/api')  # V2 Phase 3.2

