# -*- coding: utf-8 -*-
"""
Attachments API Routes - Prism V2 Phase 3.4
Manage .md file attachments for notes (RAG-ready)
"""

import os
import re
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, send_file

from db import get_db

attachments_bp = Blueprint('attachments', __name__)

# Allowed file extensions for attachments
ALLOWED_EXTENSIONS = {'md', 'txt', 'markdown'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_attachments_dir():
    """Get or create attachments directory"""
    base_dir = current_app.root_path
    attachments_dir = os.path.join(base_dir, 'docs', 'attachments')
    os.makedirs(attachments_dir, exist_ok=True)
    return attachments_dir

def sanitize_filename(filename):
    """Sanitize filename to prevent path traversal"""
    # Remove path separators and dangerous characters
    filename = os.path.basename(filename)
    filename = re.sub(r'[^\w\-_\. ]', '', filename)
    return filename


@attachments_bp.route('/notes/<int:note_id>/attachments', methods=['GET'])
def get_note_attachments(note_id):
    """
    Get all attachments for a note
    
    Returns:
        {
            'status': 'success',
            'data': [
                {
                    'id': int,
                    'file_path': str,
                    'file_type': str,
                    'title': str,
                    'size_bytes': int,
                    'created_at': str
                }
            ]
        }
    """
    try:
        db = get_db()
        
        # Verify note exists
        note = db.execute('SELECT id FROM Notes WHERE id = ?', (note_id,)).fetchone()
        if not note:
            return jsonify({'status': 'error', 'message': 'Note not found'}), 404
        
        attachments = db.execute('''
            SELECT id, file_path, file_type, title, size_bytes, is_auto_extracted, created_at
            FROM Note_Attachments
            WHERE note_id = ?
            ORDER BY created_at DESC
        ''', (note_id,)).fetchall()
        
        result = []
        for att in attachments:
            result.append({
                'id': att['id'],
                'file_path': att['file_path'],
                'file_type': att['file_type'],
                'title': att['title'],
                'size_bytes': att['size_bytes'],
                'is_auto_extracted': bool(att['is_auto_extracted']),
                'created_at': att['created_at']
            })
        
        return jsonify({'status': 'success', 'data': result})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@attachments_bp.route('/notes/<int:note_id>/attachments', methods=['POST'])
def upload_attachment(note_id):
    """
    Upload attachment for a note
    
    Request:
        - file: The attachment file (multipart/form-data)
        - title: Optional display title
    
    Returns:
        {
            'status': 'success',
            'data': {
                'id': int,
                'file_path': str,
                'title': str,
                'size_bytes': int
            }
        }
    """
    try:
        db = get_db()
        
        # Verify note exists
        note = db.execute('SELECT id FROM Notes WHERE id = ?', (note_id,)).fetchone()
        if not note:
            return jsonify({'status': 'error', 'message': 'Note not found'}), 404
        
        # Check file
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'status': 'error', 
                'message': f'File type not allowed. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # Generate unique filename
        original_name = sanitize_filename(file.filename)
        base_name, ext = os.path.splitext(original_name)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{base_name}_{timestamp}{ext}"
        
        # Save file
        attachments_dir = get_attachments_dir()
        file_path = os.path.join(attachments_dir, unique_filename)
        file.save(file_path)
        
        # Get file size
        size_bytes = os.path.getsize(file_path)
        
        # Get title from form or use filename
        title = request.form.get('title', base_name)
        
        # Relative path for storage
        relative_path = f"docs/attachments/{unique_filename}"
        
        # Insert into database
        cursor = db.execute('''
            INSERT INTO Note_Attachments (note_id, file_path, file_type, title, size_bytes, is_auto_extracted, created_at)
            VALUES (?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP)
        ''', (note_id, relative_path, ext.lstrip('.'), title, size_bytes))
        db.commit()
        
        attachment_id = cursor.lastrowid
        
        return jsonify({
            'status': 'success',
            'data': {
                'id': attachment_id,
                'file_path': relative_path,
                'title': title,
                'size_bytes': size_bytes
            }
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@attachments_bp.route('/attachments/<int:attachment_id>', methods=['GET'])
def get_attachment_content(attachment_id):
    """
    Get attachment content
    
    Query params:
        - raw: If 'true', return raw file content; else return JSON with content
    
    Returns:
        Raw file content or JSON with content
    """
    try:
        db = get_db()
        
        attachment = db.execute('''
            SELECT id, file_path, file_type, title
            FROM Note_Attachments
            WHERE id = ?
        ''', (attachment_id,)).fetchone()
        
        if not attachment:
            return jsonify({'status': 'error', 'message': 'Attachment not found'}), 404
        
        # Get full path
        full_path = os.path.join(current_app.root_path, attachment['file_path'])
        
        if not os.path.exists(full_path):
            return jsonify({'status': 'error', 'message': 'File not found on disk'}), 404
        
        # Check if raw content requested
        if request.args.get('raw', 'false').lower() == 'true':
            return send_file(full_path, as_attachment=False)
        
        # Read and return as JSON
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({
            'status': 'success',
            'data': {
                'id': attachment['id'],
                'title': attachment['title'],
                'file_type': attachment['file_type'],
                'content': content
            }
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@attachments_bp.route('/attachments/<int:attachment_id>', methods=['DELETE'])
def delete_attachment(attachment_id):
    """
    Delete an attachment
    
    Returns:
        {
            'status': 'success'
        }
    """
    try:
        db = get_db()
        
        attachment = db.execute('''
            SELECT id, file_path
            FROM Note_Attachments
            WHERE id = ?
        ''', (attachment_id,)).fetchone()
        
        if not attachment:
            return jsonify({'status': 'error', 'message': 'Attachment not found'}), 404
        
        # Delete file from disk
        full_path = os.path.join(current_app.root_path, attachment['file_path'])
        if os.path.exists(full_path):
            os.remove(full_path)
        
        # Delete from database
        db.execute('DELETE FROM Note_Attachments WHERE id = ?', (attachment_id,))
        db.commit()
        
        return jsonify({'status': 'success'})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ===================================================================
# 3.4.4 自動分離 (Auto-Separation)
# ===================================================================

# Configuration
SEPARATION_THRESHOLD = 5000  # Characters
PREVIEW_LENGTH = 500  # Characters to keep in DB


def get_notes_dir():
    """Get or create notes directory for auto-separated content"""
    base_dir = current_app.root_path
    notes_dir = os.path.join(base_dir, 'docs', 'notes')
    os.makedirs(notes_dir, exist_ok=True)
    return notes_dir


@attachments_bp.route('/notes/<int:note_id>/check_separation', methods=['GET'])
def check_separation_needed(note_id):
    """
    Check if note content should be separated
    
    Returns:
        {
            'status': 'success',
            'data': {
                'should_separate': bool,
                'content_length': int,
                'threshold': int
            }
        }
    """
    try:
        db = get_db()
        
        note = db.execute('SELECT content FROM Notes WHERE id = ?', (note_id,)).fetchone()
        if not note:
            return jsonify({'status': 'error', 'message': 'Note not found'}), 404
        
        content = note['content'] or ''
        content_length = len(content)
        
        return jsonify({
            'status': 'success',
            'data': {
                'should_separate': content_length > SEPARATION_THRESHOLD,
                'content_length': content_length,
                'threshold': SEPARATION_THRESHOLD
            }
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@attachments_bp.route('/notes/<int:note_id>/separate', methods=['POST'])
def separate_content(note_id):
    """
    Separate long note content into attachment
    
    Request JSON (optional):
        {
            'preview_length': int  # Override default preview length
        }
    
    Returns:
        {
            'status': 'success',
            'data': {
                'attachment_id': int,
                'file_path': str,
                'original_length': int,
                'preview_length': int
            }
        }
    """
    try:
        db = get_db()
        
        # Get note content
        note = db.execute('''
            SELECT id, title, content 
            FROM Notes 
            WHERE id = ?
        ''', (note_id,)).fetchone()
        
        if not note:
            return jsonify({'status': 'error', 'message': 'Note not found'}), 404
        
        content = note['content'] or ''
        original_length = len(content)
        
        # Check if separation is needed
        if original_length <= SEPARATION_THRESHOLD:
            return jsonify({
                'status': 'info',
                'message': f'Content length ({original_length}) is under threshold ({SEPARATION_THRESHOLD}), no separation needed'
            })
        
        # Check if already separated - if so, update the existing attachment
        existing = db.execute('''
            SELECT id, file_path FROM Note_Attachments 
            WHERE note_id = ? AND is_auto_extracted = 1
        ''', (note_id,)).fetchone()
        
        # Get preview length from request or use default
        data = request.get_json(silent=True) or {}
        preview_len = data.get('preview_length', PREVIEW_LENGTH)
        
        # Create/update file with full content
        notes_dir = get_notes_dir()
        filename = f"note_{note_id}.md"
        file_path = os.path.join(notes_dir, filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        file_size = os.path.getsize(file_path)
        relative_path = f"docs/notes/{filename}"
        
        if existing:
            # Update existing attachment
            db.execute('''
                UPDATE Note_Attachments 
                SET size_bytes = ?, title = ?
                WHERE id = ?
            ''', (file_size, f"{note['title']} (完整內容)", existing['id']))
            attachment_id = existing['id']
        else:
            # Create new attachment record
            cursor = db.execute('''
                INSERT INTO Note_Attachments 
                (note_id, file_path, file_type, title, size_bytes, is_auto_extracted, created_at)
                VALUES (?, ?, 'md', ?, ?, 1, CURRENT_TIMESTAMP)
            ''', (note_id, relative_path, f"{note['title']} (完整內容)", file_size))
            attachment_id = cursor.lastrowid
        
        # Update note content with preview
        preview = content[:preview_len]
        if len(content) > preview_len:
            preview += '\n\n---\n📎 **[完整內容已分離為附件]**\n\n> 此筆記內容過長，已自動分離為附件。點擊附件可查看完整內容。'
        
        db.execute('''
            UPDATE Notes 
            SET content = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (preview, note_id))
        
        db.commit()
        
        return jsonify({
            'status': 'success',
            'message': '內容已成功分離為附件',
            'data': {
                'attachment_id': attachment_id,
                'file_path': relative_path,
                'original_length': original_length,
                'preview_length': len(preview)
            }
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@attachments_bp.route('/notes/<int:note_id>/restore', methods=['POST'])
def restore_content(note_id):
    """
    Restore separated content back to note (reverse of separate)
    
    Returns:
        {
            'status': 'success',
            'message': str
        }
    """
    try:
        db = get_db()
        
        # Find auto-extracted attachment
        attachment = db.execute('''
            SELECT id, file_path
            FROM Note_Attachments
            WHERE note_id = ? AND is_auto_extracted = 1
        ''', (note_id,)).fetchone()
        
        if not attachment:
            return jsonify({
                'status': 'error',
                'message': 'No auto-extracted attachment found for this note'
            }), 404
        
        # Read full content from file
        full_path = os.path.join(current_app.root_path, attachment['file_path'])
        
        if not os.path.exists(full_path):
            return jsonify({
                'status': 'error',
                'message': 'Attachment file not found on disk'
            }), 404
        
        with open(full_path, 'r', encoding='utf-8') as f:
            full_content = f.read()
        
        # Restore content to note
        db.execute('''
            UPDATE Notes 
            SET content = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (full_content, note_id))
        
        # Delete attachment file
        os.remove(full_path)
        
        # Delete attachment record
        db.execute('DELETE FROM Note_Attachments WHERE id = ?', (attachment['id'],))
        
        db.commit()
        
        return jsonify({
            'status': 'success',
            'message': '內容已成功還原至筆記'
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

