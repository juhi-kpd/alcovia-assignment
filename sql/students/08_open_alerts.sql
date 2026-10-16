-- Open alerts for the weekly advisor review (also what n8n sends to advisors each night).
SET search_path TO alcovia;
SELECT s.name, ad.name AS advisor, a.kind, a.detail, a.raised_at::date AS raised_on
FROM alerts a JOIN students s USING (student_id) JOIN advisors ad USING (advisor_id)
WHERE a.actioned_at IS NULL
ORDER BY a.raised_at, s.name;
