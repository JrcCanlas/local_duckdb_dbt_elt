-- ERP staging: clean invoice fields, safely cast dates and amounts, and retain lineage.
{{
  config(
    materialized = 'table',
    alias = 'erp',
    tags = ['erp'])
}}

SELECT
    NULLIF(TRIM(CAST("ERP_RECORD_ID" AS VARCHAR)), '') AS erp_record_id,
    NULLIF(TRIM(CAST("DOCUMENT_ID" AS VARCHAR)), '') AS document_id,
    NULLIF(TRIM(CAST("INVOICE_ID" AS VARCHAR)), '') AS invoice_id,
    NULLIF(TRIM(CAST("INVOICE_NUMBER" AS VARCHAR)), '') AS invoice_number,
    NULLIF(TRIM(CAST("LINE_NUMBER" AS VARCHAR)), '') AS line_number,
    NULLIF(TRIM(CAST("DISTRIBUTION_NUMBER" AS VARCHAR)), '') AS distribution_number,
    NULLIF(TRIM(CAST("INVOICE_HEADER_FLAG" AS VARCHAR)), '') AS invoice_header_flag,
    NULLIF(TRIM(CAST("SUPPLIER_ID" AS VARCHAR)), '') AS supplier_id,
    NULLIF(TRIM(CAST("SUPPLIER_NAME" AS VARCHAR)), '') AS supplier_name,
    NULLIF(TRIM(CAST("CRITICAL_SUPPLIER_FLAG" AS VARCHAR)), '') AS critical_supplier_flag,
    NULLIF(TRIM(CAST("REGION" AS VARCHAR)), '') AS region,
    NULLIF(TRIM(CAST("COUNTRY_CODE" AS VARCHAR)), '') AS country_code,
    NULLIF(TRIM(CAST("COMPANY_CODE" AS VARCHAR)), '') AS company_code,
    NULLIF(TRIM(CAST("BUSINESS_UNIT" AS VARCHAR)), '') AS business_unit,
    NULLIF(TRIM(CAST("COST_CENTER" AS VARCHAR)), '') AS cost_center,
    NULLIF(TRIM(CAST("GL_ACCOUNT" AS VARCHAR)), '') AS gl_account,
    NULLIF(TRIM(CAST("CATEGORY" AS VARCHAR)), '') AS category,
    NULLIF(TRIM(CAST("QUANTITY" AS VARCHAR)), '') AS quantity,
    NULLIF(TRIM(CAST("COMPANY_CODE" AS VARCHAR)), '') AS company_code,
    TRY_CAST(NULLIF(TRIM(CAST("UNIT_PRICE" AS VARCHAR)), '') AS decimal(18, 2)) AS unit_price,
    TRY_CAST(NULLIF(TRIM(CAST("LINE_AMOUNT_DOC" AS VARCHAR)), '') AS decimal(18, 2)) AS line_amount_doc,
    TRY_CAST(NULLIF(TRIM(CAST("LINE_AMOUNT_USD" AS VARCHAR)), '') AS decimal(18, 2)) AS line_amount_usd,
    TRY_CAST(NULLIF(TRIM(CAST("INVOICE_AMOUNT_DOC" AS VARCHAR)), '') AS decimal(18, 2)) AS invoice_amount_doc,
    TRY_CAST(NULLIF(TRIM(CAST("INVOICE_AMOUNT_USD" AS VARCHAR)), '') AS decimal(18, 2)) AS invoice_amount_usd,
    NULLIF(TRIM(CAST("CURRENCY" AS VARCHAR)), '') AS currency,
    TRY_CAST(NULLIF(TRIM(CAST("FX_RATE" AS VARCHAR)), '') AS decimal(18, 3)) AS fx_rate,
    TRY_CAST(NULLIF(TRIM(CAST("PAYMENT_TERM_DAYS" AS VARCHAR)), '') AS INTEGER) AS payment_term_days,
    NULLIF(TRIM(CAST("PO_NUMBER" AS VARCHAR)), '') AS po_number,
    NULLIF(TRIM(CAST("PO_NON_PO" AS VARCHAR)), '') AS po_non_po,
    NULLIF(TRIM(CAST("MATCH_TYPE" AS VARCHAR)), '') AS match_type,
    NULLIF(TRIM(CAST("INVOICE_TYPE" AS VARCHAR)), '') AS invoice_type,
    TRY_CAST(NULLIF(TRIM(CAST("INVOICE_DATE" AS VARCHAR)), '') AS DATE) AS invoice_date,
    TRY_CAST(NULLIF(TRIM(CAST("RECEIPT_DATE" AS VARCHAR)), '') AS DATE) AS receipt_date,
    TRY_CAST(NULLIF(TRIM(CAST("CREATION_DATE" AS VARCHAR)), '') AS DATE) AS creation_date,
    TRY_CAST(NULLIF(TRIM(CAST("POSTING_DATE" AS VARCHAR)), '') AS DATE) AS posting_date,
    TRY_CAST(NULLIF(TRIM(CAST("DUE_DATE_RAW" AS VARCHAR)), '') AS DATE) AS due_date_raw,
    TRY_CAST(NULLIF(TRIM(CAST("PAYMENT_DATE" AS VARCHAR)), '') AS DATE) AS payment_date,
    NULLIF(TRIM(CAST("PAYMENT_STATUS" AS VARCHAR)), '') AS payment_status,
    TRY_CAST(NULLIF(TRIM(CAST("AMOUNT_PAID" AS VARCHAR)), '') AS decimal(18, 2)) AS amount_paid,
    TRY_CAST(NULLIF(TRIM(CAST("AMOUNT_REMAINING" AS VARCHAR)), '') AS decimal(18, 2)) AS amount_remaining,
    NULLIF(TRIM(CAST("SOURCE_SYSTEM" AS VARCHAR)), '') AS source_system,
    TRY_CAST(NULLIF(TRIM(CAST("LAST_UPDATED_TIMESTAMP" AS VARCHAR)), '') AS TIMESTAMP) AS last_updated_timestamp,
    NULLIF(TRIM(CAST("LATE_ARRIVAL_FLAG" AS VARCHAR)), '') AS late_arrival_flag,
    NULLIF(TRIM(CAST("DQ_SCENARIO" AS VARCHAR)), '') AS dq_scenario,
    _source_file,
    _loaded_at,
    _run_id
FROM {{ source('bronze', 'erp') }}
WHERE NULLIF(TRIM(CAST("SUPPLIER_ID" AS VARCHAR)), '') IS NOT NULL
  AND NULLIF(TRIM(CAST("INVOICE_NUMBER" AS VARCHAR)), '') IS NOT NULL-- ERP staging: clean invoice identifiers, dates, amounts, and source lineage.
