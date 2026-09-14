-- Interview examples. Bind :experiment_name, :as_of, :horizon_days,
-- :conversion_days from config/experiment_policy.json.
-- The complete validated decision path is src/analytics.py.

-- 1. Conversion denominator includes every fully observed assigned user.
-- The purchase window is [assignment, assignment + conversion_days).
WITH eligible AS (
  SELECT user_id, variant, assigned_at FROM experiment_assignments
  WHERE experiment_name = :experiment_name
    AND JULIANDAY(assigned_at) + :horizon_days <= JULIANDAY(:as_of)
), user_outcomes AS (
  SELECT a.user_id, a.variant,
    MAX(CASE WHEN e.event_name = 'purchase' THEN 1 ELSE 0 END) AS purchased
  FROM eligible a LEFT JOIN events e ON e.user_id = a.user_id
    AND JULIANDAY(e.event_time) >= JULIANDAY(a.assigned_at)
    AND JULIANDAY(e.event_time) < JULIANDAY(a.assigned_at) + :conversion_days
  GROUP BY a.user_id, a.variant
)
SELECT variant, COUNT(*) AS eligible_assigned_users,
  SUM(purchased) AS purchasers, 1.0 * SUM(purchased) / COUNT(*) AS purchase_rate
FROM user_outcomes GROUP BY variant;

-- 2. Descriptive all-observed-time channel revenue, not causal experiment evidence.
SELECT u.acquisition_channel, COUNT(DISTINCT u.user_id) AS users,
  COUNT(DISTINCT CASE WHEN e.event_name = 'purchase' THEN u.user_id END) AS purchasers,
  COALESCE(SUM(CASE WHEN e.event_name = 'purchase' THEN e.revenue ELSE 0 END), 0) AS revenue,
  COALESCE(SUM(CASE WHEN e.event_name = 'purchase' THEN e.revenue ELSE 0 END), 0)
    / COUNT(DISTINCT u.user_id) AS revenue_per_user
FROM users u LEFT JOIN events e ON u.user_id = e.user_id
GROUP BY u.acquisition_channel ORDER BY revenue_per_user DESC;

-- 3. Signup-cohort retention days 1-7. Includes inactive users; mature denominator.
-- Use end-exclusive +15 for days 8-14 and +31 for days 15-30.
WITH user_windows AS (
  SELECT u.user_id, STRFTIME('%Y-%W', u.signup_date) AS signup_week,
    JULIANDAY(u.signup_date) + 8 <= JULIANDAY(:as_of) AS eligible,
    MAX(CASE WHEN JULIANDAY(s.session_started_at) >= JULIANDAY(u.signup_date) + 1
      AND JULIANDAY(s.session_started_at) < JULIANDAY(u.signup_date) + 8
      THEN 1 ELSE 0 END) AS retained
  FROM users u LEFT JOIN sessions s ON u.user_id = s.user_id
    AND JULIANDAY(s.session_started_at) < JULIANDAY(:as_of)
  WHERE JULIANDAY(u.signup_date) < JULIANDAY(:as_of)
  GROUP BY u.user_id, u.signup_date
)
SELECT signup_week, COUNT(*) AS cohort_users,
  SUM(eligible) AS eligible_7d_users, SUM(retained * eligible) AS retained_7d_users,
  1.0 * SUM(retained * eligible) / NULLIF(SUM(eligible), 0) AS retention_7d
FROM user_windows GROUP BY signup_week ORDER BY signup_week;
