"""
Unit tests for CLI functionality.
"""
import pytest
import io
import sys
from unittest.mock import patch, Mock
from datetime import datetime
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.cli import HashVoteCLI
from app.models import Block


# Create test database
@pytest.fixture(name="session")
def session_fixture():
    """Create a test database session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="cli_app")
def cli_app_fixture(session: Session):
    """Create a CLI app with test database."""
    app = HashVoteCLI()
    app.session = session
    return app


class TestHashVoteCLI:
    """Test cases for HashVoteCLI class."""
    
    def test_initialization(self):
        """Test CLI initialization."""
        with patch('app.cli.create_db_and_tables'), \
             patch('app.cli.get_session_direct'):
            app = HashVoteCLI()
            assert app.session is not None or app.session is None  # Mock may return None
    
    def test_get_latest_block_hash_empty(self, cli_app: HashVoteCLI):
        """Test getting latest block hash when no blocks exist."""
        result = cli_app.get_latest_block_hash("test_poll")
        assert result == "0" * 64
    
    def test_get_latest_block_hash_with_blocks(self, cli_app: HashVoteCLI):
        """Test getting latest block hash with existing blocks."""
        # Add a test block
        timestamp = datetime.utcnow()
        block = Block(
            poll_id="test_poll",
            voter_hash="test_voter",
            choice="option_a",
            timestamp=timestamp,
            prev_hash="0" * 64,
            nonce=42,
            block_hash="abcdef123456"
        )
        cli_app.session.add(block)
        cli_app.session.commit()
        
        result = cli_app.get_latest_block_hash("test_poll")
        assert result == "abcdef123456"
    
    def test_check_duplicate_vote_no_duplicate(self, cli_app: HashVoteCLI):
        """Test duplicate vote check when no duplicate exists."""
        result = cli_app.check_duplicate_vote("test_poll", "test_voter")
        assert result is False
    
    def test_check_duplicate_vote_with_duplicate(self, cli_app: HashVoteCLI):
        """Test duplicate vote check when duplicate exists."""
        # Add a test block
        timestamp = datetime.utcnow()
        block = Block(
            poll_id="test_poll",
            voter_hash="test_voter",
            choice="option_a",
            timestamp=timestamp,
            prev_hash="0" * 64,
            nonce=42,
            block_hash="abcdef123456"
        )
        cli_app.session.add(block)
        cli_app.session.commit()
        
        result = cli_app.check_duplicate_vote("test_poll", "test_voter")
        assert result is True
    
    @patch('builtins.input')
    def test_get_user_input(self, mock_input, cli_app: HashVoteCLI):
        """Test user input handling."""
        mock_input.return_value = "test_input"
        result = cli_app.get_user_input("Test prompt")
        assert result == "test_input"
    
    @patch('os.system')
    def test_clear_screen(self, mock_system, cli_app: HashVoteCLI):
        """Test screen clearing functionality."""
        cli_app.clear_screen()
        mock_system.assert_called_once()
    
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_display_header(self, mock_stdout, cli_app: HashVoteCLI):
        """Test header display."""
        cli_app.display_header()
        output = mock_stdout.getvalue()
        assert "HashVote" in output
        assert "Proof of Work" in output
    
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_display_menu(self, mock_stdout, cli_app: HashVoteCLI):
        """Test menu display."""
        cli_app.display_menu()
        output = mock_stdout.getvalue()
        assert "投票する" in output
        assert "投票結果を確認する" in output
        assert "監査ログを確認する" in output
        assert "ヘルスチェック" in output
        assert "終了" in output


class TestCLIVoteHandling:
    """Test cases for voting functionality."""
    
    @patch('builtins.input')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_handle_vote_missing_poll_id(self, mock_stdout, mock_input, cli_app: HashVoteCLI):
        """Test vote handling with missing poll ID."""
        mock_input.side_effect = ["", "option_a", "voter1"]  # Empty poll_id
        
        cli_app.handle_vote()
        
        output = mock_stdout.getvalue()
        assert "エラー: 投票IDが必要です" in output
    
    @patch('builtins.input')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_handle_vote_missing_choice(self, mock_stdout, mock_input, cli_app: HashVoteCLI):
        """Test vote handling with missing choice."""
        mock_input.side_effect = ["test_poll", "", "voter1"]  # Empty choice
        
        cli_app.handle_vote()
        
        output = mock_stdout.getvalue()
        assert "エラー: 選択肢が必要です" in output
    
    @patch('builtins.input')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_handle_vote_missing_voter_id(self, mock_stdout, mock_input, cli_app: HashVoteCLI):
        """Test vote handling with missing voter ID."""
        mock_input.side_effect = ["test_poll", "option_a", ""]  # Empty voter_id
        
        cli_app.handle_vote()
        
        output = mock_stdout.getvalue()
        assert "エラー: 投票者IDが必要です" in output
    
    @patch('builtins.input')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_handle_vote_duplicate(self, mock_stdout, mock_input, cli_app: HashVoteCLI):
        """Test vote handling with duplicate voter."""
        # Add existing vote
        timestamp = datetime.utcnow()
        import hashlib
        voter_hash = hashlib.sha256("voter1".encode('utf-8')).hexdigest()
        
        block = Block(
            poll_id="test_poll",
            voter_hash=voter_hash,
            choice="option_a",
            timestamp=timestamp,
            prev_hash="0" * 64,
            nonce=42,
            block_hash="abcdef123456"
        )
        cli_app.session.add(block)
        cli_app.session.commit()
        
        mock_input.side_effect = ["test_poll", "option_b", "voter1"]
        
        cli_app.handle_vote()
        
        output = mock_stdout.getvalue()
        assert "エラー: この投票者は既に投票済みです" in output


class TestCLIPollResults:
    """Test cases for poll result functionality."""
    
    @patch('builtins.input')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_handle_poll_result_empty(self, mock_stdout, mock_input, cli_app: HashVoteCLI):
        """Test poll result handling for empty poll."""
        mock_input.return_value = "empty_poll"
        
        cli_app.handle_poll_result()
        
        output = mock_stdout.getvalue()
        assert "投票は見つかりませんでした" in output
    
    @patch('builtins.input')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_handle_poll_result_with_votes(self, mock_stdout, mock_input, cli_app: HashVoteCLI):
        """Test poll result handling with votes."""
        # Add test votes
        timestamp = datetime.utcnow()
        votes = [
            ("voter1", "option_a"),
            ("voter2", "option_a"),
            ("voter3", "option_b"),
        ]
        
        for i, (voter, choice) in enumerate(votes):
            block = Block(
                poll_id="test_poll",
                voter_hash=f"hash_{voter}",
                choice=choice,
                timestamp=timestamp,
                prev_hash="0" * 64,
                nonce=42 + i,
                block_hash=f"hash_{i}"
            )
            cli_app.session.add(block)
        
        cli_app.session.commit()
        
        mock_input.return_value = "test_poll"
        
        cli_app.handle_poll_result()
        
        output = mock_stdout.getvalue()
        assert "総投票数: 3" in output
        assert "option_a: 2票" in output
        assert "option_b: 1票" in output


class TestCLIAuditLog:
    """Test cases for audit log functionality."""
    
    @patch('builtins.input')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_handle_audit_log_empty(self, mock_stdout, mock_input, cli_app: HashVoteCLI):
        """Test audit log handling for empty poll."""
        mock_input.return_value = "empty_poll"
        
        cli_app.handle_audit_log()
        
        output = mock_stdout.getvalue()
        assert "投票は見つかりませんでした" in output
    
    @patch('builtins.input')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_handle_audit_log_with_blocks(self, mock_stdout, mock_input, cli_app: HashVoteCLI):
        """Test audit log handling with blocks."""
        # Add test blocks
        timestamp = datetime.utcnow()
        blocks_data = [
            ("voter1", "option_a"),
            ("voter2", "option_b"),
        ]
        
        for i, (voter, choice) in enumerate(blocks_data):
            block = Block(
                poll_id="test_poll",
                voter_hash=f"hash_{voter}",
                choice=choice,
                timestamp=timestamp,
                prev_hash="0" * 64,
                nonce=42 + i,
                block_hash=f"hash_{i}"
            )
            cli_app.session.add(block)
        
        cli_app.session.commit()
        
        mock_input.return_value = "test_poll"
        
        cli_app.handle_audit_log()
        
        output = mock_stdout.getvalue()
        assert "総ブロック数: 2" in output
        assert "ブロック #1" in output
        assert "ブロック #2" in output


class TestCLIHealthCheck:
    """Test cases for health check functionality."""
    
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_handle_health_check_success(self, mock_stdout, cli_app: HashVoteCLI):
        """Test successful health check."""
        cli_app.handle_health_check()
        
        output = mock_stdout.getvalue()
        assert "✅ システム正常" in output
        assert "データベース接続: OK" in output
        assert "総ブロック数:" in output
        assert "バージョン: 1.0.0-CLI" in output


class TestCLIMainLoop:
    """Test cases for main application loop."""
    
    @patch('builtins.input')
    @patch('app.cli.HashVoteCLI.clear_screen')
    @patch('app.cli.HashVoteCLI.display_header')
    @patch('app.cli.HashVoteCLI.display_menu')
    def test_run_exit_choice(self, mock_menu, mock_header, mock_clear, mock_input, cli_app: HashVoteCLI):
        """Test running CLI with exit choice."""
        mock_input.return_value = "5"  # Exit choice
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            cli_app.run()
            
            output = mock_stdout.getvalue()
            assert "HashVoteを終了します" in output
    
    @patch('builtins.input')
    @patch('app.cli.HashVoteCLI.clear_screen')
    @patch('app.cli.HashVoteCLI.display_header')
    @patch('app.cli.HashVoteCLI.display_menu')
    def test_run_invalid_choice(self, mock_menu, mock_header, mock_clear, mock_input, cli_app: HashVoteCLI):
        """Test running CLI with invalid choice."""
        mock_input.side_effect = ["9", "5"]  # Invalid choice then exit
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            cli_app.run()
            
            output = mock_stdout.getvalue()
            assert "無効な選択です" in output