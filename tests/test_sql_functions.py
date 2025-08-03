"""
SQL機能のテスト
app/sql_functions.pyの機能をテストする
"""
import pytest
import tempfile
import os
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from app.sql_functions import SQLManager
from app.models import Block


class TestSQLManager:
    """SQLManagerクラスのテスト"""
    
    @pytest.fixture
    def temp_db(self):
        """テスト用の一時データベースファイルを作成"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        yield temp_file.name
        os.unlink(temp_file.name)
    
    @pytest.fixture
    def sql_manager(self, temp_db):
        """テスト用のSQLManagerインスタンスを作成"""
        return SQLManager(temp_db)
    
    def test_init_database(self, sql_manager):
        """データベース初期化のテスト"""
        # 初期化実行
        sql_manager.init_database()
        
        # テーブルが作成されているかチェック
        result = sql_manager.execute_query(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='blocks'"
        )
        assert len(result) == 1
        assert result[0]['name'] == 'blocks'
        
        # インデックスが作成されているかチェック
        result = sql_manager.execute_query(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='blocks'"
        )
        assert len(result) >= 4  # 少なくとも4つのインデックスが作成される
    
    def test_execute_query_select(self, sql_manager):
        """SELECTクエリ実行のテスト"""
        sql_manager.init_database()
        
        # データを挿入
        sql_manager.execute_query(
            """INSERT INTO blocks 
               (poll_id, voter_hash, choice, timestamp, prev_hash, nonce, block_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ('test_poll', 'voter123', 'yes', datetime.now(timezone.utc), 
             '0'*64, 12345, 'block123')
        )
        
        # データを取得
        result = sql_manager.execute_query("SELECT * FROM blocks")
        assert len(result) == 1
        assert result[0]['poll_id'] == 'test_poll'
        assert result[0]['choice'] == 'yes'
    
    def test_execute_query_insert(self, sql_manager):
        """INSERTクエリ実行のテスト"""
        sql_manager.init_database()
        
        # データ挿入
        result = sql_manager.execute_query(
            """INSERT INTO blocks 
               (poll_id, voter_hash, choice, timestamp, prev_hash, nonce, block_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ('test_poll', 'voter123', 'yes', datetime.now(timezone.utc), 
             '0'*64, 12345, 'block123')
        )
        
        # INSERTは空のリストを返す
        assert result == []
        
        # データが実際に挿入されたかチェック
        count_result = sql_manager.execute_query("SELECT COUNT(*) as count FROM blocks")
        assert count_result[0]['count'] == 1
    
    def test_execute_script(self, sql_manager):
        """SQLスクリプト実行のテスト"""
        script = """
        CREATE TABLE test_table (id INTEGER, name TEXT);
        INSERT INTO test_table VALUES (1, 'test1');
        INSERT INTO test_table VALUES (2, 'test2');
        """
        
        sql_manager.execute_script(script)
        
        # データが挿入されたかチェック
        result = sql_manager.execute_query("SELECT * FROM test_table ORDER BY id")
        assert len(result) == 2
        assert result[0]['name'] == 'test1'
        assert result[1]['name'] == 'test2'
    
    def test_get_table_info(self, sql_manager):
        """テーブル情報取得のテスト"""
        sql_manager.init_database()
        
        table_info = sql_manager.get_table_info()
        
        # blocksテーブルの情報が含まれているかチェック
        assert 'blocks' in table_info
        blocks_columns = table_info['blocks']
        
        # 期待される列が存在するかチェック
        column_names = [col['name'] for col in blocks_columns]
        expected_columns = ['id', 'poll_id', 'voter_hash', 'choice', 
                          'timestamp', 'prev_hash', 'nonce', 'block_hash']
        for col in expected_columns:
            assert col in column_names
    
    def test_get_database_stats(self, sql_manager):
        """データベース統計取得のテスト"""
        sql_manager.init_database()
        
        # テストデータ挿入
        test_data = [
            ('poll1', 'voter1', 'yes', datetime.now(timezone.utc), '0'*64, 123, 'hash1'),
            ('poll1', 'voter2', 'no', datetime.now(timezone.utc), 'hash1', 456, 'hash2'),
            ('poll2', 'voter3', 'maybe', datetime.now(timezone.utc), '0'*64, 789, 'hash3'),
        ]
        
        for data in test_data:
            sql_manager.execute_query(
                """INSERT INTO blocks 
                   (poll_id, voter_hash, choice, timestamp, prev_hash, nonce, block_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                data
            )
        
        stats = sql_manager.get_database_stats()
        
        # 基本統計をチェック
        assert 'file_size_bytes' in stats
        assert 'file_size_mb' in stats
        assert 'table_counts' in stats
        assert stats['table_counts']['blocks'] == 3
        
        # top_polls情報をチェック
        assert 'top_polls' in stats
        assert len(stats['top_polls']) > 0
        
        # latest_vote情報をチェック
        assert 'latest_vote' in stats
        assert stats['latest_vote'] is not None
    
    def test_backup_database(self, sql_manager, temp_db):
        """データベースバックアップのテスト"""
        sql_manager.init_database()
        
        # テストデータ挿入
        sql_manager.execute_query(
            """INSERT INTO blocks 
               (poll_id, voter_hash, choice, timestamp, prev_hash, nonce, block_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ('test_poll', 'voter123', 'yes', datetime.now(timezone.utc), 
             '0'*64, 12345, 'block123')
        )
        
        # バックアップ作成
        backup_path = sql_manager.backup_database()
        
        try:
            # バックアップファイルが存在するかチェック
            assert os.path.exists(backup_path)
            
            # バックアップから新しいSQLManagerを作成してデータを確認
            backup_manager = SQLManager(backup_path)
            result = backup_manager.execute_query("SELECT COUNT(*) as count FROM blocks")
            assert result[0]['count'] == 1
        
        finally:
            # バックアップファイルを削除
            if os.path.exists(backup_path):
                os.unlink(backup_path)
    
    def test_verify_blockchain_integrity_valid(self, sql_manager):
        """ブロックチェーン整合性検証のテスト（正常ケース）"""
        sql_manager.init_database()
        
        # 正常なブロックチェーンデータを挿入
        now = datetime.now(timezone.utc)
        test_data = [
            ('poll1', 'voter1', 'yes', now, '0'*64, 123, 'hash1'),
            ('poll1', 'voter2', 'no', now, 'hash1', 456, 'hash2'),
        ]
        
        for data in test_data:
            sql_manager.execute_query(
                """INSERT INTO blocks 
                   (poll_id, voter_hash, choice, timestamp, prev_hash, nonce, block_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                data
            )
        
        is_valid, errors = sql_manager.verify_blockchain_integrity()
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_verify_blockchain_integrity_invalid(self, sql_manager):
        """ブロックチェーン整合性検証のテスト（異常ケース）"""
        sql_manager.init_database()
        
        # 不正なブロックチェーンデータを挿入（前ハッシュが一致しない）
        now = datetime.now(timezone.utc)
        test_data = [
            ('poll1', 'voter1', 'yes', now, '0'*64, 123, 'hash1'),
            ('poll1', 'voter2', 'no', now, 'invalid_hash', 456, 'hash2'),  # 不正な前ハッシュ
        ]
        
        for data in test_data:
            sql_manager.execute_query(
                """INSERT INTO blocks 
                   (poll_id, voter_hash, choice, timestamp, prev_hash, nonce, block_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                data
            )
        
        is_valid, errors = sql_manager.verify_blockchain_integrity()
        
        assert is_valid is False
        assert len(errors) > 0
    
    def test_get_vote_statistics_general(self, sql_manager):
        """投票統計取得のテスト（全体統計）"""
        sql_manager.init_database()
        
        # テストデータ挿入
        now = datetime.now(timezone.utc)
        test_data = [
            ('poll1', 'voter1', 'yes', now, '0'*64, 123, 'hash1'),
            ('poll1', 'voter2', 'yes', now, 'hash1', 456, 'hash2'),
            ('poll1', 'voter3', 'no', now, 'hash2', 789, 'hash3'),
            ('poll2', 'voter4', 'maybe', now, '0'*64, 111, 'hash4'),
        ]
        
        for data in test_data:
            sql_manager.execute_query(
                """INSERT INTO blocks 
                   (poll_id, voter_hash, choice, timestamp, prev_hash, nonce, block_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                data
            )
        
        stats = sql_manager.get_vote_statistics()
        
        # 基本統計をチェック
        assert stats['total_votes'] == 4
        
        # 選択肢分布をチェック
        choice_dist = stats['choice_distribution']
        assert len(choice_dist) == 3  # yes, no, maybe
        
        # yesが最多（2票）であることをチェック
        yes_votes = next(item for item in choice_dist if item['choice'] == 'yes')
        assert yes_votes['count'] == 2
        assert yes_votes['percentage'] == 50.0
    
    def test_get_vote_statistics_specific_poll(self, sql_manager):
        """投票統計取得のテスト（特定投票ID）"""
        sql_manager.init_database()
        
        # テストデータ挿入
        now = datetime.now(timezone.utc)
        test_data = [
            ('poll1', 'voter1', 'yes', now, '0'*64, 123, 'hash1'),
            ('poll1', 'voter2', 'no', now, 'hash1', 456, 'hash2'),
            ('poll2', 'voter3', 'maybe', now, '0'*64, 789, 'hash3'),
        ]
        
        for data in test_data:
            sql_manager.execute_query(
                """INSERT INTO blocks 
                   (poll_id, voter_hash, choice, timestamp, prev_hash, nonce, block_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                data
            )
        
        # poll1の統計を取得
        stats = sql_manager.get_vote_statistics('poll1')
        
        assert stats['total_votes'] == 2
        assert len(stats['choice_distribution']) == 2  # yes, no
    
    def test_execute_file_not_found(self, sql_manager):
        """存在しないSQLファイル実行のテスト"""
        with pytest.raises(FileNotFoundError):
            sql_manager.execute_file('nonexistent.sql')
    
    @patch('builtins.open')
    def test_execute_file_success(self, mock_open, sql_manager):
        """SQLファイル実行成功のテスト"""
        # ファイル内容をモック
        mock_open.return_value.__enter__.return_value.read.return_value = """
        CREATE TABLE test_file (id INTEGER);
        INSERT INTO test_file VALUES (1);
        """
        
        # パス存在チェックをモック
        with patch('pathlib.Path.exists', return_value=True):
            sql_manager.execute_file('test.sql')
        
        # テーブルが作成されたかチェック
        result = sql_manager.execute_query(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='test_file'"
        )
        assert len(result) == 1
    
    def test_restore_database_not_found(self, sql_manager):
        """存在しないバックアップファイルからの復元テスト"""
        with pytest.raises(FileNotFoundError):
            sql_manager.restore_database('nonexistent_backup.db')
    
    def test_restore_database_success(self, sql_manager, temp_db):
        """データベース復元成功のテスト"""
        # 元のデータベースを初期化してデータを挿入
        sql_manager.init_database()
        sql_manager.execute_query(
            """INSERT INTO blocks 
               (poll_id, voter_hash, choice, timestamp, prev_hash, nonce, block_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ('original_poll', 'voter123', 'yes', datetime.now(timezone.utc), 
             '0'*64, 12345, 'original_hash')
        )
        
        # バックアップ作成
        backup_path = sql_manager.backup_database()
        
        try:
            # データベースを初期化して空にする
            sql_manager.init_database()
            result = sql_manager.execute_query("SELECT COUNT(*) as count FROM blocks")
            assert result[0]['count'] == 0
            
            # バックアップから復元
            sql_manager.restore_database(backup_path)
            
            # データが復元されたかチェック
            result = sql_manager.execute_query("SELECT * FROM blocks")
            assert len(result) == 1
            assert result[0]['poll_id'] == 'original_poll'
        
        finally:
            # バックアップファイルを削除
            if os.path.exists(backup_path):
                os.unlink(backup_path)


class TestSQLManagerIntegration:
    """SQLManagerの統合テスト"""
    
    @pytest.fixture
    def temp_db(self):
        """テスト用の一時データベースファイルを作成"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        yield temp_file.name
        os.unlink(temp_file.name)
    
    def test_full_workflow(self, temp_db):
        """完全なワークフローのテスト"""
        sql_manager = SQLManager(temp_db)
        
        # 1. データベース初期化
        sql_manager.init_database()
        
        # 2. テストデータ挿入
        now = datetime.now(timezone.utc)
        test_votes = [
            ('election_2024', 'voter_alice', 'candidate_a', now, '0'*64, 100000, 'hash_001'),
            ('election_2024', 'voter_bob', 'candidate_b', now, 'hash_001', 250000, 'hash_002'),
            ('election_2024', 'voter_charlie', 'candidate_a', now, 'hash_002', 180000, 'hash_003'),
        ]
        
        for vote in test_votes:
            sql_manager.execute_query(
                """INSERT INTO blocks 
                   (poll_id, voter_hash, choice, timestamp, prev_hash, nonce, block_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                vote
            )
        
        # 3. 統計情報取得
        stats = sql_manager.get_database_stats()
        assert stats['table_counts']['blocks'] == 3
        
        # 4. 投票統計取得
        vote_stats = sql_manager.get_vote_statistics('election_2024')
        assert vote_stats['total_votes'] == 3
        
        # 5. 整合性チェック
        is_valid, errors = sql_manager.verify_blockchain_integrity()
        assert is_valid is True
        assert len(errors) == 0
        
        # 6. バックアップとリストア
        backup_path = sql_manager.backup_database()
        
        try:
            # データベースを空にして復元
            sql_manager.init_database()
            sql_manager.restore_database(backup_path)
            
            # データが復元されたかチェック
            result = sql_manager.execute_query("SELECT COUNT(*) as count FROM blocks")
            assert result[0]['count'] == 3
        
        finally:
            if os.path.exists(backup_path):
                os.unlink(backup_path)


def test_get_sql_manager():
    """get_sql_manager関数のテスト"""
    from app.sql_functions import get_sql_manager
    
    manager = get_sql_manager()
    assert isinstance(manager, SQLManager)
    assert manager.db_path == "hashvote.db"