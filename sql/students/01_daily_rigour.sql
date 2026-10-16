-- Day-level rigour per student: app minutes, focus time, 8pm quiz, timetable adherence, wearable sleep and activity.
SET search_path TO alcovia;
WITH params AS (SELECT DATE '2026-09-17' AS from_date, DATE '2026-10-16' AS to_date),
days AS (SELECT (to_date - from_date + 1)::numeric AS n FROM params),
app AS (SELECT student_id, sum(active_minutes) AS mins, count(*) AS active_days
        FROM app_usage_daily, params WHERE day BETWEEN from_date AND to_date GROUP BY 1),
focus AS (SELECT student_id, sum(actual_min) AS mins, count(*) AS sessions, count(*) FILTER (WHERE completed) AS completed
          FROM focus_sessions, params WHERE (started_at AT TIME ZONE 'Asia/Kolkata')::date BETWEEN from_date AND to_date GROUP BY 1),
quiz AS (SELECT a.student_id, count(*) AS attempts, avg(a.correct * 10.0) AS avg_score_pct
         FROM quiz_attempts a, params WHERE a.quiz_date BETWEEN from_date AND to_date GROUP BY 1),
quizzes_held AS (SELECT count(*) AS n FROM quizzes, params WHERE quiz_date BETWEEN from_date AND to_date),
tt AS (SELECT student_id, count(*) FILTER (WHERE done) AS done, count(*) AS planned
       FROM timetable_slots, params WHERE slot_type = 'self_study' AND day BETWEEN from_date AND to_date GROUP BY 1),
wear AS (SELECT student_id, avg(sleep_hours) AS sleep, avg(active_min) AS active, avg(recovery_pct) AS recovery
         FROM wearable_daily, params WHERE day BETWEEN from_date AND to_date GROUP BY 1)
SELECT s.name,
       round(coalesce(app.mins, 0) / days.n, 2)                          AS app_min_per_day,
       coalesce(app.active_days, 0)                                      AS active_days,
       round(coalesce(focus.mins, 0) / days.n, 1)                        AS focus_min_per_day,
       round(100.0 * focus.completed / nullif(focus.sessions, 0))        AS focus_completed_pct,
       round(100.0 * coalesce(quiz.attempts, 0) / quizzes_held.n)        AS quiz_attempt_pct,
       round(quiz.avg_score_pct)                                         AS quiz_avg_pct,
       round(100.0 * tt.done / nullif(tt.planned, 0))                    AS self_study_done_pct,
       round(wear.sleep, 1) AS sleep_h, round(wear.active) AS active_min, round(wear.recovery) AS recovery_pct
FROM students s CROSS JOIN days CROSS JOIN quizzes_held
LEFT JOIN app USING (student_id) LEFT JOIN focus USING (student_id) LEFT JOIN quiz USING (student_id)
LEFT JOIN tt USING (student_id) LEFT JOIN wear USING (student_id)
ORDER BY app_min_per_day DESC;
