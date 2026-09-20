CREATE TABLE IF NOT EXISTS presets (
    preset_id INTEGER PRIMARY KEY AUTOINCREMENT,
    preset_name TEXT NOT NULL UNIQUE,
    preset_path TEXT NOT NULL UNIQUE,
    keywords TEXT NOT NULL DEFAULT '[]',
    ar TEXT NOT NULL DEFAULT 'non-square' CHECK (ar IN ('square', 'non-square')),
    created_date TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_presets_name ON presets (preset_name);
