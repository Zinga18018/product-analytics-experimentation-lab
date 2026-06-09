-- Product Analytics Experimentation Lab
-- Interview-style SQL queries for product data science and analytics roles.

-- 1. Funnel by experiment variant
WITH user_events AS (
    SELECT
        ea.variant,
        ea.user_id,
        MAX(CASE WHEN e.event_name = 'view_landing' THEN 1 ELSE 0 END) AS viewed_landing,
        MAX(CASE WHEN e.event_name = 'view_product' THEN 1 ELSE 0 END) AS viewed_product,
        MAX(CASE WHEN e.event_name = 'start_checkout' THEN 1 ELSE 0 END) AS started_checkout,
        MAX(CASE WHEN e.event_name = 'purchase' THEN 1 ELSE 0 END) AS purchased
    FROM experiment_assignments ea
    LEFT JOIN events e
        ON ea.user_id = e.user_id
    GROUP BY ea.variant, ea.user_id
)
SELECT
    variant,
    COUNT(*) AS assigned_users,
    SUM(viewed_landing) AS viewed_landing_users,
    SUM(viewed_product) AS viewed_product_users,
    SUM(started_checkout) AS checkout_users,
    SUM(purchased) AS purchase_users,
    ROUND(1.0 * SUM(purchased) / COUNT(*), 4) AS purchase_rate
FROM user_events
GROUP BY variant;

-- 2. Acquisition-channel revenue per user
SELECT
    u.acquisition_channel,
    COUNT(DISTINCT u.user_id) AS users,
    COUNT(DISTINCT CASE WHEN e.event_name = 'purchase' THEN u.user_id END) AS purchasers,
    ROUND(SUM(e.revenue), 2) AS revenue,
    ROUND(SUM(e.revenue) / COUNT(DISTINCT u.user_id), 2) AS revenue_per_user
FROM users u
LEFT JOIN events e
    ON u.user_id = e.user_id
GROUP BY u.acquisition_channel
ORDER BY revenue_per_user DESC;

-- 3. Weekly cohort retention
WITH first_seen AS (
    SELECT
        user_id,
        DATE(signup_date) AS signup_date,
        STRFTIME('%Y-%W', signup_date) AS signup_week
    FROM users
),
activity AS (
    SELECT DISTINCT
        fs.user_id,
        fs.signup_week,
        CAST(JULIANDAY(s.session_date) - JULIANDAY(fs.signup_date) AS INTEGER) AS days_after_signup
    FROM first_seen fs
    JOIN sessions s
        ON fs.user_id = s.user_id
)
SELECT
    signup_week,
    COUNT(DISTINCT user_id) AS cohort_users,
    ROUND(1.0 * COUNT(DISTINCT CASE WHEN days_after_signup BETWEEN 1 AND 7 THEN user_id END)
          / COUNT(DISTINCT user_id), 4) AS retention_7d,
    ROUND(1.0 * COUNT(DISTINCT CASE WHEN days_after_signup BETWEEN 8 AND 14 THEN user_id END)
          / COUNT(DISTINCT user_id), 4) AS retention_14d,
    ROUND(1.0 * COUNT(DISTINCT CASE WHEN days_after_signup BETWEEN 15 AND 30 THEN user_id END)
          / COUNT(DISTINCT user_id), 4) AS retention_30d
FROM activity
GROUP BY signup_week
ORDER BY signup_week;
