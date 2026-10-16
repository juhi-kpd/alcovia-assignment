-- Revenue vs target by month: full program, 3-month trial, workshops (₹3,999 a seat),
-- students onboarded, and program vs workshop split. Change the dates in params.
SET search_path TO alcovia;
WITH params AS (SELECT DATE '2026-08-01' AS from_date, DATE '2026-10-16' AS to_date),
pay AS (
  SELECT date_trunc('month', p.paid_at AT TIME ZONE 'Asia/Kolkata')::date AS month, p.product, p.amount_inr
  FROM payments p, params
  WHERE (p.paid_at AT TIME ZONE 'Asia/Kolkata')::date BETWEEN params.from_date AND params.to_date
)
SELECT t.month,
       coalesce(sum(amount_inr) FILTER (WHERE product = 'full'), 0)     AS full_program_inr,
       coalesce(sum(amount_inr) FILTER (WHERE product = 'trial'), 0)    AS trial_inr,
       coalesce(sum(amount_inr) FILTER (WHERE product = 'workshop'), 0) AS workshop_inr,
       coalesce(sum(amount_inr), 0)                                     AS total_inr,
       t.target_inr,
       round(100 * coalesce(sum(amount_inr), 0) / t.target_inr, 1)     AS pct_of_target,
       count(*) FILTER (WHERE product = 'trial')                        AS trial_signups,
       count(*) FILTER (WHERE product = 'full')                         AS full_signups,
       count(*) FILTER (WHERE product = 'workshop')                     AS workshop_seats,
       round(100 * coalesce(sum(amount_inr) FILTER (WHERE product <> 'workshop'), 0)
             / nullif(sum(amount_inr), 0), 1)                           AS program_share_pct
FROM revenue_targets t
CROSS JOIN params
LEFT JOIN pay ON pay.month = t.month
WHERE t.month BETWEEN date_trunc('month', params.from_date) AND params.to_date
GROUP BY t.month, t.target_inr
ORDER BY t.month;
