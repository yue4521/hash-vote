# HashVote - Proof-of-Work投票システム

HashVoteは、ブロックチェーン技術とProof-of-Work（PoW）アルゴリズムを使用した分散型投票システムです。各投票は暗号学的に検証可能なブロックとして記録され、改ざん耐性のある投票記録を実現します。

## 特徴

- **Proof-of-Work**: 18ビットの先頭ゼロ要件による投票の計算的証明
- **ブロックチェーン**: 各投票を連鎖したブロック構造で管理
- **改ざん検証**: チェーン全体の整合性をリアルタイムで検証
- **重複投票防止**: (poll_id, voter_hash)の組み合わせによる一意性保証
- **完全監査**: 全投票履歴の透明性と検証可能性

## 技術スタック

- **Python 3.12+**
- **FastAPI** - RESTful API
- **SQLModel** - データベースORM
- **SQLite** - 永続化ストレージ
- **Uvicorn** - ASGIサーバー
- **pytest** - テストフレームワーク

## セットアップ

### 1. 依存関係のインストール

```bash
# 仮想環境の作成（推奨）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# または
venv\Scripts\activate     # Windows

# 依存関係のインストール
pip install -r requirements.txt
```

### 2. アプリケーションの起動

```bash
python -m uvicorn hashvote.main:app --reload
```

サーバーが起動したら、以下のURLでアクセス可能になります：
- API: http://localhost:8000
- ドキュメント: http://localhost:8000/docs
- 代替ドキュメント: http://localhost:8000/redoc

## API使用方法

### 投票の流れ

HashVoteは2段階の投票プロセスを採用しています：

#### 段階1: 初期リクエスト
```bash
curl -X POST "http://localhost:8000/vote" \
  -H "Content-Type: application/json" \
  -d '{
    "poll_id": "election_2024",
    "choice": "candidate_a",
    "voter_hash": "unique_voter_identifier"
  }'
```

レスポンス:
```json
{
  "difficulty_target": "000003ffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
  "prev_hash": "0000000000000000000000000000000000000000000000000000000000000000",
  "message": "Compute nonce with 18-bit leading zero requirement"
}
```

#### 段階2: PoW計算とnonce提出

クライアント側でnonce計算を実行：

```python
from hashvote.pow import compute_nonce
from datetime import datetime

# 段階1で取得したprev_hashを使用
nonce = compute_nonce(
    poll_id="election_2024",
    voter_hash="unique_voter_identifier", 
    choice="candidate_a",
    timestamp=datetime.utcnow(),
    prev_hash="prev_hash_from_step1",
    difficulty_bits=18
)
```

nonceを含む最終提出：
```bash
curl -X POST "http://localhost:8000/vote" \
  -H "Content-Type: application/json" \
  -d '{
    "poll_id": "election_2024",
    "choice": "candidate_a", 
    "voter_hash": "unique_voter_identifier",
    "nonce": 123456
  }'
```

### 結果の確認

#### 投票結果の取得
```bash
curl "http://localhost:8000/poll/election_2024/result"
```

レスポンス:
```json
{
  "poll_id": "election_2024",
  "total_votes": 150,
  "choices": {
    "candidate_a": 75,
    "candidate_b": 50,
    "candidate_c": 25
  }
}
```

#### 監査ログの取得
```bash
curl "http://localhost:8000/poll/election_2024/audit"
```

レスポンス:
```json
{
  "poll_id": "election_2024",
  "blocks": [
    {
      "id": 1,
      "poll_id": "election_2024",
      "voter_hash": "unique_voter_identifier",
      "choice": "candidate_a",
      "timestamp": "2024-01-01T12:00:00",
      "prev_hash": "0000000000000000000000000000000000000000000000000000000000000000",
      "nonce": 123456,
      "block_hash": "000001a2b3c4d5e6f7..."
    }
  ],
  "chain_valid": true
}
```

## テストの実行

```bash
# 全テスト実行
pytest

# カバレッジ付きテスト
pytest --cov=hashvote

# 特定テストファイル実行
pytest tests/test_pow.py
pytest tests/test_api.py
```

## ブロック構造

各投票ブロックは以下の構造を持ちます：

```python
{
    "poll_id": str,        # 投票ID
    "voter_hash": str,     # 投票者識別ハッシュ
    "choice": str,         # 投票選択肢
    "timestamp": datetime, # ブロック作成時刻
    "prev_hash": str,      # 前ブロックのハッシュ
    "nonce": int,          # Proof-of-Work nonce値
    "block_hash": str      # このブロックのSHA-256ハッシュ
}
```

ブロックハッシュは以下で計算されます：
```
block_hash = SHA-256(poll_id + voter_hash + choice + timestamp + prev_hash + nonce)
```

## Proof-of-Work仕様

- **難易度**: 18ビットの先頭ゼロ（約262,144回の平均試行回数）
- **アルゴリズム**: SHA-256
- **目標**: `hash_value < 2^(256-18) = 2^238`
- **16進表現**: ハッシュが`000000`から`0003ff`の範囲で開始

## セキュリティ考慮事項

### 前提条件
- **一意な投票者識別**: voter_hashは投票者ごとに一意である必要があります
- **nonce計算**: クライアント側でのPoW計算が必要（計算リソースによる証明）
- **タイムスタンプ**: サーバー側でタイムスタンプを管理（時系列の保証）

### 保護機能
- **重複投票防止**: (poll_id, voter_hash)の組み合わせで一意性保証
- **改ざん検証**: チェーン全体の暗号学的整合性チェック
- **計算的証明**: PoWによる投票コストの明示化

### 制限事項
- **Sybil攻撃**: voter_hash管理は外部システムに依存
- **51%攻撃**: 単一ノード実装のため分散合意なし
- **DoS攻撃**: PoW計算コストによる部分的軽減のみ

## プロジェクト構造

```
hash-vote/
├── hashvote/
│   ├── __init__.py
│   ├── main.py          # FastAPIアプリケーション
│   ├── models.py        # データモデル定義
│   ├── pow.py           # Proof-of-Work実装
│   └── database.py      # データベース設定
├── tests/
│   ├── __init__.py
│   ├── test_pow.py      # PoW機能テスト
│   └── test_api.py      # API機能テスト
├── requirements.txt     # Python依存関係
├── README.md           # このファイル
└── .gitignore          # Git除外設定
```

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 開発・貢献

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. Pull Requestを作成

## サポート

質問や問題がある場合は、GitHubのIssuesでお知らせください。
