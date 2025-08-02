# HashVoteテストスイート

HashVoteシステムの包括的なテストが含まれています。

## テスト概要

**総テスト数**: 24テスト  
**構成**: PoW機能テスト（12）+ API統合テスト（12）

```
tests/
├── test_pow.py      # Proof-of-Work機能テスト
├── test_api.py      # API統合テスト  
└── __init__.py      # パッケージ初期化
```

## テスト実行

```bash
# 全テスト実行
pytest

# カバレッジ付きテスト
pytest --cov=app

# 詳細出力
pytest -v

# 特定ファイル実行
pytest tests/test_pow.py
pytest tests/test_api.py
```

## 関連ドキュメント

- [詳細なテスト仕様と実行方法](../docs/testing.md)
- [開発ガイド](../docs/development.md)
- [API使用方法](../docs/api-usage.md)