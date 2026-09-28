-- Workflow fact at one row per workflow event.
{{ config(alias='fact_workflow_event', tags=['workflow']) }}

SELECT
    MD5(CONCAT_WS('|', supplier_id, invoice_number, workflow_event_id)) AS workflow_event_key,
    MD5(CONCAT_WS('|', supplier_id, invoice_number)) AS invoice_key,
    supplier_id,
    invoice_number,
    workflow_event_id,
    workflow_id,
    event_sequence,
    workflow_stage,
    previous_status,
    current_status,
    previous_event_timestamp,
    event_timestamp,
    processor_id,
    exception_reason,
    invoice_amount_usd,
    _source_file,
    _loaded_at,
    _run_id
FROM {{ ref('stg_workflow') }}
