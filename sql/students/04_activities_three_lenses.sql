-- Every program activity on three lenses:
--   did Alcovia do it (held vs planned), did Alcovians like it (attendance, rating),
--   how did they perform (facilitator soft-skill score where captured).
SET search_path TO alcovia;
WITH params AS (SELECT DATE '2026-08-01' AS from_date, DATE '2026-10-16' AS to_date)
SELECT a.kind,
       count(DISTINCT a.activity_id)                                             AS planned,
       count(DISTINCT a.activity_id) FILTER (WHERE a.held)                       AS held,
       round(100.0 * count(DISTINCT a.activity_id) FILTER (WHERE a.held) / count(DISTINCT a.activity_id)) AS held_pct,
       round(100.0 * count(*) FILTER (WHERE p.attended) / nullif(count(*) FILTER (WHERE a.held), 0))   AS attendance_pct,
       round(avg(p.rating), 2)                                                   AS avg_rating,
       round(100.0 * count(p.rating) / nullif(count(*) FILTER (WHERE p.attended), 0)) AS rated_pct,
       round(avg(p.skill_score), 2)                                              AS avg_skill_score
FROM activities a
JOIN activity_participants p USING (activity_id), params
WHERE a.scheduled_on BETWEEN from_date AND to_date
GROUP BY a.kind
ORDER BY CASE a.kind WHEN 'academic_session' THEN 1 WHEN 'workshop' THEN 2 WHEN 'pod' THEN 3 WHEN 'peer' THEN 4
                     WHEN 'mentor_call' THEN 5 WHEN 'branding' THEN 6 ELSE 7 END, a.kind;
