-- Power BI workflow output: one row per invoice with workflow events.
{{ config(alias='workflow', tags=['workflow', 'powerbi']) }}

WITH ranked_events AS (
    SELECT
        event.*,
        row_number() OVER (
            PARTITION BY event.invoice_key
            ORDER BY event.event_timestamp DESC, event.event_sequence DESC
        ) AS event_rank
    FROM {{ ref('fact_workflow_event') }} AS event
),

workflow_totals AS (
    SELECT
        invoice_key,
        MAX(invoice_amount_usd) AS invoice_amount_usd,
        MIN(event_timestamp) AS first_workflow_event_timestamp,
        MAX(event_timestamp) AS last_workflow_event_timestamp,
        COUNT(workflow_event_key) AS workflow_event_count,
        COUNT(DISTINCT workflow_stage) AS workflow_stage_count,
        SUM(CASE WHEN exception_reasON IS NOT NULL THEN 1 ELSE 0 END)
            AS exception_event_count
    FROM ranked_events
    GROUP BY invoice_key
)

SELECT
    invoice.invoice_key,
    invoice.supplier_id,
    invoice.invoice_id,
    invoice.invoice_number,
    invoice.invoice_date,
    invoice.creation_date,
    invoice.receipt_date,
    invoice.posting_date,
    invoice.payment_date,
    invoice.due_date_raw,
    latest.workflow_id AS current_workflow_id,
    latest.workflow_stage AS current_workflow_stage,
    latest.current_status AS current_workflow_status,
    totals.invoice_amount_usd,
    totals.first_workflow_event_timestamp,
    totals.last_workflow_event_timestamp,
    totals.workflow_event_count,
    totals.workflow_stage_count,
    totals.exception_event_count,
    ROUND(
        totals.exception_event_count / NULLIF(totals.workflow_event_count, 0) * 100,
        2
    ) AS exception_rate_percent,
    ROUND(
        epoch(totals.last_workflow_event_timestamp - totals.first_workflow_event_timestamp)
            / 3600,
        2
    ) AS workflow_duration_hours,
    CASE
        WHEN totals.workflow_event_count <= 1 THEN 0
        ELSE ROUND(
            epoch(totals.last_workflow_event_timestamp - totals.first_workflow_event_timestamp)
                / 3600 / (totals.workflow_event_count - 1),
            2
        )
    END AS average_event_gap_hours,
    CASE
        WHEN totals.exception_event_count > 0 THEN true
        ELSE false
    END AS has_exception,
    CASE
        WHEN UPPER(COALESCE(latest.current_status, '')) IN ('APPROVED', 'COMPLETED', 'CLOSED', 'PAID')
            THEN true
        ELSE false
    END AS is_workflow_complete,
    invoice._loaded_at,
    invoice._run_id
FROM workflow_totals AS totals
JOIN {{ ref('dim_invoice') }} AS invoice
    ON invoice.invoice_key = totals.invoice_key
LEFT JOIN ranked_events AS latest
    ON totals.invoice_key = latest.invoice_key
   AND latest.event_rank = 1
