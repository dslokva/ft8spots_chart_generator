-- `default`.dxcc_list definition
CREATE TABLE default.dxcc_list
(
    `prefix` String,
    `entity` String,
    `cont` String,
    `itu` String,
    `cq` String,
    `entity_code` UInt16,
    `deleted` UInt8
)
ENGINE = MergeTree
PRIMARY KEY entity_code
ORDER BY entity_code
SETTINGS index_granularity = 8192;