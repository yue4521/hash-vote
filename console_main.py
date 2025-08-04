#!/usr/bin/env python3
"""
HashVote Console Application Entry Point.

A command-line interface for the proof-of-work based voting system.
"""
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.cli import main  # noqa: E402

if __name__ == "__main__":
    print("HashVote CLI Starting...")
    print("Pythonコンソール版HashVote投票システムを開始します。")
    print()

    try:
        main()
    except KeyboardInterrupt:
        print("\nプログラムが中断されました。")
        sys.exit(0)
    except Exception as e:
        print(f"エラー: {str(e)}")
        sys.exit(1)
