#!/usr/bin/env python3
"""
README.mdのバージョンバッジをapp/__init__.pyの__version__と同期するスクリプト
"""

import re
from pathlib import Path


def get_version():
    """app/__init__.pyから__version__を読み込む"""
    init_file = Path("app/__init__.py")
    if not init_file.exists():
        raise FileNotFoundError("app/__init__.py が見つかりません")
    
    content = init_file.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
    if not match:
        raise ValueError("app/__init__.py に __version__ が見つかりません")
    
    return match.group(1)


def update_readme_badge(version):
    """README.mdのバージョンバッジを更新する"""
    readme_file = Path("README.md")
    if not readme_file.exists():
        raise FileNotFoundError("README.md が見つかりません")
    
    content = readme_file.read_text(encoding="utf-8")
    
    # バージョンバッジの正規表現パターン
    pattern = r'(\[\!\[Version\]\(https://img\.shields\.io/badge/version-)[^-]+(-green\.svg\)\])'
    replacement = f'\\g<1>{version}\\g<2>'
    
    updated_content = re.sub(pattern, replacement, content)
    
    if content == updated_content:
        print(f"README.md は既に最新バージョン {version} です")
        return False
    
    readme_file.write_text(updated_content, encoding="utf-8")
    print(f"README.md のバージョンバッジを {version} に更新しました")
    return True


def main():
    try:
        version = get_version()
        print(f"検出されたバージョン: {version}")
        
        updated = update_readme_badge(version)
        
        if updated:
            print("✅ バージョンバッジの更新が完了しました")
        else:
            print("ℹ️  更新の必要はありませんでした")
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())