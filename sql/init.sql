-- HashVote データベース初期化スクリプト
-- このスクリプトはデータベースを完全に初期化し、テーブルとインデックスを作成します

-- 既存のテーブルを削除（存在する場合）
DROP TABLE IF EXISTS blocks;

-- ブロックテーブル作成
-- 各ブロックは一つの投票を表し、ブロックチェーン構造を形成します
CREATE TABLE blocks (
    -- プライマリキー（自動増分）
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- 投票ID（どの投票に対するものか）
    poll_id VARCHAR NOT NULL,
    
    -- 投票者のハッシュ（プライバシー保護のため）
    voter_hash VARCHAR NOT NULL,
    
    -- 投票の選択肢
    choice VARCHAR NOT NULL,
    
    -- 投票時刻（UTC）
    timestamp DATETIME NOT NULL,
    
    -- 前のブロックのハッシュ（ブロックチェーン構造）
    prev_hash VARCHAR NOT NULL,
    
    -- Proof of Work のナンス値
    nonce INTEGER NOT NULL,
    
    -- このブロックのハッシュ値（一意）
    block_hash VARCHAR NOT NULL UNIQUE,
    
    -- 制約：同じ投票で同じ投票者は一度しか投票できない
    CONSTRAINT unique_vote UNIQUE (poll_id, voter_hash)
);

-- インデックス作成（クエリ性能向上のため）

-- 投票ID別の検索用インデックス
CREATE INDEX ix_blocks_poll_id ON blocks (poll_id);

-- ブロックハッシュ検索用インデックス
CREATE INDEX ix_blocks_block_hash ON blocks (block_hash);

-- 時系列検索用インデックス
CREATE INDEX ix_blocks_timestamp ON blocks (timestamp);

-- 投票者別検索用インデックス
CREATE INDEX ix_blocks_voter_hash ON blocks (voter_hash);

-- 複合インデックス：投票ID + 時系列順での検索最適化
CREATE INDEX ix_blocks_poll_timestamp ON blocks (poll_id, timestamp);

-- 初期化完了メッセージ用のビュー作成
-- （このビューは実際のデータではなく、初期化確認用）
CREATE VIEW database_info AS
SELECT 
    'HashVote Database' as database_name,
    '1.1.0' as version,
    datetime('now') as initialized_at,
    'Proof of Work Voting System' as description;

-- 初期化スクリプト実行ログ用テーブル（オプション）
CREATE TABLE IF NOT EXISTS init_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    script_name VARCHAR NOT NULL,
    executed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    version VARCHAR,
    notes TEXT
);

-- 初期化ログ記録
INSERT INTO init_log (script_name, version, notes) 
VALUES ('init.sql', '1.1.0', 'Database initialization completed');

-- 統計情報確認用ビュー
CREATE VIEW blocks_summary AS
SELECT 
    COUNT(*) as total_blocks,
    COUNT(DISTINCT poll_id) as unique_polls,
    COUNT(DISTINCT voter_hash) as unique_voters,
    MIN(timestamp) as first_vote,
    MAX(timestamp) as last_vote
FROM blocks;