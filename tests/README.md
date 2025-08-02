# HashVoteテストスイート

このディレクトリには、HashVoteシステムの包括的なテストが含まれています。

## テストの概要

**総テスト数**: 24テスト  
**テストファイル**: 2ファイル  
**カバレッジ**: 全主要機能

### テスト構成

```
tests/
├── test_pow.py      # Proof-of-Work機能テスト（12テスト）
├── test_api.py      # API統合テスト（12テスト）
└── __init__.py      # パッケージ初期化
```

## テストファイル詳細

### `test_pow.py` - Proof-of-Work機能テスト

HashVoteの核となる暗号学的機能をテストします。

#### TestHashBlock（3テスト）
- **`test_hash_block_deterministic`**: 同一入力での決定論的ハッシュ生成
- **`test_hash_block_different_inputs`**: 異なる入力での異なるハッシュ生成
- **`test_hash_block_format`**: SHA-256の64文字16進数出力形式

#### TestComputeNonce（3テスト）
- **`test_compute_nonce_easy_difficulty`**: 低難易度でのnonce計算
- **`test_compute_nonce_timeout`**: タイムアウト機能のテスト
- **`test_compute_nonce_deterministic`**: 決定論的nonce計算

#### TestVerifyPow（3テスト）
- **`test_verify_pow_valid`**: 有効なProof-of-Work検証
- **`test_verify_pow_invalid`**: 無効なnonce拒否
- **`test_verify_pow_different_difficulty`**: 異なる難易度での検証

#### TestGetDifficultyTarget（3テスト）
- **`test_get_difficulty_target_18_bits`**: 18ビット難易度目標
- **`test_get_difficulty_target_8_bits`**: 8ビット難易度目標
- **`test_get_difficulty_target_format`**: 目標値形式検証

### `test_api.py` - API統合テスト

FastAPIエンドポイントとビジネスロジックの統合テストです。

#### TestVoteEndpoint（3テスト）
- **`test_vote_initial_request`**: 初期投票リクエスト（第1段階）
- **`test_vote_full_submission`**: 完全投票プロセス（第1+第2段階）
- **`test_vote_duplicate_rejection`**: 重複投票の拒否

#### TestPollResultEndpoint（3テスト）
- **`test_poll_result_empty`**: 空の投票結果
- **`test_poll_result_with_votes`**: 投票データがある場合の結果
- **`test_poll_result_chain_integrity`**: チェーン整合性検証

#### TestPollAuditEndpoint（3テスト）
- **`test_poll_audit_empty`**: 空の監査証跡
- **`test_poll_audit_with_blocks`**: ブロックがある場合の監査
- **`test_poll_audit_chain_validation`**: チェーン検証状態

#### TestHealthEndpoint（1テスト）
- **`test_health_check`**: ヘルスチェックエンドポイント

#### TestErrorHandling（2テスト）
- **`test_vote_missing_fields`**: 必須フィールド不足エラー
- **`test_vote_invalid_pow`**: 無効なProof-of-Workエラー

## テスト実行方法

### 基本実行

```bash
# 全テスト実行
pytest

# 詳細出力
pytest -v

# 特定ファイルのみ
pytest tests/test_pow.py
pytest tests/test_api.py
```

### カバレッジ確認

```bash
# カバレッジ付きテスト
pytest --cov=app

# HTML形式のカバレッジレポート
pytest --cov=app --cov-report=html

# カバレッジレポートの確認
open htmlcov/index.html
```

### パフォーマンステスト

```bash
# 実行時間の測定
pytest --durations=10

# 特定のテストのプロファイリング
pytest tests/test_pow.py::TestComputeNonce::test_compute_nonce_easy_difficulty -v -s
```

## テスト環境

### テストデータベース

APIテストでは、各テストで独立したインメモリSQLiteデータベースを使用：

```python
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
```

### テスト専用難易度

実際のシステムよりも低い難易度でテストを高速化：

```python
# 本番: 18ビット（約262,144回試行）
# テスト: 6ビット（約64回試行）または4ビット（約16回試行）
```

### Fixture（テスト用データ）

- **`session`**: インメモリデータベースセッション
- **`client`**: FastAPIテストクライアント
- **依存性注入オーバーライド**: テスト用データベースへの接続

## 新しいテストの追加

### 1. PoW機能テストの追加

```python
# tests/test_pow.py内
class TestHashBlock:
    def test_new_hash_functionality(self):
        # 新しいハッシュ機能のテスト
        pass
```

### 2. APIテストの追加

```python
# tests/test_api.py内
class TestNewEndpoint:
    def test_new_endpoint_functionality(self, client: TestClient):
        response = client.get("/new-endpoint")
        assert response.status_code == 200
```

### 3. テストデータの作成

```python
# データベースに直接テストデータを追加
def test_with_existing_data(self, session: Session):
    # テストデータの作成
    block = Block(
        poll_id="test_poll",
        voter_hash="test_voter",
        choice="test_choice",
        timestamp=datetime.utcnow(),
        prev_hash="0" * 64,
        nonce=12345,
        block_hash="test_hash"
    )
    session.add(block)
    session.commit()
    
    # テスト実行
    # ...
```

## トラブルシューティング

### よくある問題

1. **"No module named pytest"**
   ```bash
   pip install -r requirements.txt
   ```

2. **"Database is locked"**
   - テスト間でセッションが適切にクリアされていない
   - Fixtureの`yield`使用を確認

3. **"PoW verification failed"**
   - テスト用の低難易度設定を確認
   - nonce計算のタイムアウト値を調整

### デバッグモード

```bash
# 詳細ログ付きテスト
pytest -v -s --log-cli-level=DEBUG

# 特定のテストのみデバッグ
pytest tests/test_api.py::TestVoteEndpoint::test_vote_full_submission -v -s
```

## 継続的インテグレーション

テストは以下の環境で自動実行されます：

- **Python 3.12+**
- **SQLite 3.x**
- **仮想環境（venv）**

すべてのPull Requestで24/24テストの成功が必要です。

## 関連ドキュメント

- [プロジェクト全体の概要](../readme.md)
- [アプリケーション実装詳細](../app/README.md)
- [API使用方法](../readme.md#api使用方法)