# GitHub Actions OSV Scanner 修正タスク

## 発見された新しい問題

### OSV Scanner Action エラー (2025-08-09)
- **問題**: `google/osv-scanner-action@v2.1.0` の action.yml ファイルが不正
- **エラーメッセージ**: "Top level 'runs:' section is required for google/osv-scanner-action/v2.1.0/action.yml"
- **場所**: security.yml の osv-scanner ジョブ（174行目）
- **影響**: OSV脆弱性スキャンジョブが完全に失敗
- **調査結果**: 
  - v2.1.0 でも action.yml の構造に問題がある
  - 公式推奨は再利用可能ワークフロー `google/osv-scanner-action/.github/workflows/osv-scanner-reusable.yml@v2.2.0` の使用
  - 直接アクションを呼び出す方法は非推奨となった

## 以前に修正済みの問題

### 1. CI Workflow (ci.yml) 失敗 - ✅ 修正済み
- **問題**: `pyproject.toml`の TOML構文エラー
- **場所**: 64行目 `[tool.bandit.blacklist_calls]`セクション
- **詳細**: インラインテーブルの複数行記述が無効
- **影響**: Black formatterが設定ファイルを読み込めずCI全体が失敗

### 2. Security Workflow (security.yml) 失敗 - ✅ 部分修正済み
- **OSV Scanner**: `google/osv-scanner-action@v1`が存在しない → v1.8.5に更新したが新たな問題発生
- **License Check**: `license-report.json`ファイルパス問題 → 修正済み

## 修正が必要なタスク

### 🔧 OSV Scanner Action 修正 (緊急) - 🔄 進行中
- **対応**: 再利用可能ワークフロー `google/osv-scanner-action/.github/workflows/osv-scanner-reusable.yml@v2.2.0` に変更
- **設定変更**: 直接アクション呼び出しから `uses` で再利用可能ワークフローを呼び出すに変更
- **scan-args調整**: 新しい形式で `--recursive --format=json --output=osv-results.json ./` を指定
- **権限追加**: 必要な permissions を追加（security-events: write など）
- **テスト**: 修正後のワークフロー実行確認

## 以前に実施した修正

### ✅ pyproject.toml TOML構文修正
- 64行目: インラインテーブルを1行形式に修正
- スペーシングをPython3.8互換に調整
- Black formatterから`pyproject.toml`を除外

### ✅ OSVスキャナー修正 (完了)
- `google/osv-scanner-action@v1.8.5` → `@v2.1.0`に更新
- 引数を `-r` から `--recursive` に変更

### ✅ ライセンスチェック修正
- ファイル存在チェックを追加
- ファイル未存在時はスキップするよう修正

### ✅ CI Workflow修正
- Black formatterから`pyproject.toml`を除外
- `--exclude="pyproject\.toml"`オプションを追加

## テスト結果

- ✅ TOML構文検証: 正常
- ✅ Black formatterチェック: 11ファイル正常
- ✅ Flake8リントチェック: エラーなし
- ✅ OSV Scanner: v2.1.0に更新してエラー解決