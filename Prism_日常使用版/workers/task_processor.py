#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI_Tasks Worker - Independent Task Processor

Phase 0 Step 2: 實作真正的任務隊列
取代 ThreadPoolExecutor，消化 AI_Tasks 表中的待處理任務。

優勢:
- 任務持久化 (伺服器崩潰不丟失)
- 支援優雅中斷 (Graceful Shutdown)
- 失敗重試機制 (max 3 retries)

用法:
    python workers/task_processor.py          # 單次執行模式
    python workers/task_processor.py --daemon  # 常駐模式
"""

import sys
import signal
import time
import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config


class TaskProcessor:
    """AI 任務處理器"""

    def __init__(self):
        self.running = True
        self.db_path = Config.DATABASE

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """處理中斷信號"""
        print(f"\n[Worker] 收到信號 {signum}，正在優雅退出...")
        self.running = False

    def process_tasks(self, once=False):
        """
        處理待處理的任務

        Args:
            once: True = 單次執行模式 (處理所有待處理任務後退出)
                  False = 常駐模式 (持續監控並處理任務)
        """
        print(f"[Worker] 啟動 AI_Tasks 處理器 (模式: {'單次' if once else '常駐'})")

        while self.running:
            conn = None
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row

                # 獲取待處理的任務 (FIFO: 最舊的優先)
                cursor = conn.execute("""
                    SELECT id, task_type, payload, retry_count
                    FROM AI_Tasks
                    WHERE status = 'pending'
                    ORDER BY created_at ASC
                    LIMIT 10
                """)

                tasks = cursor.fetchall()

                if not tasks:
                    if once:
                        print("[Worker] 沒有待處理任務，退出")
                        break
                    else:
                        # 常駐模式: 等待 30 秒後再檢查
                        time.sleep(30)
                        continue

                print(f"[Worker] 發現 {len(tasks)} 個待處理任務")

                for task in tasks:
                    if not self.running:
                        break

                    self._process_single_task(conn, task)

                if once:
                    # 單次模式: 處理完所有任務後退出
                    break

            except Exception as e:
                print(f"[Worker] 錯誤: {e}")

            finally:
                if conn:
                    conn.close()

                if not once and self.running:
                    # 常駐模式: 短暫等待後繼續
                    time.sleep(5)

        print("[Worker] 已停止")

    def _process_single_task(self, conn, task):
        """處理單個任務"""
        task_id = task['id']
        task_type = task['task_type']
        payload = json.loads(task['payload'])
        retry_count = task['retry_count']

        print(f"[Worker] 處理任務 #{task_id} ({task_type})")

        # 標記為處理中
        conn.execute("""
            UPDATE AI_Tasks
            SET status = 'processing', updated_at = datetime('now')
            WHERE id = ?
        """, (task_id,))
        conn.commit()

        try:
            # 根據任務類型分發
            if task_type == 'embedding':
                result = self._do_embedding(payload)
            else:
                raise ValueError(f"未知的任務類型: {task_type}")

            # 標記為完成
            conn.execute("""
                UPDATE AI_Tasks
                SET status = 'completed',
                    result = ?,
                    updated_at = datetime('now')
                WHERE id = ?
            """, (json.dumps(result), task_id))
            conn.commit()

            print(f"[Worker] 任務 #{task_id} 完成")

        except Exception as e:
            error_msg = str(e)
            print(f"[Worker] 任務 #{task_id} 失敗: {error_msg}")

            # 失敗重試邏輯
            if retry_count < 3:
                # 重置為 pending，增加重試計數
                conn.execute("""
                    UPDATE AI_Tasks
                    SET status = 'pending',
                        retry_count = retry_count + 1,
                        result = ?,
                        updated_at = datetime('now')
                    WHERE id = ?
                """, (json.dumps({'error': error_msg}), task_id))
                print(f"[Worker] 任務 #{task_id} 將重試 (#{retry_count + 1}/3)")
            else:
                # 超過重試次數，標記為 failed
                conn.execute("""
                    UPDATE AI_Tasks
                    SET status = 'failed',
                        result = ?,
                        updated_at = datetime('now')
                    WHERE id = ?
                """, (json.dumps({'error': error_msg}), task_id))
                print(f"[Worker] 任務 #{task_id} 永久失敗 (超過重試次數)")

            conn.commit()

    def _do_embedding(self, payload):
        """
        執行 Embedding 任務

        Args:
            payload: {'note_id': int, 'title': str, 'content': str}

        Returns:
            {'success': True, 'note_id': int}
        """
        note_id = payload['note_id']
        title = payload.get('title', '')
        content = payload.get('content', '')

        # Import embedding service
        from services.embedding_service import is_model_available, text_to_embedding, embedding_to_blob

        if not is_model_available():
            raise RuntimeError("Embedding model not available")

        # 計算 content_hash (用於增量更新)
        text = f"{title}\n{content}"
        content_hash = hashlib.md5(text.encode('utf-8')).hexdigest()

        # 獨立資料庫連線
        conn = sqlite3.connect(self.db_path)

        try:
            # 檢查是否需要更新 (content_hash 比對)
            cursor = conn.execute(
                'SELECT content_hash FROM Embeddings WHERE resource_type = ? AND resource_id = ?',
                ('note', note_id)
            )
            existing = cursor.fetchone()

            if existing and existing[0] == content_hash:
                return {'success': True, 'note_id': note_id, 'skipped': True, 'reason': 'content unchanged'}

            # 產生新 Embedding
            embedding = text_to_embedding(text)
            if embedding is None:
                raise RuntimeError("Failed to generate embedding")

            blob = embedding_to_blob(embedding)

            # 更新或插入 Embeddings 表
            conn.execute('''
                INSERT OR REPLACE INTO Embeddings
                (resource_type, resource_id, chunk_index, model_name, vector, content_hash, dimensions, created_at)
                VALUES (?, ?, 0, 'all-MiniLM-L6-v2', ?, ?, 384, datetime('now'))
            ''', ('note', note_id, blob, content_hash))

            # 同時更新 Notes.embedding_status (如果欄位存在)
            try:
                conn.execute(
                    'UPDATE Notes SET embedding_status = ? WHERE id = ?',
                    ('indexed', note_id)
                )
            except sqlite3.OperationalError:
                pass  # 欄位不存在，忽略

            conn.commit()

            return {'success': True, 'note_id': note_id, 'content_hash': content_hash}

        finally:
            conn.close()


def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description='AI_Tasks Worker - Process queued AI tasks')
    parser.add_argument('--daemon', action='store_true', help='Run in daemon mode (continuous processing)')
    args = parser.parse_args()

    processor = TaskProcessor()

    try:
        processor.process_tasks(once=not args.daemon)
    except KeyboardInterrupt:
        print("\n[Worker] 收到中斷信號，退出")
    except Exception as e:
        print(f"[Worker] 嚴重錯誤: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
