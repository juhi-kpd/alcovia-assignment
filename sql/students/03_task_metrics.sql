-- Advisor-set task metrics per student: completion rate, deadline adherence, time-estimate accuracy.
SET search_path TO alcovia;
WITH params AS (SELECT DATE '2026-09-17' AS from_date, DATE '2026-10-16' AS to_date)
SELECT s.name,
       count(*)                                                                  AS tasks_due,
       round(100.0 * count(done_on) / count(*))                                  AS completion_pct,
       round(100.0 * count(*) FILTER (WHERE done_on <= due_on) / nullif(count(done_on), 0)) AS on_time_pct,
       round(avg(actual_min::numeric / est_min) FILTER (WHERE actual_min IS NOT NULL), 2)  AS actual_vs_estimate
FROM tasks t JOIN students s USING (student_id), params
WHERE t.due_on BETWEEN from_date AND to_date
GROUP BY s.name
ORDER BY completion_pct;
