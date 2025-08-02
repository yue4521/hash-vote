# HashVoteアプリケーション

HashVoteシステムのメインアプリケーションコードが含まれています。

## 概要

Proof-of-Work投票システムの4層アーキテクチャ：

```
┌─────────────────┐
│   FastAPI       │  ← API層（main.py）
├─────────────────┤
│   Models        │  ← データモデル（models.py）
├─────────────────┤
│   PoW Engine    │  ← Proof-of-Work実装（pow.py）
├─────────────────┤
│   Database      │  ← データベース層（database.py）
└─────────────────┘
```

## ファイル構成

- **`main.py`** - FastAPIアプリケーション、全APIエンドポイント
- **`models.py`** - SQLModelデータモデル定義
- **`pow.py`** - SHA-256 Proof-of-Work実装
- **`database.py`** - SQLiteデータベース設定

## クイックスタート

```bash
# 開発環境起動
uvicorn app.main:app --reload

# テスト実行
pytest tests/
```

## 関連ドキュメント

- [詳細なアーキテクチャと開発ガイド](../docs/development.md)
- [API使用方法](../docs/api-usage.md) 
- [テスト仕様](../docs/testing.md)
- [セキュリティ考慮事項](../docs/security.md)