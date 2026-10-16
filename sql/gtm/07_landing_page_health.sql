-- Landing page health: visits, drop-off (1 - form submits / visits) and latest mobile load time.
SET search_path TO alcovia;
WITH params AS (SELECT DATE '2026-08-01' AS from_date, DATE '2026-10-16' AS to_date)
SELECT page, sum(visits) AS visits,
       round(100 - 100.0 * sum(conversions) / sum(visits), 1) AS drop_off_pct,
       (array_agg(mobile_load_s ORDER BY day DESC))[1]          AS latest_mobile_load_s,
       CASE WHEN (array_agg(mobile_load_s ORDER BY day DESC))[1] > 3 THEN 'slow'
            WHEN 100 - 100.0 * sum(conversions) / sum(visits) > 65   THEN 'high drop-off'
            ELSE 'healthy' END AS health
FROM landing_page_daily, params
WHERE day BETWEEN from_date AND to_date
GROUP BY page ORDER BY visits DESC;
