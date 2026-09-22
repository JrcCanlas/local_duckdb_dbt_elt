-- Silver staging: cast types, trim text, reject invalid IDs, and keep the latest row.
{{ 
  config(
    materialized = 'table',
    alias = 'customer',
    tags = ['customer']
    )
}}

SELECT 
    TRY_CAST(customer_id AS BIGINT) AS customer_id,
    TRIM(customer_name) AS  customer_name,
    TRIM(city) AS city,
    TRY_CAST(modified_date AS DATE) AS modified_date,
    _source_file, _loaded_at, _run_id
FROM {{ source('bronze', 'customer') }}
WHERE TRY_CAST(customer_id AS BIGINT) IS NOT NULL
QUALIFY ROW_NUMBER() OVER(PARTITION BY TRY_CAST(customer_id AS BIGINT) ORDER BY _loaded_at DESC) = 1