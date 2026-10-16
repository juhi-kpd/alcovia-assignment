-- 3-month trials ending in the next 30 days, with how engaged the teen is (app days in the last 14 days).
SET search_path TO alcovia;
WITH params AS (SELECT DATE '2026-10-16' AS today)
SELECT s.name, e.end_on, e.end_on - params.today AS days_left,
       count(DISTINCT u.day) AS active_days_last_14,
       CASE WHEN count(DISTINCT u.day) >= 7 THEN 'high'
            WHEN count(DISTINCT u.day) >= 3 THEN 'medium' ELSE 'low' END AS engagement
FROM enrolments e
JOIN students s USING (student_id)
CROSS JOIN params
LEFT JOIN app_usage_daily u ON u.student_id = e.student_id AND u.day > params.today - 14
WHERE e.plan = 'trial' AND NOT e.renewed
  AND e.end_on BETWEEN params.today AND params.today + 30
GROUP BY s.name, e.end_on, params.today
ORDER BY e.end_on;
