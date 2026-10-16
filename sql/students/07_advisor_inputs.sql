-- Advisor input KPIs: targets agreed with parents, students logging inputs often enough for automations
-- to be accurate (3+ active days a week over the last 4 weeks), and alerts actioned within 48 hours.
SET search_path TO alcovia;
WITH params AS (SELECT DATE '2026-10-16' AS as_of),
agreed AS (SELECT student_id, bool_and(target_agreed_on IS NOT NULL) AS ok FROM exam_results GROUP BY 1),
cadence AS (SELECT u.student_id, count(*) / 4.0 AS days_per_week
            FROM app_usage_daily u, params WHERE u.day > as_of - 28 GROUP BY 1),
al AS (SELECT student_id, count(*) AS alerts,
              count(*) FILTER (WHERE actioned_at <= raised_at + interval '48 hours') AS actioned_48h
       FROM alerts GROUP BY 1)
SELECT ad.name AS advisor,
       count(*)                                                                   AS students,
       round(100.0 * count(*) FILTER (WHERE agreed.ok) / count(*))                AS targets_agreed_pct,
       round(100.0 * count(*) FILTER (WHERE coalesce(cadence.days_per_week, 0) >= 3) / count(*)) AS logging_3plus_days_pct,
       coalesce(sum(al.alerts), 0)                                                AS alerts,
       round(100.0 * sum(al.actioned_48h) / nullif(sum(al.alerts), 0))            AS alerts_actioned_48h_pct
FROM students s JOIN advisors ad USING (advisor_id)
LEFT JOIN agreed USING (student_id) LEFT JOIN cadence USING (student_id) LEFT JOIN al USING (student_id)
GROUP BY ad.name ORDER BY ad.name;
