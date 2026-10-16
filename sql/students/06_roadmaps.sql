-- Roadmap progress: career (done / not done), personal milestones hit, academic targets set.
SET search_path TO alcovia;
WITH params AS (SELECT DATE '2026-10-16' AS as_of)
SELECT s.name,
       bool_or(r.done_on IS NOT NULL) FILTER (WHERE r.roadmap = 'career')                       AS career_roadmap_done,
       count(*) FILTER (WHERE r.roadmap = 'personal' AND r.done_on IS NOT NULL)                AS personal_hit,
       count(*) FILTER (WHERE r.roadmap = 'personal' AND r.due_on <= params.as_of)             AS personal_due,
       bool_or(r.done_on IS NOT NULL) FILTER (WHERE r.roadmap = 'academic')                    AS academic_targets_set
FROM roadmap_items r JOIN students s USING (student_id), params
GROUP BY s.name ORDER BY personal_hit;
