-- Shared invoice dimension at one row per supplier and invoice number.
{{ config(alias='dim_invoice', tags=['erp', 'workflow']) }}

SELECT
    MD5(CONCAT_WS('|', supplier_id, invoice_number)) AS invoice_key,
    supplier_id,
    MAX(invoice_id) AS invoice_id,
    invoice_number,
    min(invoice_date) AS invoice_date,
    min(creation_date) AS creation_date,
    min(receipt_date) AS receipt_date,
    min(posting_date) AS posting_date,
    MAX(payment_date) AS payment_date,
    MAX(due_date_raw) AS due_date_raw,
    MAX(payment_status) AS payment_status,
    MAX(currency) AS currency,
    MAX(_loaded_at) AS _loaded_at,
    MAX(_run_id) AS _run_id
FROM {{ ref('stg_erp') }}
GROUP BY supplier_id, invoice_number
