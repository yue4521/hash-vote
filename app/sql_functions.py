"""
SQL直接操作機能
データベースの初期化、メンテナンス、高度なクエリ実行を提供
"""
import sqlite3
import os
import shutil
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from .database import DATABASE_URL


class SQLManager:
    """SQLiteデータベースの直接操作を管理するクラス"""
    
    def __init__(self, db_path: str = None):
        """SQLManager初期化
        
        Args:
            db_path: データベースファイルパス（デフォルトは設定から取得）
        """
        if db_path is None:
            # DATABASE_URLから実際のファイルパスを抽出
            self.db_path = DATABASE_URL.replace("sqlite:///./", "")
        else:
            self.db_path = db_path
        
        self.project_root = Path(__file__).parent.parent
    
    def get_connection(self) -> sqlite3.Connection:
        """データベース接続を取得
        
        Returns:
            SQLite接続オブジェクト
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 辞書形式でレコードにアクセス可能
        return conn
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """SQLクエリを実行して結果を返す
        
        Args:
            query: 実行するSQL文
            params: クエリパラメータ
            
        Returns:
            クエリ結果のリスト（辞書形式）
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # SELECTクエリまたはPRAGMAの場合は結果を返す
            query_upper = query.strip().upper()
            if query_upper.startswith('SELECT') or query_upper.startswith('PRAGMA'):
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
            else:
                conn.commit()
                return []
    
    def execute_script(self, sql_script: str) -> None:
        """複数のSQL文を含むスクリプトを実行
        
        Args:
            sql_script: 実行するSQLスクリプト
        """
        with self.get_connection() as conn:
            conn.executescript(sql_script)
            conn.commit()
    
    def execute_file(self, sql_file_path: str) -> None:
        """SQLファイルを読み込んで実行
        
        Args:
            sql_file_path: SQLファイルのパス
        """
        file_path = Path(sql_file_path)
        if not file_path.is_absolute():
            file_path = self.project_root / sql_file_path
        
        if not file_path.exists():
            raise FileNotFoundError(f"SQLファイルが見つかりません: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as file:
            sql_script = file.read()
        
        self.execute_script(sql_script)
    
    def init_database(self) -> None:
        """データベースを初期化（全テーブル削除後再作成）"""
        init_sql = """
        -- 既存テーブルを削除
        DROP TABLE IF EXISTS blocks;
        
        -- blocksテーブルを作成
        CREATE TABLE blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            poll_id VARCHAR NOT NULL,
            voter_hash VARCHAR NOT NULL,
            choice VARCHAR NOT NULL,
            timestamp DATETIME NOT NULL,
            prev_hash VARCHAR NOT NULL,
            nonce INTEGER NOT NULL,
            block_hash VARCHAR NOT NULL UNIQUE,
            CONSTRAINT unique_vote UNIQUE (poll_id, voter_hash)
        );
        
        -- インデックス作成
        CREATE INDEX ix_blocks_poll_id ON blocks (poll_id);
        CREATE INDEX ix_blocks_block_hash ON blocks (block_hash);
        CREATE INDEX ix_blocks_timestamp ON blocks (timestamp);
        """
        
        self.execute_script(init_sql)
    
    def backup_database(self, backup_path: str = None) -> str:
        """データベースをバックアップ
        
        Args:
            backup_path: バックアップファイルパス（未指定時は自動生成）
            
        Returns:
            作成されたバックアップファイルのパス
        """
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"hashvote_backup_{timestamp}.db"
        
        shutil.copy2(self.db_path, backup_path)
        return backup_path
    
    def restore_database(self, backup_path: str) -> None:
        """バックアップからデータベースを復元
        
        Args:
            backup_path: バックアップファイルのパス
        """
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"バックアップファイルが見つかりません: {backup_path}")
        
        shutil.copy2(backup_path, self.db_path)
    
    def get_table_info(self) -> Dict[str, List[Dict[str, Any]]]:
        """テーブル情報を取得
        
        Returns:
            テーブル名をキーとした列情報の辞書
        """
        tables_query = "SELECT name FROM sqlite_master WHERE type='table'"
        tables = self.execute_query(tables_query)
        
        table_info = {}
        for table in tables:
            table_name = table['name']
            columns_query = f"PRAGMA table_info({table_name})"
            columns = self.execute_query(columns_query)
            table_info[table_name] = columns
        
        return table_info
    
    def get_database_stats(self) -> Dict[str, Any]:
        """データベース統計情報を取得
        
        Returns:
            統計情報の辞書
        """
        stats = {}
        
        # ファイルサイズ
        stats['file_size_bytes'] = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        stats['file_size_mb'] = round(stats['file_size_bytes'] / (1024 * 1024), 2)
        
        # テーブル統計
        table_stats = {}
        table_info = self.get_table_info()
        
        for table_name in table_info.keys():
            count_query = f"SELECT COUNT(*) as count FROM {table_name}"
            result = self.execute_query(count_query)
            table_stats[table_name] = result[0]['count'] if result else 0
        
        stats['table_counts'] = table_stats
        
        # ブロック関連統計（blocksテーブルが存在する場合）
        if 'blocks' in table_info:
            # 投票数の多い順にpoll_idを取得
            poll_stats_query = """
            SELECT poll_id, COUNT(*) as vote_count 
            FROM blocks 
            GROUP BY poll_id 
            ORDER BY vote_count DESC 
            LIMIT 5
            """
            stats['top_polls'] = self.execute_query(poll_stats_query)
            
            # 最新の投票
            latest_vote_query = """
            SELECT poll_id, choice, timestamp 
            FROM blocks 
            ORDER BY timestamp DESC 
            LIMIT 1
            """
            latest_votes = self.execute_query(latest_vote_query)
            stats['latest_vote'] = latest_votes[0] if latest_votes else None
        
        return stats
    
    def verify_blockchain_integrity(self) -> Tuple[bool, List[str]]:
        """ブロックチェーンの整合性を検証
        
        Returns:
            (整合性OK, エラーメッセージリスト)のタプル
        """
        errors = []
        
        # ブロックを順番に取得
        blocks_query = "SELECT * FROM blocks ORDER BY id"
        blocks = self.execute_query(blocks_query)
        
        if not blocks:
            return True, []
        
        # 各ブロックの検証
        prev_hash_map = {}  # poll_id -> 最新ブロックハッシュ
        
        for block in blocks:
            poll_id = block['poll_id']
            current_hash = block['block_hash']
            prev_hash = block['prev_hash']
            
            # 最初のブロック（前ハッシュが全ゼロ）でない場合
            if prev_hash != "0" * 64:
                if poll_id not in prev_hash_map:
                    errors.append(f"ブロックID {block['id']}: 前ブロックが存在しません")
                elif prev_hash_map[poll_id] != prev_hash:
                    errors.append(f"ブロックID {block['id']}: 前ブロックハッシュが不正です")
            
            # 現在のブロックハッシュを記録
            prev_hash_map[poll_id] = current_hash
        
        # 重複投票の確認
        duplicate_query = """
        SELECT poll_id, voter_hash, COUNT(*) as count 
        FROM blocks 
        GROUP BY poll_id, voter_hash 
        HAVING COUNT(*) > 1
        """
        duplicates = self.execute_query(duplicate_query)
        
        if duplicates:
            for dup in duplicates:
                errors.append(f"重複投票: poll_id={dup['poll_id']}, voter_hash={dup['voter_hash'][:16]}...")
        
        return len(errors) == 0, errors
    
    def get_vote_statistics(self, poll_id: str = None) -> Dict[str, Any]:
        """投票統計を取得
        
        Args:
            poll_id: 特定の投票ID（未指定時は全体統計）
            
        Returns:
            統計情報の辞書
        """
        stats = {}
        
        # ベースクエリ
        where_clause = f"WHERE poll_id = '{poll_id}'" if poll_id else ""
        
        # 総投票数
        total_votes_query = f"SELECT COUNT(*) as total FROM blocks {where_clause}"
        total_result = self.execute_query(total_votes_query)
        stats['total_votes'] = total_result[0]['total'] if total_result else 0
        
        # 選択肢別投票数
        choice_stats_query = f"""
        SELECT choice, COUNT(*) as count, 
               ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM blocks {where_clause}), 2) as percentage
        FROM blocks {where_clause}
        GROUP BY choice 
        ORDER BY count DESC
        """
        stats['choice_distribution'] = self.execute_query(choice_stats_query)
        
        # 時系列統計
        timeline_query = f"""
        SELECT DATE(timestamp) as vote_date, COUNT(*) as daily_votes
        FROM blocks {where_clause}
        GROUP BY DATE(timestamp)
        ORDER BY vote_date
        """
        stats['daily_timeline'] = self.execute_query(timeline_query)
        
        # poll_id別統計（全体統計の場合のみ）
        if poll_id is None:
            poll_stats_query = """
            SELECT poll_id, COUNT(*) as votes, 
                   MIN(timestamp) as first_vote, 
                   MAX(timestamp) as last_vote
            FROM blocks 
            GROUP BY poll_id 
            ORDER BY votes DESC
            """
            stats['poll_distribution'] = self.execute_query(poll_stats_query)
        
        return stats


def get_sql_manager() -> SQLManager:
    """SQLManagerのインスタンスを取得
    
    Returns:
        SQLManagerインスタンス
    """
    return SQLManager()