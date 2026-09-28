-- Mart table: expose only the business columns needed by reporting tools.
{{ config(alias='customer', tags=['customer']) }}

SELECT 
    customer_id,
    customer_name,
    city,
    modified_date
FROM {{ ref('stg_customer') }}
