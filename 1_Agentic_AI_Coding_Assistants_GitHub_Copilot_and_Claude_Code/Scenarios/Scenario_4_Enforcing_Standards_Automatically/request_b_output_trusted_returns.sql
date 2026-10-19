CREATE TABLE trusted_returns (
    return_date DATE NOT NULL,
    retailer_id STRING NOT NULL,
    sku STRING NOT NULL,
    units_returned INT NOT NULL,
    reason_code STRING
);
