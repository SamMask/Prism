# -*- coding: utf-8 -*-
"""
Notes API Module - Blueprint & Sub-module Registration
Local Insight v1.0

模組拆分結構:
- crud.py: GET/POST/PUT/DELETE 基本操作
- actions.py: pin/archive/duplicate/reorder 動作
- history.py: 版本歷史相關
- batch.py: 批量操作
"""

from flask import Blueprint

# Notes Blueprint
notes_bp = Blueprint('notes', __name__, url_prefix='/api')

# 導入所有子模組 (注意順序，避免循環導入)
from . import crud
from . import actions
from . import history
from . import batch
from . import export
from . import import_


