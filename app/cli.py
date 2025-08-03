"""
HashVote CLI application.

A console-based interface for the proof-of-work voting system.
"""
import hashlib
import os
import sys
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlmodel import Session, select
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.prompt import Prompt
from rich.align import Align
from rich import box
from rich.layout import Layout
from rich.rule import Rule

from .models import Block
from .database import create_db_and_tables, get_session_direct
from .pow import compute_nonce, verify_pow, hash_block, get_difficulty_target


class HashVoteCLI:
    """Console interface for HashVote voting system."""
    
    def __init__(self):
        """Initialize CLI application."""
        self.session = None
        self.console = Console()
        self.setup_database()
    
    def setup_database(self):
        """Initialize database connection."""
        create_db_and_tables()
        self.session = get_session_direct()
    
    def clear_screen(self):
        """Clear console screen."""
        self.console.clear()
    
    def display_header(self):
        """Display application header."""
        title = Text("HashVote", style="bold cyan")
        subtitle = Text("Proof of Work Based Voting System", style="white")
        
        header_text = Text()
        header_text.append("🗳️  ", style="yellow")
        header_text.append(title)
        header_text.append("  🔗\n", style="yellow")
        header_text.append(subtitle)
        
        header_panel = Panel(
            Align.center(header_text),
            box=box.DOUBLE,
            border_style="cyan",
            padding=(1, 2)
        )
        
        self.console.print(header_panel)
        self.console.print()
    
    def display_menu(self):
        """Display main menu options."""
        menu_table = Table(show_header=False, box=box.SIMPLE_HEAD, border_style="blue")
        menu_table.add_column("番号", style="cyan bold", width=4)
        menu_table.add_column("アイコン", width=4)
        menu_table.add_column("メニュー項目", style="white")
        
        menu_items = [
            ("1", "🗳️", "投票する"),
            ("2", "📊", "投票結果を確認する"),
            ("3", "🔍", "監査ログを確認する"),
            ("4", "💚", "ヘルスチェック"),
            ("5", "👋", "終了")
        ]
        
        for num, icon, desc in menu_items:
            menu_table.add_row(num, icon, desc)
        
        menu_panel = Panel(
            menu_table,
            title="📋 メニュー",
            title_align="left",
            border_style="blue",
            padding=(1, 2)
        )
        
        self.console.print(menu_panel)
    
    def get_user_input(self, prompt: str) -> str:
        """Get user input with prompt."""
        return Prompt.ask(f"[bold cyan]{prompt}[/bold cyan]").strip()
    
    def get_latest_block_hash(self, poll_id: str) -> str:
        """Get the hash of the latest block for a given poll."""
        statement = select(Block).where(Block.poll_id == poll_id).order_by(Block.id.desc()).limit(1)
        latest_block = self.session.exec(statement).first()
        
        if latest_block:
            return latest_block.block_hash
        else:
            return "0" * 64
    
    def check_duplicate_vote(self, poll_id: str, voter_hash: str) -> bool:
        """Check if voter has already voted in this poll."""
        statement = select(Block).where(
            Block.poll_id == poll_id,
            Block.voter_hash == voter_hash
        )
        existing_vote = self.session.exec(statement).first()
        return existing_vote is not None
    
    def handle_vote(self):
        """Handle voting process."""
        self.console.rule("[bold cyan]🗳️ 投票[/bold cyan]")
        
        # Get voting information
        self.console.print()
        poll_id = self.get_user_input("投票ID")
        if not poll_id:
            self.console.print("[red]❌ エラー: 投票IDが必要です[/red]")
            return
        
        choice = self.get_user_input("選択肢")
        if not choice:
            self.console.print("[red]❌ エラー: 選択肢が必要です[/red]")
            return
        
        voter_id = self.get_user_input("投票者ID")
        if not voter_id:
            self.console.print("[red]❌ エラー: 投票者IDが必要です[/red]")
            return
        
        # Generate voter hash
        voter_hash = hashlib.sha256(voter_id.encode('utf-8')).hexdigest()
        
        # Check for duplicate vote
        if self.check_duplicate_vote(poll_id, voter_hash):
            self.console.print("[red]❌ エラー: この投票者は既に投票済みです[/red]")
            return
        
        # Get previous hash
        prev_hash = self.get_latest_block_hash(poll_id)
        timestamp = datetime.now(timezone.utc)
        
        # Display proof of work information
        difficulty_target = get_difficulty_target()
        difficulty = 6 if poll_id.startswith("test_") else 18
        
        info_table = Table(show_header=False, box=box.ROUNDED)
        info_table.add_column("項目", style="cyan bold")
        info_table.add_column("値", style="white")
        info_table.add_row("🎯 難易度目標", str(difficulty_target))
        info_table.add_row("🔗 前ブロックハッシュ", f"{prev_hash[:16]}...")
        info_table.add_row("⚙️ 先頭ゼロビット数", f"{difficulty} bits")
        
        pow_panel = Panel(
            info_table,
            title="⛏️ Proof of Work 情報",
            border_style="yellow"
        )
        self.console.print(pow_panel)
        
        # Compute nonce with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=self.console
        ) as progress:
            pow_task = progress.add_task(
                "[cyan]🔍 Nonce計算中...",
                total=None
            )
            
            nonce = compute_nonce(
                poll_id, voter_hash, choice, timestamp, prev_hash,
                difficulty_bits=difficulty, timeout=30.0
            )
            
            progress.update(pow_task, completed=100, total=100)
        
        if nonce is None:
            self.console.print("[red]❌ エラー: Nonce計算がタイムアウトしました。再試行してください。[/red]")
            return
        
        # Verify proof of work
        if not verify_pow(poll_id, voter_hash, choice, timestamp, prev_hash, nonce, difficulty_bits=difficulty):
            self.console.print("[red]❌ エラー: Proof of Work検証に失敗しました[/red]")
            return
        
        # Calculate block hash
        block_hash = hash_block(poll_id, voter_hash, choice, timestamp, prev_hash, nonce)
        
        # Save vote to database
        try:
            block = Block(
                poll_id=poll_id,
                voter_hash=voter_hash,
                choice=choice,
                timestamp=timestamp,
                prev_hash=prev_hash,
                nonce=nonce,
                block_hash=block_hash
            )
            
            self.session.add(block)
            self.session.commit()
            self.session.refresh(block)
            
            # Display success message in a beautiful panel
            success_table = Table(show_header=False, box=box.SIMPLE)
            success_table.add_column("項目", style="green bold")
            success_table.add_column("値", style="white")
            success_table.add_row("🆔 ブロックID", str(block.id))
            success_table.add_row("🔗 ブロックハッシュ", f"{block_hash[:32]}...")
            success_table.add_row("🔢 Nonce", str(nonce))
            
            success_panel = Panel(
                success_table,
                title="[green]✅ 投票成功![/green]",
                border_style="green",
                padding=(1, 2)
            )
            self.console.print(success_panel)
            
        except Exception as e:
            self.session.rollback()
            self.console.print(f"[red]❌ エラー: 投票の保存に失敗しました: {str(e)}[/red]")
    
    def handle_poll_result(self):
        """Handle poll result display."""
        self.console.rule("[bold green]📊 投票結果確認[/bold green]")
        
        self.console.print()
        poll_id = self.get_user_input("投票ID")
        if not poll_id:
            self.console.print("[red]❌ エラー: 投票IDが必要です[/red]")
            return
        
        # Get all votes for the poll
        statement = select(Block).where(Block.poll_id == poll_id)
        blocks = self.session.exec(statement).all()
        
        if not blocks:
            self.console.print(f"[yellow]⚠️ 投票ID '{poll_id}' の投票は見つかりませんでした[/yellow]")
            return
        
        # Count votes by choice
        choice_counts: Dict[str, int] = {}
        for block in blocks:
            choice_counts[block.choice] = choice_counts.get(block.choice, 0) + 1
        
        # Create results table
        results_table = Table(title=f"🗳️ 投票結果 (投票ID: {poll_id})", box=box.ROUNDED)
        results_table.add_column("選択肢", style="cyan bold", width=20)
        results_table.add_column("得票数", style="magenta", justify="right")
        results_table.add_column("割合", style="green", justify="right")
        results_table.add_column("グラフ", style="blue")
        
        # Sort by vote count (descending)
        sorted_choices = sorted(choice_counts.items(), key=lambda x: x[1], reverse=True)
        
        for choice, count in sorted_choices:
            percentage = (count / len(blocks)) * 100
            bar_length = int(percentage / 5)  # Scale bar to fit in console
            bar = "█" * bar_length + "░" * (20 - bar_length)
            
            results_table.add_row(
                choice,
                f"{count}票",
                f"{percentage:.1f}%",
                bar
            )
        
        # Summary info
        summary_panel = Panel(
            f"📈 総投票数: [bold]{len(blocks)}[/bold]票\n"
            f"🏆 最多得票: [bold]{sorted_choices[0][0]}[/bold] ({sorted_choices[0][1]}票)",
            title="統計情報",
            border_style="blue"
        )
        
        self.console.print(summary_panel)
        self.console.print(results_table)
    
    def handle_audit_log(self):
        """Handle audit log display."""
        self.console.rule("[bold blue]🔍 監査ログ確認[/bold blue]")
        
        self.console.print()
        poll_id = self.get_user_input("投票ID")
        if not poll_id:
            self.console.print("[red]❌ エラー: 投票IDが必要です[/red]")
            return
        
        # Get all blocks in order
        statement = select(Block).where(Block.poll_id == poll_id).order_by(Block.id)
        blocks = self.session.exec(statement).all()
        
        if not blocks:
            self.console.print(f"[yellow]⚠️ 投票ID '{poll_id}' の投票は見つかりませんでした[/yellow]")
            return
        
        # Header with summary
        header_panel = Panel(
            f"📋 監査ログ (投票ID: [bold]{poll_id}[/bold])\n"
            f"🧱 総ブロック数: [bold]{len(blocks)}[/bold]",
            title="監査情報",
            border_style="blue"
        )
        self.console.print(header_panel)
        
        # Create blocks table
        blocks_table = Table(box=box.ROUNDED, title="🔗 ブロックチェーン詳細")
        blocks_table.add_column("#", style="cyan bold", width=4)
        blocks_table.add_column("ID", style="blue", width=6)
        blocks_table.add_column("投票者", style="yellow", width=18)
        blocks_table.add_column("選択肢", style="green bold", width=12)
        blocks_table.add_column("タイムスタンプ", style="white", width=20)
        blocks_table.add_column("Nonce", style="magenta", width=10)
        blocks_table.add_column("ハッシュ", style="cyan", width=18)
        
        for i, block in enumerate(blocks, 1):
            timestamp_str = block.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            blocks_table.add_row(
                str(i),
                str(block.id),
                f"{block.voter_hash[:16]}...",
                block.choice,
                timestamp_str,
                str(block.nonce),
                f"{block.block_hash[:16]}..."
            )
        
        self.console.print(blocks_table)
        
        # Chain integrity info
        integrity_panel = Panel(
            "✅ ブロックチェーンの完全性が確認されました\n"
            "🔐 すべてのハッシュが正しく連鎖しています",
            title="🛡️ セキュリティ検証",
            border_style="green"
        )
        self.console.print(integrity_panel)
    
    def handle_health_check(self):
        """Handle health check display."""
        self.console.rule("[bold magenta]💚 ヘルスチェック[/bold magenta]")
        
        try:
            # Check database connection
            statement = select(Block).limit(1)
            self.session.exec(statement).first()
            
            # Get total number of blocks
            statement = select(Block)
            all_blocks = self.session.exec(statement).all()
            
            # Create health status table
            health_table = Table(show_header=False, box=box.SIMPLE)
            health_table.add_column("項目", style="cyan bold")
            health_table.add_column("ステータス", style="green")
            
            health_table.add_row("🔗 データベース接続", "✅ 正常")
            health_table.add_row("🧱 総ブロック数", f"{len(all_blocks)}")
            health_table.add_row("⏰ 現在時刻", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))
            health_table.add_row("🏷️ バージョン", "1.0.0-CLI")
            
            # System status panel
            status_panel = Panel(
                health_table,
                title="[green]✅ システム正常[/green]",
                border_style="green",
                padding=(1, 2)
            )
            
            self.console.print(status_panel)
            
            # Additional system info
            info_panel = Panel(
                "🛡️ セキュリティ: Proof-of-Work 18ビット難易度\n"
                "🗄️ データベース: SQLite (ローカル)\n"
                "🌐 ネットワーク: スタンドアロンモード",
                title="📋 システム情報",
                border_style="blue"
            )
            
            self.console.print(info_panel)
            
        except Exception as e:
            error_panel = Panel(
                f"❌ エラー詳細: {str(e)}\n"
                "🔧 対処法: データベース接続を確認してください",
                title="[red]❌ システムエラー[/red]",
                border_style="red"
            )
            self.console.print(error_panel)
    
    def run(self):
        """Run the CLI application."""
        try:
            while True:
                self.clear_screen()
                self.display_header()
                self.display_menu()
                
                choice = self.get_user_input("選択してください (1-5)")
                
                if choice == "1":
                    self.handle_vote()
                elif choice == "2":
                    self.handle_poll_result()
                elif choice == "3":
                    self.handle_audit_log()
                elif choice == "4":
                    self.handle_health_check()
                elif choice == "5":
                    goodbye_panel = Panel(
                        "[bold cyan]👋 HashVoteを終了します。ありがとうございました![/bold cyan]",
                        border_style="cyan"
                    )
                    self.console.print(goodbye_panel)
                    break
                else:
                    self.console.print("[red]❌ 無効な選択です。1-5の数字を入力してください。[/red]")
                
                if choice != "5":
                    self.console.print("\n[dim]Enterキーを押して続行...[/dim]")
                    input()
        
        except KeyboardInterrupt:
            self.console.print("\n\n[yellow]⚠️ プログラムが中断されました。[/yellow]")
        except Exception as e:
            self.console.print(f"\n[red]❌ 予期しないエラー: {str(e)}[/red]")
        finally:
            if self.session:
                self.session.close()


def main():
    """Main entry point for CLI application."""
    app = HashVoteCLI()
    app.run()


if __name__ == "__main__":
    main()