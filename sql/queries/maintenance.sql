-- データベースメンテナンス・管理クエリ集
-- データベースの最適化、クリーンアップ、管理操作のためのクエリ集

-- =================================
-- データベース情報・統計
-- =================================

-- データベース全般情報
-- ファイルサイズ、テーブル情報、インデックス情報を表示
SELECT 
    'Database' as info_type,
    'hashvote.db' as name,
    'SQLite' as engine,
    datetime('now') as checked_at;

-- テーブル一覧と基本情報
SELECT 
    name as table_name,
    type as object_type,
    sql as definition
FROM sqlite_master 
WHERE type IN ('table', 'view', 'index')
ORDER BY type, name;

-- テーブルサイズ統計
SELECT 
    'blocks' as table_name,
    COUNT(*) as row_count,
    COUNT(DISTINCT poll_id) as unique_polls,
    COUNT(DISTINCT voter_hash) as unique_voters,
    MIN(timestamp) as oldest_record,
    MAX(timestamp) as newest_record
FROM blocks;

-- =================================
-- インデックス最適化
-- =================================

-- インデックス使用状況分析
-- 既存インデックスの効果を確認
PRAGMA index_list(blocks);

-- インデックス情報詳細
PRAGMA index_info(ix_blocks_poll_id);
PRAGMA index_info(ix_blocks_block_hash);
PRAGMA index_info(ix_blocks_timestamp);

-- データベース統計情報の更新
-- SQLiteの内部統計を更新してクエリ最適化を改善
ANALYZE;

-- =================================
-- データクリーンアップ
-- =================================

-- 重複レコード削除（安全版）
-- 重複を検出するが削除は手動確認後に実行
SELECT 
    poll_id,
    voter_hash,
    choice,
    COUNT(*) as duplicate_count,
    MIN(id) as keep_id,
    GROUP_CONCAT(id) as all_ids
FROM blocks 
GROUP BY poll_id, voter_hash, choice 
HAVING COUNT(*) > 1;

-- 古いテストデータの識別
-- テスト用データ（poll_idがtest_で始まる）を特定
SELECT 
    'Test Data' as data_type,
    COUNT(*) as record_count,
    MIN(timestamp) as oldest,
    MAX(timestamp) as newest
FROM blocks 
WHERE poll_id LIKE 'test_%';

-- 孤立ブロック検出
-- 前ブロックハッシュが存在しないブロック（チェーン不整合）
SELECT 
    b1.id,
    b1.poll_id,
    b1.prev_hash,
    'Orphaned block - previous hash not found' as issue
FROM blocks b1
LEFT JOIN blocks b2 ON b1.poll_id = b2.poll_id 
                   AND b1.prev_hash = b2.block_hash
WHERE b1.prev_hash != '0000000000000000000000000000000000000000000000000000000000000000'
  AND b2.id IS NULL;

-- =================================
-- パフォーマンス最適化
-- =================================

-- データベース整理
-- 削除されたレコードの領域を回収
VACUUM;

-- 統計情報の完全更新
-- クエリプランナーの統計を更新
ANALYZE sqlite_master;

-- インデックス再構築（必要時のみ実行）
-- 注意：大きなテーブルでは時間がかかる可能性があります
-- REINDEX;

-- =================================
-- バックアップ・復旧支援
-- =================================

-- バックアップ確認用データ
-- バックアップ前後でデータ整合性を確認
SELECT 
    'blocks' as table_name,
    COUNT(*) as total_records,
    COUNT(DISTINCT block_hash) as unique_hashes,
    MIN(id) as min_id,
    MAX(id) as max_id,
    datetime('now') as snapshot_time
FROM blocks;

-- エクスポート用基本データ
-- CSVエクスポートなどに使用する基本的なデータ選択
SELECT 
    id,
    poll_id,
    voter_hash,
    choice,
    datetime(timestamp) as timestamp_iso,
    prev_hash,
    nonce,
    block_hash
FROM blocks 
ORDER BY poll_id, timestamp;

-- =================================
-- データ品質管理
-- =================================

-- データ品質チェックリスト
WITH quality_checks AS (
    -- NULL値チェック
    SELECT 'NULL Values Check' as check_name,
           CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END as status,
           COUNT(*) as issue_count,
           'Critical: NULL values found in required fields' as description
    FROM blocks 
    WHERE poll_id IS NULL OR voter_hash IS NULL OR choice IS NULL 
       OR timestamp IS NULL OR block_hash IS NULL

    UNION ALL
    
    -- ハッシュ長チェック
    SELECT 'Hash Length Check',
           CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
           COUNT(*),
           'Block hashes must be 64 characters'
    FROM blocks 
    WHERE length(block_hash) != 64 OR length(prev_hash) != 64
    
    UNION ALL
    
    -- 未来日付チェック
    SELECT 'Future Timestamp Check',
           CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
           COUNT(*),
           'Timestamps cannot be in the future'
    FROM blocks 
    WHERE timestamp > datetime('now')
    
    UNION ALL
    
    -- 重複ハッシュチェック
    SELECT 'Unique Hash Check',
           CASE WHEN COUNT(*) = (SELECT COUNT(DISTINCT block_hash) FROM blocks) THEN 'PASS' ELSE 'FAIL' END,
           COUNT(*) - (SELECT COUNT(DISTINCT block_hash) FROM blocks),
           'All block hashes must be unique'
    FROM blocks
)
SELECT * FROM quality_checks ORDER BY status DESC, check_name;

-- データ分布チェック
-- 異常な分布を持つデータを識別
SELECT 
    'Poll Distribution' as metric,
    COUNT(DISTINCT poll_id) as unique_values,
    ROUND(AVG(vote_count), 2) as avg_per_poll,
    MIN(vote_count) as min_votes,
    MAX(vote_count) as max_votes
FROM (
    SELECT poll_id, COUNT(*) as vote_count 
    FROM blocks 
    GROUP BY poll_id
);

-- =================================
-- システムメンテナンス
-- =================================

-- データベース設定確認
PRAGMA database_list;
PRAGMA table_info(blocks);
PRAGMA foreign_key_list(blocks);

-- パフォーマンス設定
-- 注意：これらの設定は一時的で、接続終了時にリセットされます
PRAGMA cache_size = 10000;  -- キャッシュサイズを増加
PRAGMA temp_store = memory;  -- 一時データをメモリに保存

-- データベース整合性チェック
-- データベースファイルの物理的整合性を検証
PRAGMA integrity_check;

-- 高速整合性チェック（大きなDBで有用）
PRAGMA quick_check;

-- =================================
-- 監視・アラート用クエリ
-- =================================

-- 異常検知用メトリクス
-- 定期的な監視で使用する異常値検知
SELECT 
    'Recent Activity' as alert_type,
    CASE 
        WHEN COUNT(*) = 0 THEN 'WARNING: No votes in last 24 hours'
        WHEN COUNT(*) > 1000 THEN 'WARNING: Unusually high activity'
        ELSE 'NORMAL'
    END as status,
    COUNT(*) as recent_votes,
    datetime('now', '-24 hours') as check_period_start
FROM blocks 
WHERE timestamp > datetime('now', '-24 hours');

-- ストレージ使用量アラート
-- ファイルサイズが大きくなりすぎていないかチェック
SELECT 
    'Storage Usage' as alert_type,
    'Monitor database growth' as status,
    COUNT(*) as total_records,
    ROUND(COUNT(*) / 1000.0, 1) as estimated_mb_size,
    CASE 
        WHEN COUNT(*) > 100000 THEN 'Consider archiving old data'
        WHEN COUNT(*) > 50000 THEN 'Monitor growth closely'
        ELSE 'Storage levels normal'
    END as recommendation
FROM blocks;

-- =================================
-- 運用レポート生成
-- =================================

-- 日次運用レポート
-- 過去24時間の活動サマリー
SELECT 
    DATE('now') as report_date,
    COUNT(*) as votes_today,
    COUNT(DISTINCT poll_id) as active_polls_today,
    COUNT(DISTINCT voter_hash) as unique_voters_today,
    (SELECT COUNT(*) FROM blocks) as total_votes_all_time,
    (SELECT COUNT(DISTINCT poll_id) FROM blocks) as total_polls_all_time
FROM blocks 
WHERE DATE(timestamp) = DATE('now');

-- 週次パフォーマンスレポート
-- 過去7日間のトレンド分析
SELECT 
    DATE(timestamp) as activity_date,
    COUNT(*) as daily_votes,
    COUNT(DISTINCT poll_id) as daily_polls,
    AVG(nonce) as avg_mining_difficulty,
    MIN(timestamp) as first_vote_time,
    MAX(timestamp) as last_vote_time
FROM blocks 
WHERE timestamp > datetime('now', '-7 days')
GROUP BY DATE(timestamp)
ORDER BY activity_date DESC;