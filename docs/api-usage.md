# API使用方法詳細

## 投票の流れ

HashVoteは2段階の投票プロセスを採用しています：

### 段階1: 初期リクエスト
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

### 段階2: PoW計算とnonce提出

クライアント側でnonce計算を実行：

```python
from app.pow import compute_nonce
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

## 結果の確認

### 投票結果の取得
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

### 監査ログの取得
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