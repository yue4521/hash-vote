# HashVote - Proof-of-Work投票システム

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

ブロックチェーン技術とProof-of-Work（PoW）アルゴリズムを使用した分散型投票システム。各投票は暗号学的に検証可能なブロックとして記録され、改ざん耐性のある投票記録を実現します。

## 特徴

- **Proof-of-Work**: 18ビットの先頭ゼロ要件による投票証明
- **改ざん検証**: チェーン全体の整合性をリアルタイムで検証  
- **重複投票防止**: 投票者ごとの一意性保証
- **完全監査**: 全投票履歴の透明性と検証可能性
- **コンソール対応**: Pythonコンソール上での直接操作
- **WebAPI**: HTTP API経由でのプログラマブルアクセス

## セットアップ

```bash
# 仮想環境の作成と依存関係のインストール
python -m venv venv
source venv/bin/activate  # Linux/Mac の場合
pip install -r requirements.txt
```

## 実行方法

### 1. コンソール版（推奨）

```bash
# Pythonコンソール上でのメニュー駆動操作
python console_main.py
```

コンソール版では以下の機能が利用できます：
- 投票の提出（Proof-of-Work計算込み）
- 投票結果の確認
- 監査ログの表示
- システムヘルスチェック

### 2. WebAPI版

```bash
# WebAPIサーバーの起動
python -m uvicorn app.main:app --reload
```

起動後のアクセス先：
- API: http://localhost:8000
- ドキュメント: http://localhost:8000/docs

## 基本的な使用方法

### コンソール版の使用

```bash
# コンソールアプリケーションの起動
python console_main.py

# メニューから選択して操作
# 1. 投票する - 投票ID、選択肢、投票者IDを入力
# 2. 投票結果を確認する - 投票IDを入力して結果表示
# 3. 監査ログを確認する - 全ブロックの詳細情報表示
# 4. ヘルスチェック - システム状態確認
# 5. 終了
```

### WebAPI版の使用

### 1. 投票リクエスト（Proof-of-Work計算用）
```bash
curl -X POST "http://localhost:8000/vote" \
  -H "Content-Type: application/json" \
  -d '{"poll_id": "election_2024", "choice": "candidate_a", "voter_hash": "unique_voter_id"}'
```

### 2. nonce計算後の投票提出
```bash
curl -X POST "http://localhost:8000/vote" \
  -H "Content-Type: application/json" \
  -d '{"poll_id": "election_2024", "choice": "candidate_a", "voter_hash": "unique_voter_id", "nonce": 123456}'
```

### 3. 結果確認
```bash
# 投票結果
curl "http://localhost:8000/poll/election_2024/result"

# 監査ログ
curl "http://localhost:8000/poll/election_2024/audit"
```

## テスト実行

```bash
pytest
```

## ドキュメント

詳細な情報については、以下のドキュメントを参照してください：

- [開発ガイド](docs/development.md) - アーキテクチャ、実装詳細、開発作業フロー
- [API使用方法詳細](docs/api-usage.md) - 詳細なAPI例とレスポンス
- [テスト仕様](docs/testing.md) - テスト詳細仕様、実行方法、トラブルシューティング
- [技術仕様](docs/technical-specs.md) - ブロック構造とProof-of-Work仕様
- [セキュリティ](docs/security.md) - セキュリティ考慮事項と制限事項

## ライセンス

MIT
