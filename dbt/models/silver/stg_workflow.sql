-- ERP staging: clean invoice fields, safely cast dates and amounts, and retain lineage.
{{
  config(
    materialized = 'table',
    alias='workflow',
    tags=['workflow']
    )
}}


SELECT
    NULLIF(TRIM(CAST("WORKFLOW_EVENT_ID" AS VARCHAR)),'') AS workflow_event_id,
    NULLIF(TRIM(CAST("WORKFLOW_ID" AS VARCHAR)),'') AS workflow_id,
    NULLIF(TRIM(CAST("EVENT_SEQUENCE" AS VARCHAR)),'') AS event_sequence,
    NULLIF(TRIM(CAST("ERP_RECORD_ID" AS VARCHAR)), '') AS erp_record_id,
    NULLIF(TRIM(CAST("DOCUMENT_ID" AS VARCHAR)),'') AS document_id,
    NULLIF(TRIM(CAST("INVOICE_ID" AS VARCHAR)),'') AS invoice_id,
    NULLIF(TRIM(CAST("INVOICE_NUMBER" AS VARCHAR)),'') AS invoice_number,
    NULLIF(TRIM(CAST("INVOICE_NUMBER" AS VARCHAR)),'') AS invoice_number,
    NULLIF(TRIM(CAST("SUPPLIER_ID" AS VARCHAR)),'') AS supplier_id,
    NULLIF(TRIM(CAST("PO_NUMBER" AS VARCHAR)),'') AS po_number,
    NULLIF(TRIM(CAST("COMPANY_CODE" AS VARCHAR)),'') AS company_code,
    TRY_CAST(NULLIF(TRIM(CAST("INVOICE_AMOUNT_USD" AS VARCHAR)),'') AS decimal(18, 2)) AS invoice_amount_usd,
    NULLIF(TRIM(CAST("WORKFLOW_STAGE" AS VARCHAR)),'') AS workflow_stage,
    NULLIF(TRIM(CAST("PREVIOUS_STATUS" AS VARCHAR)),'') AS previous_status,
    NULLIF(TRIM(CAST("CURRENT_STATUS" AS VARCHAR)),'') AS current_status,
    TRY_CAST(NULLIF(TRIM(CAST("PREVIOUS_EVENT_TIMESTAMP" AS VARCHAR)),'') AS TIMESTAMP) AS previous_event_TIMESTAMP,
    TRY_CAST(NULLIF(TRIM(CAST("EVENT_TIMESTAMP" AS VARCHAR)),'') AS TIMESTAMP) AS event_TIMESTAMP,
    TRY_CAST(NULLIF(TRIM(CAST("STAGE_DURATION_HOURS" AS VARCHAR)),'') AS TIMESTAMP) AS stage_duration_hours,
    NULLIF(TRIM(CAST("PROCESSOR_ID" AS VARCHAR)),'') AS processor_id,
    NULLIF(TRIM(CAST("EXCEPTION_REASON" AS VARCHAR)),'') AS exception_reason,
    _source_file,
    _loaded_at,
    _run_id
FROM {{ source('bronze', 'workflow') }}
WHERE NULLIF(TRIM(CAST("SUPPLIER_ID" AS VARCHAR)),'') IS NOT NULL
  AND NULLIF(TRIM(CAST("INVOICE_NUMBER" AS VARCHAR)),'') IS NOT NULL-- ERP staging: clean invoice identifiers, dates, amounts, and source lineage.
