# 技術仕様

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

## 技術スタック

- **Python 3.12+**
- **SQLModel** - データベースORM
- **SQLite** - 永続化ストレージ
- **pytest** - テストフレームワーク