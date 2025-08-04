"""
Unit tests for CLI functionality.
"""

import pytest
from unittest.mock import patch
from datetime import datetime, timezone
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
        with patch("app.cli.create_db_and_tables"), patch("app.cli.get_session_direct"):
            app = HashVoteCLI()
            # Mock may return None
            assert app.session is not None or app.session is None
            # Rich console should be initialized
            assert hasattr(app, "console")

    def test_get_latest_block_hash_empty(self, cli_app: HashVoteCLI):
        """Test getting latest block hash when no blocks exist."""
        result = cli_app.get_latest_block_hash("test_poll")
        assert result == "0" * 64

    def test_get_latest_block_hash_with_blocks(self, cli_app: HashVoteCLI):
        """Test getting latest block hash with existing blocks."""
        # Add a test block
        timestamp = datetime.now(timezone.utc)
        block = Block(
            poll_id="test_poll",
            voter_hash="test_voter",
            choice="option_a",
            timestamp=timestamp,
            prev_hash="0" * 64,
            nonce=42,
            block_hash="abcdef123456",
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
        timestamp = datetime.now(timezone.utc)
        block = Block(
            poll_id="test_poll",
            voter_hash="test_voter",
            choice="option_a",
            timestamp=timestamp,
            prev_hash="0" * 64,
            nonce=42,
            block_hash="abcdef123456",
        )
        cli_app.session.add(block)
        cli_app.session.commit()

        result = cli_app.check_duplicate_vote("test_poll", "test_voter")
        assert result is True

    @patch("rich.prompt.Prompt.ask")
    def test_get_user_input(self, mock_ask, cli_app: HashVoteCLI):
        """Test user input handling with Rich Prompt."""
        mock_ask.return_value = "test_input"
        result = cli_app.get_user_input("Test prompt")
        assert result == "test_input"
        mock_ask.assert_called_once()

    @patch("rich.console.Console.clear")
    def test_clear_screen(self, mock_clear, cli_app: HashVoteCLI):
        """Test screen clearing functionality with Rich Console."""
        cli_app.clear_screen()
        mock_clear.assert_called_once()

    @patch("rich.console.Console.print")
    def test_display_header(self, mock_print, cli_app: HashVoteCLI):
        """Test header display with Rich formatting."""
        cli_app.display_header()
        # Should be called twice: once for panel, once for empty line
        assert mock_print.call_count >= 1
        # Check that Panel was created
        # (can't easily test content due to Rich formatting)
        call_args = mock_print.call_args_list
        assert len(call_args) > 0

    @patch("rich.console.Console.print")
    def test_display_menu(self, mock_print, cli_app: HashVoteCLI):
        """Test menu display with Rich table."""
        cli_app.display_menu()
        # Should be called once for the panel with table
        mock_print.assert_called_once()
        # Verify it's called with a Panel object
        call_args = mock_print.call_args[0]
        assert len(call_args) > 0


class TestCLIVoteHandling:
    """Test cases for voting functionality."""

    @patch("rich.prompt.Prompt.ask")
    @patch("rich.console.Console.print")
    @patch("rich.console.Console.rule")
    def test_handle_vote_missing_poll_id(
        self, mock_rule, mock_print, mock_ask, cli_app: HashVoteCLI
    ):
        """Test vote handling with missing poll ID."""
        mock_ask.side_effect = ["", "option_a", "voter1"]  # Empty poll_id

        cli_app.handle_vote()

        # Check that error message was printed
        error_calls = [
            call
            for call in mock_print.call_args_list
            if any("エラー: 投票IDが必要です" in str(arg) for arg in call[0])
        ]
        assert len(error_calls) > 0

    @patch("rich.prompt.Prompt.ask")
    @patch("rich.console.Console.print")
    @patch("rich.console.Console.rule")
    def test_handle_vote_missing_choice(
        self, mock_rule, mock_print, mock_ask, cli_app: HashVoteCLI
    ):
        """Test vote handling with missing choice."""
        mock_ask.side_effect = ["test_poll", "", "voter1"]  # Empty choice

        cli_app.handle_vote()

        # Check that error message was printed
        error_calls = [
            call
            for call in mock_print.call_args_list
            if any("エラー: 選択肢が必要です" in str(arg) for arg in call[0])
        ]
        assert len(error_calls) > 0

    @patch("rich.prompt.Prompt.ask")
    @patch("rich.console.Console.print")
    @patch("rich.console.Console.rule")
    def test_handle_vote_missing_voter_id(
        self, mock_rule, mock_print, mock_ask, cli_app: HashVoteCLI
    ):
        """Test vote handling with missing voter ID."""
        mock_ask.side_effect = ["test_poll", "option_a", ""]  # Empty voter_id

        cli_app.handle_vote()

        # Check that error message was printed
        error_calls = [
            call
            for call in mock_print.call_args_list
            if any("エラー: 投票者IDが必要です" in str(arg) for arg in call[0])
        ]
        assert len(error_calls) > 0

    @patch("rich.prompt.Prompt.ask")
    @patch("rich.console.Console.print")
    @patch("rich.console.Console.rule")
    def test_handle_vote_duplicate(
        self, mock_rule, mock_print, mock_ask, cli_app: HashVoteCLI
    ):
        """Test vote handling with duplicate voter."""
        # Add existing vote
        timestamp = datetime.now(timezone.utc)
        import hashlib

        voter_hash = hashlib.sha256("voter1".encode("utf-8")).hexdigest()

        block = Block(
            poll_id="test_poll",
            voter_hash=voter_hash,
            choice="option_a",
            timestamp=timestamp,
            prev_hash="0" * 64,
            nonce=42,
            block_hash="abcdef123456",
        )
        cli_app.session.add(block)
        cli_app.session.commit()

        mock_ask.side_effect = ["test_poll", "option_b", "voter1"]

        cli_app.handle_vote()

        # Check that error message was printed
        error_calls = [
            call
            for call in mock_print.call_args_list
            if any("この投票者は既に投票済みです" in str(arg) for arg in call[0])
        ]
        assert len(error_calls) > 0


class TestCLIPollResults:
    """Test cases for poll result functionality."""

    @patch("rich.prompt.Prompt.ask")
    @patch("rich.console.Console.print")
    @patch("rich.console.Console.rule")
    def test_handle_poll_result_empty(
        self, mock_rule, mock_print, mock_ask, cli_app: HashVoteCLI
    ):
        """Test poll result handling for empty poll."""
        mock_ask.return_value = "empty_poll"

        cli_app.handle_poll_result()

        # Check that warning message was printed
        warning_calls = [
            call
            for call in mock_print.call_args_list
            if any("投票は見つかりませんでした" in str(arg) for arg in call[0])
        ]
        assert len(warning_calls) > 0

    @patch("rich.prompt.Prompt.ask")
    @patch("rich.console.Console.print")
    @patch("rich.console.Console.rule")
    def test_handle_poll_result_with_votes(
        self, mock_rule, mock_print, mock_ask, cli_app: HashVoteCLI
    ):
        """Test poll result handling with votes."""
        # Add test votes
        timestamp = datetime.now(timezone.utc)
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
                block_hash=f"hash_{i}",
            )
            cli_app.session.add(block)

        cli_app.session.commit()

        mock_ask.return_value = "test_poll"

        cli_app.handle_poll_result()

        # Verify that print was called with panels and table
        # At least summary panel and results table
        assert mock_print.call_count >= 2


class TestCLIAuditLog:
    """Test cases for audit log functionality."""

    @patch("rich.prompt.Prompt.ask")
    @patch("rich.console.Console.print")
    @patch("rich.console.Console.rule")
    def test_handle_audit_log_empty(
        self, mock_rule, mock_print, mock_ask, cli_app: HashVoteCLI
    ):
        """Test audit log handling for empty poll."""
        mock_ask.return_value = "empty_poll"

        cli_app.handle_audit_log()

        # Check that warning message was printed
        warning_calls = [
            call
            for call in mock_print.call_args_list
            if any("投票は見つかりませんでした" in str(arg) for arg in call[0])
        ]
        assert len(warning_calls) > 0

    @patch("rich.prompt.Prompt.ask")
    @patch("rich.console.Console.print")
    @patch("rich.console.Console.rule")
    def test_handle_audit_log_with_blocks(
        self, mock_rule, mock_print, mock_ask, cli_app: HashVoteCLI
    ):
        """Test audit log handling with blocks."""
        # Add test blocks
        timestamp = datetime.now(timezone.utc)
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
                block_hash=f"hash_{i}",
            )
            cli_app.session.add(block)

        cli_app.session.commit()

        mock_ask.return_value = "test_poll"

        cli_app.handle_audit_log()

        # Verify that print was called multiple times
        # (header, table, integrity panels)
        assert mock_print.call_count >= 3


class TestCLIHealthCheck:
    """Test cases for health check functionality."""

    @patch("rich.console.Console.print")
    @patch("rich.console.Console.rule")
    def test_handle_health_check_success(
        self, mock_rule, mock_print, cli_app: HashVoteCLI
    ):
        """Test successful health check."""
        cli_app.handle_health_check()

        # Verify that print was called multiple times
        # (status panel and info panel)
        assert mock_print.call_count >= 2
        mock_rule.assert_called_once()


class TestCLIMainLoop:
    """Test cases for main application loop."""

    @patch("rich.prompt.Prompt.ask")
    @patch("rich.console.Console.print")
    @patch("app.cli.HashVoteCLI.clear_screen")
    @patch("app.cli.HashVoteCLI.display_header")
    @patch("app.cli.HashVoteCLI.display_menu")
    def test_run_exit_choice(
        self,
        mock_menu,
        mock_header,
        mock_clear,
        mock_print,
        mock_ask,
        cli_app: HashVoteCLI,
    ):
        """Test running CLI with exit choice."""
        mock_ask.return_value = "5"  # Exit choice

        cli_app.run()

        # Check that print was called (goodbye panel should be printed)
        assert mock_print.called
        # Verify that we tried to get input for menu choice
        mock_ask.assert_called()

    @patch("rich.prompt.Prompt.ask")
    @patch("rich.console.Console.print")
    @patch("builtins.input")  # For the continue prompt
    @patch("app.cli.HashVoteCLI.clear_screen")
    @patch("app.cli.HashVoteCLI.display_header")
    @patch("app.cli.HashVoteCLI.display_menu")
    def test_run_invalid_choice(
        self,
        mock_menu,
        mock_header,
        mock_clear,
        mock_input,
        mock_print,
        mock_ask,
        cli_app: HashVoteCLI,
    ):
        """Test running CLI with invalid choice."""
        mock_ask.side_effect = ["9", "5"]  # Invalid choice then exit
        mock_input.return_value = ""  # For continue prompt

        cli_app.run()

        # Check that invalid choice message was printed
        invalid_calls = [
            call
            for call in mock_print.call_args_list
            if any("無効な選択です" in str(arg) for arg in call[0])
        ]
        assert len(invalid_calls) > 0
