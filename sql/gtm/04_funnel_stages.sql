-- Meta + organic funnel for leads created in the period:
-- lead -> qualified -> discovery call set -> showed up -> ambition interview -> architect session -> paid.
-- step_pct = share of the previous stage that carried on.
SET search_path TO alcovia;
WITH params AS (SELECT DATE '2026-08-01' AS from_date, DATE '2026-10-16' AS to_date),
l AS (SELECT * FROM leads, params WHERE (created_at AT TIME ZONE 'Asia/Kolkata')::date BETWEEN from_date AND to_date),
stages AS (
  SELECT 1 AS n, 'Total leads'        AS stage, count(*)                   AS leads FROM l UNION ALL
  SELECT 2, 'Qualified',               count(qualified_at)                         FROM l UNION ALL
  SELECT 3, 'Discovery call set',      count(discovery_set_at)                     FROM l UNION ALL
  SELECT 4, 'Showed up to call',       count(discovery_showed_at)                  FROM l UNION ALL
  SELECT 5, 'Ambition interview',      count(ambition_done_at)                     FROM l UNION ALL
  SELECT 6, 'Architect session',       count(architect_done_at)                    FROM l UNION ALL
  SELECT 7, 'Paid sign-up',            count(paid_at)                              FROM l
)
SELECT n, stage, leads,
       round(100.0 * leads / lag(leads) OVER (ORDER BY n), 1)         AS step_pct,
       round(100.0 * leads / first_value(leads) OVER (ORDER BY n), 1) AS of_all_leads_pct
FROM stages ORDER BY n;
-- show-up rate = step_pct of 'Showed up to call'; ambition drop-off = 100 - step_pct of 'Architect session'
