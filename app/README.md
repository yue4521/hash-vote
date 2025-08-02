# HashVoteアプリケーション

このディレクトリには、HashVoteシステムのメインアプリケーションコードが含まれています。

## アーキテクチャ概要

HashVoteは以下の層構造で設計されたProof-of-Work投票システムです：

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

### `main.py` - FastAPIアプリケーション
メインのAPIアプリケーションファイル。すべてのエンドポイントとビジネスロジックを実装。

**主要な機能:**
- **2段階投票プロセス**: 初回リクエスト → PoW計算 → 最終提出
- **チェーン整合性検証**: ブロックチェーンの暗号学的整合性をリアルタイムで検証
- **重複投票防止**: データベース制約による確実な一意性保証
- **エラーハンドリング**: 適切なHTTPステータスコードと詳細エラーメッセージ

**API エンドポイント:**
- `POST /vote` - 投票の提出（2段階プロセス）
- `GET /poll/{poll_id}/result` - 投票結果の集計
- `GET /poll/{poll_id}/audit` - 監査証跡の取得
- `GET /health` - ヘルスチェック

### `models.py` - データモデル
SQLModelを使用したタイプセーフなデータモデル定義。

**主要なモデル:**
- **`Block`**: 投票ブロックの永続化モデル
  - 複合UNIQUE制約（poll_id + voter_hash）による重複防止
  - インデックス最適化されたクエリサポート
- **`VoteRequest`/`VoteSubmission`**: リクエストバリデーション
- **`VoteResponse`/`PollResult`/`AuditResponse`**: レスポンス形式

**データベース制約:**
```sql
UNIQUE(poll_id, voter_hash)  -- 重複投票防止
UNIQUE(block_hash)           -- ブロックハッシュ一意性
INDEX(poll_id)               -- 投票検索最適化
INDEX(block_hash)            -- チェーン検証最適化
```

### `pow.py` - Proof-of-Work実装
ブロックチェーンの核となる暗号学的機能を提供。

**主要な関数:**
- **`hash_block()`**: SHA-256ブロックハッシュ計算
- **`compute_nonce()`**: 難易度条件を満たすnonce計算
- **`verify_pow()`**: Proof-of-Work検証
- **`get_difficulty_target()`**: 難易度目標値の計算

**PoW仕様:**
- **難易度**: 18ビット先頭ゼロ（約262,144回平均試行）
- **アルゴリズム**: SHA-256
- **目標**: `hash_value < 2^(256-18) = 2^238`
- **タイムアウト**: オプションで計算時間制限

**ハッシュ計算順序:**
```
block_data = poll_id + voter_hash + choice + timestamp + prev_hash + nonce
block_hash = SHA-256(block_data)
```

### `database.py` - データベース層
SQLiteデータベースの接続管理と設定。

**主要な機能:**
- **SQLite設定**: スレッドセーフ接続とパフォーマンス最適化
- **セッション管理**: FastAPIの依存性注入システムと統合
- **テーブル初期化**: アプリケーション起動時の自動スキーマ作成

**設定:**
```python
DATABASE_URL = "sqlite:///./hashvote.db"
check_same_thread = False  # マルチスレッド対応
echo = False              # 本番環境用設定
```

## 開発ガイド

### 新しいAPIエンドポイントの追加

1. **models.py**でリクエスト/レスポンスモデルを定義
2. **main.py**でエンドポイント関数を実装
3. **database.py**の依存性注入を使用してデータベースアクセス
4. 適切なHTTPステータスコードとエラーハンドリングを実装

例:
```python
@app.get("/new-endpoint", response_model=ResponseModel)
async def new_endpoint(session: Session = Depends(get_session)):
    # ビジネスロジック実装
    return ResponseModel(...)
```

### データモデルの変更

1. **models.py**でSQLModelクラスを更新
2. データベースマイグレーション（手動またはAlembic）
3. 関連するAPI エンドポイントの更新
4. テストケースの更新

### PoW難易度の調整

```python
# main.py内の難易度設定
difficulty = 6 if poll_id.startswith("test_") else 18

# pow.py内のcompute_nonce()でタイムアウト設定
nonce = compute_nonce(..., difficulty_bits=difficulty, timeout=300)
```

### セキュリティ考慮事項

**実装済みの保護:**
- SQLインジェクション対策（SQLModel使用）
- 入力値検証（Pydanticモデル）
- 重複投票防止（データベース制約）
- チェーン整合性検証（暗号学的検証）

**注意が必要な領域:**
- voter_hash管理（外部認証システムと統合）
- DoS攻撃対策（レート制限の追加検討）
- データベースバックアップ戦略

### パフォーマンス最適化

**現在の実装:**
- データベースインデックス（poll_id, block_hash）
- 非同期API（FastAPI）
- SQLiteの最適化設定

**スケールアップ時の検討事項:**
- PostgreSQL/MySQLへの移行
- Redis等のキャッシュ層追加
- 水平スケーリング対応

## 関連ドキュメント

- [プロジェクト全体の概要](../readme.md)
- [テスト仕様](../tests/README.md)
- [API使用方法](../readme.md#api使用方法)