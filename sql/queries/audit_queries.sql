-- 監査・セキュリティ分析クエリ集
-- ブロックチェーンの整合性とセキュリティ検証のためのクエリ集

-- =================================
-- ブロックチェーン整合性チェック
-- =================================

-- 前ブロックハッシュ整合性チェック
-- 各ブロックの前ブロックハッシュが正しく連鎖しているかを確認
WITH hash_chain AS (
    SELECT 
        b1.id as current_id,
        b1.poll_id,
        b1.block_hash as current_hash,
        b1.prev_hash as declared_prev_hash,
        b2.block_hash as actual_prev_hash,
        CASE 
            WHEN b1.prev_hash = '0000000000000000000000000000000000000000000000000000000000000000' 
            THEN 'GENESIS'
            WHEN b1.prev_hash = b2.block_hash 
            THEN 'VALID'
            ELSE 'INVALID'
        END as chain_status
    FROM blocks b1
    LEFT JOIN blocks b2 ON b1.poll_id = b2.poll_id 
                       AND b2.timestamp < b1.timestamp
                       AND b2.id = (
                           SELECT MAX(id) 
                           FROM blocks b3 
                           WHERE b3.poll_id = b1.poll_id 
                           AND b3.timestamp < b1.timestamp
                       )
)
SELECT 
    poll_id,
    chain_status,
    COUNT(*) as block_count,
    GROUP_CONCAT(current_id) as block_ids
FROM hash_chain 
GROUP BY poll_id, chain_status
ORDER BY poll_id, chain_status;

-- ブロック順序整合性チェック
-- IDと時刻の順序が一致しているかを確認
SELECT 
    poll_id,
    COUNT(*) as total_blocks,
    COUNT(CASE 
        WHEN id < LAG(id) OVER (PARTITION BY poll_id ORDER BY timestamp) 
        THEN 1 
    END) as id_order_violations,
    COUNT(CASE 
        WHEN timestamp < LAG(timestamp) OVER (PARTITION BY poll_id ORDER BY id) 
        THEN 1 
    END) as timestamp_order_violations
FROM blocks 
GROUP BY poll_id
HAVING id_order_violations > 0 OR timestamp_order_violations > 0;

-- =================================
-- 重複投票検出
-- =================================

-- 同一投票者による重複投票
-- データベース制約では防げない論理的重複をチェック
SELECT 
    poll_id,
    voter_hash,
    COUNT(*) as vote_count,
    GROUP_CONCAT(choice) as all_choices,
    GROUP_CONCAT(id) as block_ids,
    MIN(timestamp) as first_vote,
    MAX(timestamp) as last_vote
FROM blocks 
GROUP BY poll_id, voter_hash 
HAVING COUNT(*) > 1
ORDER BY vote_count DESC, poll_id;

-- 同一ブロックハッシュの重複
-- 異なるブロックが同じハッシュを持つ場合（理論上ありえない）
SELECT 
    block_hash,
    COUNT(*) as duplicate_count,
    GROUP_CONCAT(id) as block_ids,
    GROUP_CONCAT(DISTINCT poll_id) as poll_ids
FROM blocks 
GROUP BY block_hash 
HAVING COUNT(*) > 1;

-- =================================
-- 異常パターン検出
-- =================================

-- 短時間内の大量投票（潜在的な不正行為）
-- 同一投票者または同一IPからの異常な投票頻度を検出
WITH vote_intervals AS (
    SELECT 
        voter_hash,
        poll_id,
        timestamp,
        LAG(timestamp) OVER (PARTITION BY voter_hash ORDER BY timestamp) as prev_timestamp,
        (julianday(timestamp) - julianday(LAG(timestamp) OVER (PARTITION BY voter_hash ORDER BY timestamp))) * 24 * 60 * 60 as seconds_since_last
    FROM blocks
)
SELECT 
    voter_hash,
    COUNT(*) as rapid_votes,
    MIN(seconds_since_last) as min_interval_seconds,
    AVG(seconds_since_last) as avg_interval_seconds,
    GROUP_CONCAT(DISTINCT poll_id) as polls_involved
FROM vote_intervals 
WHERE seconds_since_last < 60  -- 60秒以内の連続投票
GROUP BY voter_hash 
HAVING COUNT(*) > 1
ORDER BY rapid_votes DESC;

-- 異常なナンス値パターン
-- 通常の分布から外れたナンス値を持つブロック
WITH nonce_stats AS (
    SELECT 
        AVG(nonce) as avg_nonce,
        (SELECT nonce FROM blocks ORDER BY nonce LIMIT 1 OFFSET (SELECT COUNT(*)/2 FROM blocks)) as median_nonce,
        MIN(nonce) as min_nonce,
        MAX(nonce) as max_nonce
    FROM blocks
)
SELECT 
    b.id,
    b.poll_id,
    b.nonce,
    b.timestamp,
    CASE 
        WHEN b.nonce < s.avg_nonce * 0.1 THEN 'SUSPICIOUSLY_LOW'
        WHEN b.nonce > s.avg_nonce * 10 THEN 'SUSPICIOUSLY_HIGH'
        ELSE 'NORMAL'
    END as nonce_category
FROM blocks b
CROSS JOIN nonce_stats s
WHERE b.nonce < s.avg_nonce * 0.1 OR b.nonce > s.avg_nonce * 10
ORDER BY b.nonce;

-- =================================
-- 投票パターン分析
-- =================================

-- 投票者の行動パターン分析
-- 同一投票者の投票間隔と選択パターンを分析
SELECT 
    voter_hash,
    COUNT(DISTINCT poll_id) as polls_participated,
    COUNT(DISTINCT choice) as unique_choices_used,
    ROUND(AVG(
        (julianday(timestamp) - julianday(LAG(timestamp) OVER (PARTITION BY voter_hash ORDER BY timestamp))) * 24 * 60
    ), 2) as avg_minutes_between_votes,
    MIN(timestamp) as first_activity,
    MAX(timestamp) as last_activity
FROM blocks 
GROUP BY voter_hash 
HAVING COUNT(*) > 1
ORDER BY polls_participated DESC, avg_minutes_between_votes;

-- 投票選択肢の相関分析
-- 特定の選択肢を選ぶ投票者が他の投票でどの選択肢を選ぶかを分析
WITH voter_choices AS (
    SELECT 
        voter_hash,
        poll_id,
        choice,
        ROW_NUMBER() OVER (PARTITION BY voter_hash ORDER BY timestamp) as vote_sequence
    FROM blocks
),
choice_transitions AS (
    SELECT 
        v1.choice as choice_1,
        v2.choice as choice_2,
        COUNT(*) as transition_count
    FROM voter_choices v1
    JOIN voter_choices v2 ON v1.voter_hash = v2.voter_hash 
                         AND v1.vote_sequence = v2.vote_sequence - 1
    GROUP BY v1.choice, v2.choice
)
SELECT 
    choice_1,
    choice_2,
    transition_count,
    ROUND(
        transition_count * 100.0 / SUM(transition_count) OVER (PARTITION BY choice_1), 2
    ) as percentage_from_choice_1
FROM choice_transitions 
ORDER BY transition_count DESC;

-- =================================
-- セキュリティメトリクス
-- =================================

-- Proof of Work セキュリティ評価
-- 各投票の計算難易度とセキュリティレベルを評価
SELECT 
    poll_id,
    COUNT(*) as total_blocks,
    AVG(nonce) as avg_computational_effort,
    MIN(nonce) as min_effort,
    MAX(nonce) as max_effort,
    SUM(nonce) as total_computational_work,
    CASE 
        WHEN AVG(nonce) > 1000000 THEN 'HIGH_SECURITY'
        WHEN AVG(nonce) > 100000 THEN 'MEDIUM_SECURITY'
        ELSE 'LOW_SECURITY'
    END as security_level
FROM blocks 
GROUP BY poll_id 
ORDER BY avg_computational_effort DESC;

-- ブロック生成時間分析
-- ブロック間の生成時間間隔を分析（マイニング難易度の妥当性確認）
WITH block_intervals AS (
    SELECT 
        poll_id,
        id,
        timestamp,
        LAG(timestamp) OVER (PARTITION BY poll_id ORDER BY id) as prev_timestamp,
        (julianday(timestamp) - julianday(LAG(timestamp) OVER (PARTITION BY poll_id ORDER BY id))) * 24 * 60 as minutes_since_prev
    FROM blocks
)
SELECT 
    poll_id,
    COUNT(*) as intervals_measured,
    ROUND(AVG(minutes_since_prev), 2) as avg_minutes_between_blocks,
    ROUND(MIN(minutes_since_prev), 2) as min_interval,
    ROUND(MAX(minutes_since_prev), 2) as max_interval,
    COUNT(CASE WHEN minutes_since_prev < 1 THEN 1 END) as blocks_under_1min,
    COUNT(CASE WHEN minutes_since_prev > 60 THEN 1 END) as blocks_over_1hour
FROM block_intervals 
WHERE minutes_since_prev IS NOT NULL
GROUP BY poll_id 
ORDER BY avg_minutes_between_blocks;

-- =================================
-- 監査レポート統合
-- =================================

-- 包括的監査サマリー
-- 主要な監査項目をまとめたレポート
SELECT 
    'Total Blocks' as metric,
    CAST(COUNT(*) as TEXT) as value,
    'Blocks in database' as description
FROM blocks

UNION ALL

SELECT 
    'Unique Polls',
    CAST(COUNT(DISTINCT poll_id) as TEXT),
    'Different voting sessions'
FROM blocks

UNION ALL

SELECT 
    'Unique Voters',
    CAST(COUNT(DISTINCT voter_hash) as TEXT),
    'Distinct voters (by hash)'
FROM blocks

UNION ALL

SELECT 
    'Average Nonce',
    CAST(ROUND(AVG(nonce)) as TEXT),
    'Average computational effort'
FROM blocks

UNION ALL

SELECT 
    'Chain Integrity',
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
    'Duplicate hash check'
FROM (
    SELECT block_hash 
    FROM blocks 
    GROUP BY block_hash 
    HAVING COUNT(*) > 1
)

UNION ALL

SELECT 
    'Voting Integrity',
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
    'Duplicate voter check'
FROM (
    SELECT poll_id, voter_hash 
    FROM blocks 
    GROUP BY poll_id, voter_hash 
    HAVING COUNT(*) > 1
);