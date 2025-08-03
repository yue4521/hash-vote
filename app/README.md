# HashVoteアプリケーション

HashVoteシステムのメインアプリケーションコードが含まれています。

## 概要

Proof-of-Work投票システムの3層アーキテクチャ：

```
┌─────────────────┐
│   CLI           │  ← CLI層（cli.py）
├─────────────────┤
│   Models        │  ← データモデル（models.py）
├─────────────────┤
│   PoW Engine    │  ← Proof-of-Work実装（pow.py）
├─────────────────┤
│   Database      │  ← データベース層（database.py）
└─────────────────┘
```

## ファイル構成

- **`cli.py`** - コンソールアプリケーション、メニュー駆動インターフェース
- **`models.py`** - SQLModelデータモデル定義（ブロック構造）
- **`pow.py`** - SHA-256 Proof-of-Work実装
- **`database.py`** - SQLiteデータベース設定

## クイックスタート

```bash
# コンソールアプリケーション起動
python console_main.py

# テスト実行
pytest tests/
```

## 関連ドキュメント

- [詳細なアーキテクチャと開発ガイド](../docs/development.md)
- [テスト仕様](../docs/testing.md)
- [セキュリティ考慮事項](../docs/security.md)