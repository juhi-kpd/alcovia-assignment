-- Invoices raised in the period and not yet paid, with days overdue.
SET search_path TO alcovia;
WITH params AS (SELECT DATE '2026-08-01' AS from_date, DATE '2026-10-16' AS to_date, DATE '2026-10-16' AS today)
SELECT i.invoice_id, i.billed_to, i.product, i.amount_inr, i.issued_on, i.due_on,
       greatest(params.today - i.due_on, 0) AS days_overdue,
       CASE WHEN params.today - i.due_on > 30 THEN 'critical'
            WHEN params.today > i.due_on      THEN 'overdue'
            ELSE 'not due' END              AS status
FROM invoices i, params
WHERE i.paid_on IS NULL
  AND i.issued_on BETWEEN params.from_date AND params.to_date
ORDER BY days_overdue DESC;
