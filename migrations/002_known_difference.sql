CREATE TABLE known_difference (
    difference_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    source_pattern VARCHAR(2000) NOT NULL,
    db2_pattern VARCHAR(2000) NOT NULL,
    cause VARCHAR(2000),
    fix_template VARCHAR(2000),
    verified SMALLINT NOT NULL DEFAULT 0,
    evidence_run_id INTEGER,
    embedding VECTOR(384, FLOAT32)
);
