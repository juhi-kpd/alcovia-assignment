-- Syllabus pace and chapter readiness per student and subject, as of a date.
-- Pace target: 25% of the syllabus a quarter from 1 April.
-- Readiness: each chapter earns 20 points per rigour stage reached (read, notes, practice >70%,
-- timed past paper, exam-ready >80%); subject readiness = points / chapters, 0–100.
SET search_path TO alcovia;
WITH params AS (SELECT DATE '2026-10-16' AS as_of, DATE '2026-04-01' AS year_start),
expected AS (SELECT round(least(100, 100 * (as_of - year_start)::numeric / 365)) AS pct FROM params),
per_subject AS (
  SELECT sb.student_id, sb.name AS subject, sb.chapters_total,
         count(DISTINCT cs.chapter_id) FILTER (WHERE cs.stage = 1) AS chapters_started,
         count(cs.*)                                               AS stage_points
  FROM subjects sb
  JOIN chapters c USING (subject_id)
  LEFT JOIN chapter_stages cs ON cs.chapter_id = c.chapter_id AND cs.reached_on <= (SELECT as_of FROM params)
  GROUP BY 1, 2, 3
)
SELECT s.name, p.subject,
       round(100.0 * p.chapters_started / p.chapters_total) AS syllabus_done_pct,
       expected.pct                                         AS expected_pct,
       round(100.0 * p.chapters_started / p.chapters_total) - expected.pct AS gap_pts,
       round(20.0 * p.stage_points / p.chapters_total)      AS readiness_score
FROM per_subject p JOIN students s USING (student_id) CROSS JOIN expected
ORDER BY gap_pts, s.name;
