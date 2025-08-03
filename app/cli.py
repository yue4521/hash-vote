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

from .models import Block
from .database import create_db_and_tables, get_session_direct
from .pow import compute_nonce, verify_pow, hash_block, get_difficulty_target


class HashVoteCLI:
    """Console interface for HashVote voting system."""
    
    def __init__(self):
        """Initialize CLI application."""
        self.session = None
        self.setup_database()
    
    def setup_database(self):
        """Initialize database connection."""
        create_db_and_tables()
        self.session = get_session_direct()
    
    def clear_screen(self):
        """Clear console screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def display_header(self):
        """Display application header."""
        print("=" * 60)
        print("  HashVote - Proof of Work Based Voting System")
        print("=" * 60)
        print()
    
    def display_menu(self):
        """Display main menu options."""
        print("メニュー:")
        print("1. 投票する")
        print("2. 投票結果を確認する")
        print("3. 監査ログを確認する")
        print("4. ヘルスチェック")
        print("5. 終了")
        print()
    
    def get_user_input(self, prompt: str) -> str:
        """Get user input with prompt."""
        return input(f"{prompt}: ").strip()
    
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
        print("\n--- 投票 ---")
        
        # Get voting information
        poll_id = self.get_user_input("投票ID")
        if not poll_id:
            print("エラー: 投票IDが必要です")
            return
        
        choice = self.get_user_input("選択肢")
        if not choice:
            print("エラー: 選択肢が必要です")
            return
        
        voter_id = self.get_user_input("投票者ID")
        if not voter_id:
            print("エラー: 投票者IDが必要です")
            return
        
        # Generate voter hash
        voter_hash = hashlib.sha256(voter_id.encode('utf-8')).hexdigest()
        
        # Check for duplicate vote
        if self.check_duplicate_vote(poll_id, voter_hash):
            print("エラー: この投票者は既に投票済みです")
            return
        
        # Get previous hash
        prev_hash = self.get_latest_block_hash(poll_id)
        timestamp = datetime.now(timezone.utc)
        
        # Display proof of work information
        difficulty_target = get_difficulty_target()
        print(f"\n証明書作業 (Proof of Work) 情報:")
        print(f"難易度目標: {difficulty_target}")
        print(f"前ブロックハッシュ: {prev_hash}")
        print(f"必要な先頭ゼロビット数: 18 bits")
        
        print("\nNonce計算中... (しばらくお待ちください)")
        
        # Compute nonce (use lower difficulty for test polls)
        difficulty = 6 if poll_id.startswith("test_") else 18
        nonce = compute_nonce(
            poll_id, voter_hash, choice, timestamp, prev_hash,
            difficulty_bits=difficulty, timeout=30.0
        )
        
        if nonce is None:
            print("エラー: Nonce計算がタイムアウトしました。再試行してください。")
            return
        
        # Verify proof of work
        if not verify_pow(poll_id, voter_hash, choice, timestamp, prev_hash, nonce, difficulty_bits=difficulty):
            print("エラー: Proof of Work検証に失敗しました")
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
            
            print("\n✅ 投票が正常に記録されました!")
            print(f"ブロックID: {block.id}")
            print(f"ブロックハッシュ: {block_hash}")
            print(f"Nonce: {nonce}")
            
        except Exception as e:
            self.session.rollback()
            print(f"エラー: 投票の保存に失敗しました: {str(e)}")
    
    def handle_poll_result(self):
        """Handle poll result display."""
        print("\n--- 投票結果確認 ---")
        
        poll_id = self.get_user_input("投票ID")
        if not poll_id:
            print("エラー: 投票IDが必要です")
            return
        
        # Get all votes for the poll
        statement = select(Block).where(Block.poll_id == poll_id)
        blocks = self.session.exec(statement).all()
        
        if not blocks:
            print(f"投票ID '{poll_id}' の投票は見つかりませんでした")
            return
        
        # Count votes by choice
        choice_counts: Dict[str, int] = {}
        for block in blocks:
            choice_counts[block.choice] = choice_counts.get(block.choice, 0) + 1
        
        print(f"\n投票結果 (投票ID: {poll_id}):")
        print(f"総投票数: {len(blocks)}")
        print("\n選択肢別得票数:")
        for choice, count in sorted(choice_counts.items()):
            percentage = (count / len(blocks)) * 100
            print(f"  {choice}: {count}票 ({percentage:.1f}%)")
    
    def handle_audit_log(self):
        """Handle audit log display."""
        print("\n--- 監査ログ確認 ---")
        
        poll_id = self.get_user_input("投票ID")
        if not poll_id:
            print("エラー: 投票IDが必要です")
            return
        
        # Get all blocks in order
        statement = select(Block).where(Block.poll_id == poll_id).order_by(Block.id)
        blocks = self.session.exec(statement).all()
        
        if not blocks:
            print(f"投票ID '{poll_id}' の投票は見つかりませんでした")
            return
        
        print(f"\n監査ログ (投票ID: {poll_id}):")
        print(f"総ブロック数: {len(blocks)}")
        print()
        
        for i, block in enumerate(blocks, 1):
            print(f"ブロック #{i} (ID: {block.id})")
            print(f"  投票者ハッシュ: {block.voter_hash[:16]}...")
            print(f"  選択肢: {block.choice}")
            print(f"  タイムスタンプ: {block.timestamp}")
            print(f"  前ブロックハッシュ: {block.prev_hash[:16]}...")
            print(f"  Nonce: {block.nonce}")
            print(f"  ブロックハッシュ: {block.block_hash[:16]}...")
            print()
    
    def handle_health_check(self):
        """Handle health check display."""
        print("\n--- ヘルスチェック ---")
        
        try:
            # Check database connection
            statement = select(Block).limit(1)
            self.session.exec(statement).first()
            
            # Get total number of blocks
            statement = select(Block)
            all_blocks = self.session.exec(statement).all()
            
            print("✅ システム正常")
            print(f"データベース接続: OK")
            print(f"総ブロック数: {len(all_blocks)}")
            print(f"現在時刻: {datetime.now(timezone.utc).isoformat()}")
            print(f"バージョン: 1.0.0-CLI")
            
        except Exception as e:
            print(f"❌ システムエラー: {str(e)}")
    
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
                    print("\nHashVoteを終了します。ありがとうございました!")
                    break
                else:
                    print("無効な選択です。1-5の数字を入力してください。")
                
                if choice != "5":
                    input("\nEnterキーを押して続行...")
        
        except KeyboardInterrupt:
            print("\n\nプログラムが中断されました。")
        except Exception as e:
            print(f"\n予期しないエラー: {str(e)}")
        finally:
            if self.session:
                self.session.close()


def main():
    """Main entry point for CLI application."""
    app = HashVoteCLI()
    app.run()


if __name__ == "__main__":
    main()