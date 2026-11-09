CREATE TABLE run (
    run_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_dir VARCHAR(500) NOT NULL,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT TIMESTAMP,
    finished_at TIMESTAMP,
    exit_code INTEGER
);

CREATE TABLE comparison_result (
    result_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id INTEGER NOT NULL,
    query_id VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    risk_score INTEGER,
    risk_label VARCHAR(10),
    note VARCHAR(500),
    source_sql VARCHAR(3000),
    db2_sql VARCHAR(3000),
    diff_summary VARCHAR(1000)
);
