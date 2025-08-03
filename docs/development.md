# 開発ガイド

## プロジェクト構造

```
hash-vote/
├── app/                 # メインアプリケーション
│   ├── __init__.py
│   ├── cli.py           # コンソールアプリケーション
│   ├── models.py        # データモデル定義
│   ├── pow.py           # Proof-of-Work実装
│   ├── database.py      # データベース設定
│   └── README.md        # アプリケーション概要
├── tests/               # テストスイート
│   ├── __init__.py
│   ├── test_pow.py      # PoW機能テスト
│   ├── test_cli.py      # CLI機能テスト
│   └── README.md        # テスト概要
├── docs/                # ドキュメント
│   ├── technical-specs.md # 技術仕様
│   ├── security.md      # セキュリティ考慮事項
│   ├── testing.md       # テスト詳細仕様
│   └── development.md   # このファイル
├── console_main.py      # CLIエントリーポイント
├── tasks/               # 開発タスク管理
│   └── todo.md          # 実装計画とタスクリスト
├── requirements.txt     # Python依存関係
├── README.md           # プロジェクト概要
└── .gitignore          # Git除外設定
```

## アーキテクチャ詳細

HashVoteは以下の層構造で設計されたProof-of-Work投票システムです：

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

### `cli.py` - コンソールアプリケーション

メニュー駆動のコンソールインターフェース。すべての投票機能をコンソール上で提供。

**主要な機能:**
- **メニュー駆動操作**: 1-5の数字選択による直感的な操作
- **投票処理**: PoW計算込みの完全な投票プロセス
- **結果表示**: 投票結果の集計と表示
- **監査機能**: 全ブロックの詳細情報表示
- **ヘルスチェック**: システム状態確認

**CLI機能:**
- `1. 投票する` - 投票ID、選択肢、投票者IDを入力して投票
- `2. 投票結果を確認する` - 投票IDを入力して結果表示
- `3. 監査ログを確認する` - 全ブロックの詳細情報表示
- `4. ヘルスチェック` - システム状態確認
- `5. 終了` - アプリケーション終了

### `models.py` - データモデル

SQLModelを使用したタイプセーフなデータモデル定義。

**主要なモデル:**
- **`Block`**: 投票ブロックの永続化モデル
  - 複合UNIQUE制約（poll_id + voter_hash）による重複防止
  - インデックス最適化されたクエリサポート
  - CLI機能で直接使用される唯一のモデル

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
- **セッション管理**: CLI機能との直接統合
- **テーブル初期化**: アプリケーション起動時の自動スキーマ作成

**設定:**
```python
DATABASE_URL = "sqlite:///./hashvote.db"
check_same_thread = False  # マルチスレッド対応
echo = False              # 本番環境用設定
```

## 開発作業フロー

### 新しいCLI機能の追加

1. **cli.py**のHashVoteCLIクラスに新しいメソッドを追加
2. **display_menu()**でメニュー項目を追加
3. **run()**メソッドで選択肢処理を追加
4. 適切なエラーハンドリングとユーザー体験を実装

例:
```python
def handle_new_feature(self):
    print("\n--- 新機能 ---")
    # 機能実装
    input("\nEnterキーを押して続行...")
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

## セキュリティ考慮事項

**実装済みの保護:**
- SQLインジェクション対策（SQLModel使用）
- 入力値検証（Pydanticモデル）
- 重複投票防止（データベース制約）
- チェーン整合性検証（暗号学的検証）

**注意が必要な領域:**
- voter_hash管理（外部認証システムと統合）
- DoS攻撃対策（レート制限の追加検討）
- データベースバックアップ戦略

## パフォーマンス最適化

**現在の実装:**
- データベースインデックス（poll_id, block_hash）
- 同期処理によるシンプルなCLI操作
- SQLiteの最適化設定

**スケールアップ時の検討事項:**
- PostgreSQL/MySQLへの移行
- Redis等のキャッシュ層追加
- 水平スケーリング対応

## テスト実行

```bash
# 全テスト実行
pytest

# カバレッジ付きテスト
pytest --cov=app

# 特定テストファイル実行
pytest tests/test_pow.py
pytest tests/test_cli.py
```

## 開発・貢献

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)  
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. Pull Requestを作成

## サポート

質問や問題がある場合は、GitHubのIssuesでお知らせください。

## 関連ドキュメント

- [詳細なテスト仕様](testing.md)
- [セキュリティ考慮事項](security.md)
- [技術仕様](technical-specs.md)