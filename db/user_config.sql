CREATE TABLE IF NOT EXISTS UserConfig (
    user_config_id INTEGER PRIMARY KEY CHECK (user_config_id = 1), -- always single record as we have a single user
    consent_given BOOLEAN NOT NULL DEFAULT 0,
    use_external_services BOOLEAN NOT NULL DEFAULT 0,
    external_services TEXT,         -- JSON e.g. {"openai": {"allowed": True}}
    default_ignore_patterns TEXT,   -- e.g. ["*.log", "*.env"]
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER IF NOT EXISTS UserConfigUpdateTimestamp
AFTER UPDATE ON UserConfig
BEGIN
    UPDATE UserConfig 
    SET updated_at = CURRENT_TIMESTAMP
    WHERE user_config_id = NEW.user_config_id;
END;