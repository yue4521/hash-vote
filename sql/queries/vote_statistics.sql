-- 投票統計クエリ集
-- 様々な角度から投票データを分析するためのクエリ集

-- =================================
-- 基本統計クエリ
-- =================================

-- 全体統計サマリー
-- 総投票数、投票ID数、投票者数などの基本情報
SELECT 
    COUNT(*) as total_votes,
    COUNT(DISTINCT poll_id) as unique_polls,
    COUNT(DISTINCT voter_hash) as unique_voters,
    MIN(timestamp) as first_vote_time,
    MAX(timestamp) as last_vote_time,
    ROUND(
        (julianday(MAX(timestamp)) - julianday(MIN(timestamp))) * 24 * 60, 2
    ) as voting_period_minutes
FROM blocks;

-- =================================
-- 投票ID別統計
-- =================================

-- 投票ID別の詳細統計
-- 各投票の参加者数、選択肢数、期間など
SELECT 
    poll_id,
    COUNT(*) as total_votes,
    COUNT(DISTINCT choice) as unique_choices,
    MIN(timestamp) as first_vote,
    MAX(timestamp) as last_vote,
    ROUND(
        (julianday(MAX(timestamp)) - julianday(MIN(timestamp))) * 24 * 60, 2
    ) as duration_minutes
FROM blocks 
GROUP BY poll_id 
ORDER BY total_votes DESC;

-- 投票ID別選択肢分布
-- 各投票における選択肢別の得票数と割合
SELECT 
    poll_id,
    choice,
    COUNT(*) as vote_count,
    ROUND(
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY poll_id), 2
    ) as percentage
FROM blocks 
GROUP BY poll_id, choice 
ORDER BY poll_id, vote_count DESC;

-- =================================
-- 時系列分析
-- =================================

-- 日別投票数
-- 投票活動の時系列パターンを分析
SELECT 
    DATE(timestamp) as vote_date,
    COUNT(*) as daily_votes,
    COUNT(DISTINCT poll_id) as active_polls,
    COUNT(DISTINCT voter_hash) as unique_voters
FROM blocks 
GROUP BY DATE(timestamp) 
ORDER BY vote_date;

-- 時間別投票数
-- 一日の中での投票パターンを分析
SELECT 
    strftime('%H', timestamp) as hour,
    COUNT(*) as hourly_votes,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM blocks), 2) as percentage
FROM blocks 
GROUP BY strftime('%H', timestamp) 
ORDER BY hour;

-- =================================
-- 投票者行動分析
-- =================================

-- 投票者別統計
-- 各投票者の投票パターン分析
SELECT 
    voter_hash,
    COUNT(*) as total_votes,
    COUNT(DISTINCT poll_id) as polls_participated,
    MIN(timestamp) as first_vote,
    MAX(timestamp) as last_vote
FROM blocks 
GROUP BY voter_hash 
ORDER BY total_votes DESC;

-- 複数投票参加者
-- 複数の投票に参加した投票者を特定
SELECT 
    voter_hash,
    COUNT(DISTINCT poll_id) as polls_count,
    GROUP_CONCAT(DISTINCT poll_id) as participated_polls
FROM blocks 
GROUP BY voter_hash 
HAVING COUNT(DISTINCT poll_id) > 1
ORDER BY polls_count DESC;

-- =================================
-- ブロックチェーン分析
-- =================================

-- ブロックハッシュ分析
-- ハッシュの分布や特徴を分析
SELECT 
    substr(block_hash, 1, 2) as hash_prefix,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM blocks), 2) as percentage
FROM blocks 
GROUP BY substr(block_hash, 1, 2) 
ORDER BY count DESC;

-- Proof of Work 難易度分析
-- ナンス値の分布を分析
SELECT 
    CASE 
        WHEN nonce < 100000 THEN 'Low (< 100k)'
        WHEN nonce < 1000000 THEN 'Medium (100k - 1M)'
        WHEN nonce < 10000000 THEN 'High (1M - 10M)'
        ELSE 'Very High (> 10M)'
    END as nonce_range,
    COUNT(*) as count,
    ROUND(AVG(nonce)) as avg_nonce,
    MIN(nonce) as min_nonce,
    MAX(nonce) as max_nonce
FROM blocks 
GROUP BY 
    CASE 
        WHEN nonce < 100000 THEN 'Low (< 100k)'
        WHEN nonce < 1000000 THEN 'Medium (100k - 1M)'
        WHEN nonce < 10000000 THEN 'High (1M - 10M)'
        ELSE 'Very High (> 10M)'
    END
ORDER BY avg_nonce;

-- =================================
-- トップランキング
-- =================================

-- 最も人気の選択肢（全投票通算）
SELECT 
    choice,
    COUNT(*) as total_votes,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM blocks), 2) as percentage_of_all,
    COUNT(DISTINCT poll_id) as polls_appeared
FROM blocks 
GROUP BY choice 
ORDER BY total_votes DESC 
LIMIT 10;

-- 最も活発な投票ID
SELECT 
    poll_id,
    COUNT(*) as total_votes,
    COUNT(DISTINCT choice) as choice_options,
    ROUND(
        (julianday(MAX(timestamp)) - julianday(MIN(timestamp))) * 24 * 60, 2
    ) as duration_minutes,
    ROUND(COUNT(*) / MAX(1, (julianday(MAX(timestamp)) - julianday(MIN(timestamp))) * 24 * 60), 2) as votes_per_minute
FROM blocks 
GROUP BY poll_id 
ORDER BY total_votes DESC 
LIMIT 10;

-- =================================
-- データ品質チェック
-- =================================

-- 異常なデータのチェック
-- 将来日付、重複、異常値などをチェック
SELECT 
    'Future timestamps' as check_type,
    COUNT(*) as count
FROM blocks 
WHERE timestamp > datetime('now')

UNION ALL

SELECT 
    'Duplicate block hashes' as check_type,
    COUNT(*) - COUNT(DISTINCT block_hash) as count
FROM blocks

UNION ALL

SELECT 
    'Invalid previous hash format' as check_type,
    COUNT(*) as count
FROM blocks 
WHERE length(prev_hash) != 64

UNION ALL

SELECT 
    'Invalid block hash format' as check_type,
    COUNT(*) as count
FROM blocks 
WHERE length(block_hash) != 64;