# 選択肢形式投票機能の実装

## 概要

投票の選択肢入力を自由入力から事前定義の選択肢形式に変更する。
`poll_options` テーブルを追加し、投票作成時に選択肢を登録できるようにする。
投票時は登録済み選択肢を番号で選択する方式に変更する。

## ToDo

- [x] `models.py` に `PollOption` モデル（`poll_options` テーブル）を追加
- [x] `cli.py` のメニューに「投票を作成する」を追加（番号を 1〜7 にシフト）
- [x] `cli.py` に `handle_create_poll()` メソッドを実装
  - poll_id を入力
  - 選択肢を複数入力（空行で終了）
  - `poll_options` テーブルに保存
- [x] `cli.py` の `handle_vote()` を修正
  - poll_id 入力後に `poll_options` から選択肢を取得
  - 選択肢が未登録の場合はエラーを表示
  - 選択肢を番号リストで表示し、番号で投票
- [x] `sql_functions.py` の `init_database()` に `poll_options` テーブルの DDL を追加

## Review

### 変更内容

- **`app/models.py`**: `PollOption` モデル（`poll_options` テーブル）を追加。`poll_id` と `option_text` フィールドを持つ。
- **`app/sql_functions.py`**: `init_database()` に `poll_options` テーブルの DROP/CREATE DDL を追加。
- **`app/cli.py`**:
  - `PollOption` をインポート。
  - メニューに「📝 投票を作成する」を追加し、番号を 1〜7 にシフト。
  - `handle_create_poll()` を新規実装（poll_id・選択肢を入力し `poll_options` に保存）。
  - `handle_vote()` を修正：自由入力から `poll_options` 取得→番号選択方式に変更。未登録の場合はエラーを表示。
  - `run()` のルーティングを 1〜7 に対応。
- **`tests/test_cli.py`**: `handle_vote()` 変更に伴いテストを3件更新（`PollOption` 事前登録・番号入力フロー対応）。全49件パス。
