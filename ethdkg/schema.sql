DROP TABLE IF EXISTS gsk;
DROP TABLE IF EXISTS commitments;

CREATE TABLE gsk (
    user_id TEXT,
    gsk TEXT
);

CREATE TABLE commitments (
    user_id TEXT,
    x TEXT,
    y TEXT
);