DROP TABLE IF EXISTS gsk;
DROP TABLE IF EXISTS commitments;
DROP TABLE IF EXISTS qualified_nodes;
DROP TABLE IF EXISTS nodes;

CREATE TABLE gsk (
    user_id TEXT,
    gsk TEXT
);

CREATE TABLE commitments (
    user_id TEXT,
    x TEXT,
    y TEXT
);

CREATE TABLE qualified_nodes (
    user_id TEXT
);

CREATE TABLE nodes (
    user_id TEXT
);