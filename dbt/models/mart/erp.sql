-- Power BI invoice output: one row per supplier and invoice number.
{{ config(alias='erp', tags=['erp', 'powerbi']) }}

WITH invoice_totals AS (
    SELECT
        invoice_key,
        SUM(line_amount_doc) AS line_amount_doc,
        SUM(line_amount_usd) AS line_amount_usd,
        MAX(invoice_amount_doc) AS invoice_amount_doc,
        MAX(amount_paid) AS amount_paid,
        COUNT(invoice_row_key) AS source_row_count
    FROM {{ ref('fact_invoice') }}
    GROUP BY invoice_key
),

invoice_output AS (
    SELECT
        dim.invoice_key,
        dim.supplier_id,
        dim.invoice_id,
        dim.invoice_number,
        dim.invoice_date,
        dim.creation_date,
        dim.receipt_date,
        dim.posting_date,
        dim.payment_date,
        dim.due_date_raw,
        dim.payment_status,
        dim.currency,
        totals.line_amount_doc,
        totals.line_amount_usd,
        totals.invoice_amount_doc,
        totals.amount_paid,
        totals.source_row_count,
        dim._loaded_at,
        dim._run_id
    FROM {{ ref('dim_invoice') }} AS dim
    LEFT JOIN invoice_totals AS totals
        ON dim.invoice_key = totals.invoice_key
)

SELECT
    invoice_output.*,
    invoice_amount_doc - line_amount_doc AS line_amount_variance_doc,
    invoice_amount_doc - COALESCE(amount_paid, 0) AS outstanding_amount_doc,
    CASE
        WHEN invoice_amount_doc IS NULL OR invoice_amount_doc = 0 THEN NULL
        ELSE ROUND(COALESCE(amount_paid, 0) / invoice_amount_doc * 100, 2)
    END AS paid_percent,
    CASE
        WHEN invoice_date IS NULL OR payment_date IS NULL THEN NULL
        ELSE DATE_DIFF('day', invoice_date, payment_date)
    END AS days_to_pay,
    CASE
        WHEN invoice_date IS NULL OR posting_date IS NULL THEN NULL
        ELSE DATE_DIFF('day', invoice_date, posting_date)
    END AS days_to_post,
    CASE
        WHEN due_date_raw IS NULL THEN NULL
        WHEN payment_date IS NOT NULL THEN GREATEST(DATE_DIFF('day', due_date_raw, payment_date), 0)
        WHEN current_date > due_date_raw THEN DATE_DIFF('day', due_date_raw, current_date)
        ELSE 0
    END AS overdue_days,
    CASE
        WHEN due_date_raw IS NULL THEN 'UNKNOWN'
        WHEN payment_date IS NULL and current_date > due_date_raw THEN 'OVERDUE'
        WHEN payment_date IS NULL THEN 'OPEN'
        WHEN payment_date <= due_date_raw THEN 'ON_TIME'
        ELSE 'LATE'
    END AS payment_timing,
    CASE
        WHEN payment_date IS NOT NULL THEN true
        ELSE false
    END AS is_paid
FROM invoice_output
