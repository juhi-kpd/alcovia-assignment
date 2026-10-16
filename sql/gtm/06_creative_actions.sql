-- Creative performance and the scale / refresh / drop call (root-cause view).
-- Results: qualified leads for program ads, workshop seats for workshop ads.
-- Rules (targets are assumptions, tuned after a month of real data):
--   drop    = cost per result > 1.6 x target AND CTR < 1%
--   refresh = frequency >= 3 (latest month) OR CTR < 1%
--   scale   = cost per result <= target AND frequency < 2.5
SET search_path TO alcovia;
WITH params AS (SELECT DATE '2026-08-01' AS from_date, DATE '2026-10-16' AS to_date,
                       2500::numeric AS target_cpql, 800::numeric AS target_cost_per_seat),
ads AS (
  SELECT c.creative_id, c.name, k.objective,
         sum(a.spend_inr) AS spend, sum(a.impressions) AS impressions, sum(a.link_clicks) AS clicks
  FROM ad_daily a JOIN creatives c USING (creative_id) JOIN campaigns k USING (campaign_id), params
  WHERE a.day BETWEEN from_date AND to_date
  GROUP BY 1, 2, 3
),
freq AS (   -- frequency in the latest month of the range
  SELECT creative_id, sum(impressions)::numeric / nullif(sum(reach), 0) AS frequency
  FROM ad_daily, params
  WHERE date_trunc('month', day) = date_trunc('month', to_date)
  GROUP BY 1
),
results AS (
  SELECT creative_id, count(*) AS results FROM leads, params
  WHERE qualified_at IS NOT NULL AND (created_at AT TIME ZONE 'Asia/Kolkata')::date BETWEEN from_date AND to_date
  GROUP BY 1
  UNION ALL
  SELECT utm_creative_id, count(*) FROM payments, params
  WHERE product = 'workshop' AND (paid_at AT TIME ZONE 'Asia/Kolkata')::date BETWEEN from_date AND to_date
  GROUP BY 1
),
m AS (
  SELECT ads.*, round(100.0 * clicks / impressions, 2) AS ctr_pct, round(f.frequency, 1) AS frequency,
         coalesce(r.results, 0) AS results,
         round(spend / nullif(r.results, 0)) AS cost_per_result,
         CASE WHEN objective = 'program' THEN p.target_cpql ELSE p.target_cost_per_seat END AS target
  FROM ads JOIN freq f USING (creative_id) LEFT JOIN results r USING (creative_id), params p
)
SELECT name, objective, round(spend) AS spend_inr, ctr_pct, frequency, results, cost_per_result, target,
       CASE WHEN cost_per_result > 1.6 * target AND ctr_pct < 1 THEN 'drop'
            WHEN frequency >= 3 OR ctr_pct < 1                 THEN 'refresh'
            WHEN cost_per_result <= target AND frequency < 2.5  THEN 'scale'
            ELSE 'hold' END AS action
FROM m
ORDER BY ctr_pct DESC;
