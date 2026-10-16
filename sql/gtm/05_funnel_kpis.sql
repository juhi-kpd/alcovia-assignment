-- Top funnel metrics: blended cost per qualified lead (program ad spend / all qualified leads), program conversion, organic leads,
-- and average days in the funnel for those who paid and for those who dropped (by stage).
SET search_path TO alcovia;
WITH params AS (SELECT DATE '2026-08-01' AS from_date, DATE '2026-10-16' AS to_date),
l AS (SELECT * FROM leads, params WHERE (created_at AT TIME ZONE 'Asia/Kolkata')::date BETWEEN from_date AND to_date),
spend AS (
  SELECT sum(a.spend_inr) AS program_spend
  FROM ad_daily a JOIN creatives c USING (creative_id) JOIN campaigns k USING (campaign_id), params
  WHERE k.objective = 'program' AND a.day BETWEEN from_date AND to_date
)
SELECT round(spend.program_spend / nullif(count(qualified_at), 0)) AS cost_per_qualified_lead_inr,
       round(100.0 * count(paid_at) / count(*), 2)                         AS program_conversion_pct,
       count(*) FILTER (WHERE source = 'organic')                          AS organic_leads,
       round(avg(extract(epoch FROM paid_at - created_at) / 86400) FILTER (WHERE paid_at IS NOT NULL), 1)    AS avg_days_to_pay,
       round(avg(extract(epoch FROM dropped_at - created_at) / 86400) FILTER (WHERE dropped_at IS NOT NULL), 1) AS avg_days_to_drop
FROM l, spend
GROUP BY spend.program_spend;

-- Where the drop-offs happen
WITH params AS (SELECT DATE '2026-08-01' AS from_date, DATE '2026-10-16' AS to_date)
SELECT drop_stage AS last_stage_reached, count(*) AS dropped,
       round(avg(extract(epoch FROM dropped_at - created_at) / 86400), 1) AS avg_days_in_funnel
FROM alcovia.leads, params
WHERE dropped_at IS NOT NULL AND (created_at AT TIME ZONE 'Asia/Kolkata')::date BETWEEN from_date AND to_date
GROUP BY drop_stage ORDER BY dropped DESC;
