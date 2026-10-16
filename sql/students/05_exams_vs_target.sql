-- Exam results against the targets agreed with student and parent.
SET search_path TO alcovia;
SELECT s.name, e.exam_type, round(avg(e.target_pct)) AS avg_target_pct, round(avg(e.actual_pct)) AS avg_actual_pct,
       count(*) FILTER (WHERE e.actual_pct >= e.target_pct) AS subjects_on_target, count(*) AS subjects
FROM exam_results e JOIN students s USING (student_id)
GROUP BY s.name, e.exam_type, e.exam_date
ORDER BY e.exam_date DESC, avg(e.actual_pct) - avg(e.target_pct);
