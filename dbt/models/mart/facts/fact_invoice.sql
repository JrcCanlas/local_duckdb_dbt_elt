-- Invoice fact at source-row grain; amounts remain available for detailed analysis.
{{ config(alias='fact_invoice', tags=['erp']) }}

SELECT
    MD5(CONCAT_WS('|', supplier_id, invoice_number, COALESCE(invoice_id, ''))) AS invoice_row_key,
    MD5(CONCAT_WS('|', supplier_id, invoice_number)) AS invoice_key,
    supplier_id,
    invoice_id,
    invoice_number,
    line_amount_doc,
    line_amount_usd,
    invoice_amount_doc,
    amount_paid,
    _source_file,
    _loaded_at,
    _run_id
FROM {{ ref('stg_erp') }}
