package main

import (
	"database/sql"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

var migrationBackupNow = time.Now

type migrationRunResult struct {
	Applied      int
	FromVersion  int
	FinalVersion int
}

type migrationStatusSnapshot struct {
	CurrentVersion int
	LatestVersion  int
	Completed      []migrationDefinition
	Pending        []migrationDefinition
}

type sqlQueryer interface {
	Query(query string, args ...any) (*sql.Rows, error)
	QueryRow(query string, args ...any) *sql.Row
}

func backupSQLiteBeforeMigration(cfg runtimeConfig, currentVersion, latestVersion int) (string, error) {
	if strings.TrimSpace(cfg.backupsDir) == "" {
		return "", errors.New("backup directory is required before migration")
	}
	if err := os.MkdirAll(cfg.backupsDir, 0755); err != nil {
		return "", err
	}
	timestamp := migrationBackupNow().Format("20060102_150405_000000000")
	backupName := fmt.Sprintf("prism_go_pre_migrate_v%d_to_v%d_%s.db", currentVersion, latestVersion, timestamp)
	backupPath := filepath.Join(cfg.backupsDir, backupName)
	if !isSubpath(backupPath, cfg.backupsDir) {
		return "", fmt.Errorf("backup path %q escapes backup directory", backupPath)
	}
	if err := copyFileExclusive(cfg.dbPath, backupPath); err != nil {
		return "", err
	}
	for _, suffix := range []string{"-wal", "-shm"} {
		if err := copyFileIfExists(cfg.dbPath+suffix, backupPath+suffix); err != nil {
			return "", err
		}
	}
	return backupPath, nil
}

func copyFileIfExists(src, dst string) error {
	if _, err := os.Stat(src); err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}
	return copyFileExclusive(src, dst)
}

func copyFileExclusive(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()
	out, err := os.OpenFile(dst, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if err != nil {
		return err
	}
	defer out.Close()
	if _, err := io.Copy(out, in); err != nil {
		return err
	}
	return out.Sync()
}

func runExistingDBMigrations(owner *sqliteConnectionOwner, definitions []migrationDefinition) (migrationRunResult, error) {
	result := migrationRunResult{}
	if owner == nil {
		return result, errors.New("SQLite connection owner is required for migrations")
	}
	if len(definitions) == 0 {
		return result, errors.New("migration definitions are required")
	}
	err := owner.withTransaction(func(tx *sql.Tx) error {
		if err := ensureSchemaMeta(tx); err != nil {
			return err
		}
		current, err := schemaMetaVersion(tx)
		if err != nil {
			return err
		}
		if current == 0 {
			detected, err := detectExistingSchemaVersion(tx)
			if err != nil {
				return err
			}
			if detected > 0 {
				if _, err := tx.Exec("UPDATE Schema_Meta SET value = ? WHERE key = 'schema_version'", strconv.Itoa(detected)); err != nil {
					return err
				}
				current = detected
			}
		}
		result.FromVersion = current
		result.FinalVersion = current
		for _, migration := range definitions {
			if migration.Version <= current {
				continue
			}
			for _, statement := range migration.Statements {
				sqlClean := strings.TrimSpace(statement)
				if sqlClean == "" {
					continue
				}
				if _, err := tx.Exec(sqlClean); err != nil {
					if skippableMigrationError(err) {
						continue
					}
					return fmt.Errorf("migration v%03d %s failed: %w", migration.Version, migration.Name, err)
				}
			}
			if _, err := tx.Exec("UPDATE Schema_Meta SET value = ? WHERE key = 'schema_version'", strconv.Itoa(migration.Version)); err != nil {
				return err
			}
			result.Applied++
			result.FinalVersion = migration.Version
			current = migration.Version
		}
		return nil
	})
	return result, err
}

func ensureSchemaMeta(tx *sql.Tx) error {
	if _, err := tx.Exec(`
		CREATE TABLE IF NOT EXISTS Schema_Meta (
			key TEXT PRIMARY KEY,
			value TEXT NOT NULL
		)`); err != nil {
		return err
	}
	_, err := tx.Exec("INSERT OR IGNORE INTO Schema_Meta (key, value) VALUES ('schema_version', '0')")
	return err
}

func migrationStatus(db *sql.DB) (migrationStatusSnapshot, error) {
	current, err := currentMigrationVersion(db)
	if err != nil {
		return migrationStatusSnapshot{}, err
	}
	status := migrationStatusSnapshot{
		CurrentVersion: current,
		LatestVersion:  latestMigrationVersion(),
		Completed:      []migrationDefinition{},
		Pending:        []migrationDefinition{},
	}
	for _, migration := range migrationDefinitions {
		if migration.Version > current {
			status.Pending = append(status.Pending, migration)
		} else {
			status.Completed = append(status.Completed, migration)
		}
	}
	return status, nil
}

func currentMigrationVersion(q sqlQueryer) (int, error) {
	current, err := schemaMetaVersion(q)
	if err != nil {
		if !missingSchemaMetaError(err) {
			return 0, err
		}
		current = 0
	}
	if current == 0 {
		detected, err := detectExistingSchemaVersion(q)
		if err != nil {
			return 0, err
		}
		if detected > 0 {
			return detected, nil
		}
	}
	return current, nil
}

func schemaMetaVersion(q sqlQueryer) (int, error) {
	var raw string
	if err := q.QueryRow("SELECT value FROM Schema_Meta WHERE key = 'schema_version'").Scan(&raw); err != nil {
		return 0, err
	}
	version, err := strconv.Atoi(raw)
	if err != nil {
		return 0, fmt.Errorf("invalid schema_version %q: %w", raw, err)
	}
	return version, nil
}

func detectExistingSchemaVersion(q sqlQueryer) (int, error) {
	version := 0
	checks := []struct {
		column  string
		version int
	}{
		{"is_pinned", 1},
		{"cover_position", 2},
		{"editor_layout", 3},
		{"is_archived", 4},
		{"sort_order", 5},
		{"category_id", 7},
	}
	for _, check := range checks {
		exists, err := columnExists(q, "Notes", check.column)
		if err != nil {
			return 0, err
		}
		if exists && check.version > version {
			version = check.version
		}
	}
	return version, nil
}

func columnExists(q sqlQueryer, table, column string) (bool, error) {
	rows, err := q.Query("PRAGMA table_info(" + table + ")")
	if err != nil {
		if missingSchemaObjectError(err) {
			return false, nil
		}
		return false, err
	}
	defer rows.Close()
	for rows.Next() {
		var cid int
		var name, columnType string
		var notNull int
		var defaultValue sql.NullString
		var pk int
		if err := rows.Scan(&cid, &name, &columnType, &notNull, &defaultValue, &pk); err != nil {
			return false, err
		}
		if name == column {
			return true, nil
		}
	}
	return false, rows.Err()
}

func latestMigrationVersion() int {
	latest := 0
	for _, migration := range migrationDefinitions {
		if migration.Version > latest {
			latest = migration.Version
		}
	}
	return latest
}

func skippableMigrationError(err error) bool {
	message := strings.ToLower(err.Error())
	return strings.Contains(message, "duplicate column name") || strings.Contains(message, "no such column")
}

func missingSchemaMetaError(err error) bool {
	return errors.Is(err, sql.ErrNoRows) || missingSchemaObjectError(err)
}

func missingSchemaObjectError(err error) bool {
	message := strings.ToLower(err.Error())
	return strings.Contains(message, "no such table") || strings.Contains(message, "no such column")
}

func initializeFreshDatabase(owner *sqliteConnectionOwner) error {
	if owner == nil {
		return errors.New("SQLite connection owner is required for fresh DB init")
	}
	return owner.withTransaction(func(tx *sql.Tx) error {
		for index, statement := range freshSchemaStatements {
			if _, err := tx.Exec(statement); err != nil {
				return fmt.Errorf("fresh schema statement %d failed: %w", index+1, err)
			}
		}
		if err := seedDefaultCategories(tx); err != nil {
			return err
		}
		if err := seedWelcomeNote(tx); err != nil {
			return err
		}
		return nil
	})
}

var freshSchemaStatements = []string{
	`CREATE TABLE Notes (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		content TEXT NOT NULL,
		remarks TEXT,
		cover_image TEXT,
		cover_position TEXT DEFAULT 'top',
		editor_layout TEXT DEFAULT 'single',
		is_pinned BOOLEAN NOT NULL DEFAULT 0,
		is_archived BOOLEAN NOT NULL DEFAULT 0,
		sort_order INTEGER,
		category_id INTEGER REFERENCES Categories(id),
		parent_id INTEGER REFERENCES Notes(id),
		prompt_params TEXT,
		created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
		updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
	)`,
	`CREATE INDEX idx_notes_updated_at ON Notes(updated_at DESC)`,
	`CREATE INDEX idx_notes_category_id ON Notes(category_id)`,
	`CREATE INDEX idx_notes_sort_order ON Notes(sort_order)`,
	`CREATE INDEX idx_notes_is_archived ON Notes(is_archived)`,
	`CREATE INDEX idx_notes_parent_id ON Notes(parent_id)`,
	`CREATE TABLE Categories (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		name TEXT NOT NULL UNIQUE,
		icon TEXT,
		sort_order INTEGER NOT NULL DEFAULT 0,
		is_default BOOLEAN NOT NULL DEFAULT 0,
		system_key TEXT UNIQUE,
		name_override TEXT,
		CHECK (system_key IS NULL OR system_key IN ('prompt', 'note', 'tutorial', 'data', 'inspiration'))
	)`,
	`CREATE UNIQUE INDEX idx_categories_system_key ON Categories(system_key) WHERE system_key IS NOT NULL`,
	`CREATE TABLE Tags (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		name TEXT NOT NULL UNIQUE COLLATE NOCASE
	)`,
	`CREATE UNIQUE INDEX idx_tags_name ON Tags(name COLLATE NOCASE)`,
	`CREATE TABLE Note_Tags (
		note_id INTEGER NOT NULL,
		tag_id INTEGER NOT NULL,
		PRIMARY KEY (note_id, tag_id),
		FOREIGN KEY (note_id) REFERENCES Notes(id) ON DELETE CASCADE,
		FOREIGN KEY (tag_id) REFERENCES Tags(id) ON DELETE CASCADE
	)`,
	`CREATE TABLE Source_Urls (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		note_id INTEGER NOT NULL,
		url TEXT NOT NULL,
		FOREIGN KEY (note_id) REFERENCES Notes(id) ON DELETE CASCADE
	)`,
	`CREATE INDEX idx_source_urls_note_id ON Source_Urls(note_id)`,
	`CREATE TABLE Note_History (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		note_id INTEGER NOT NULL,
		content TEXT NOT NULL,
		diff_summary TEXT,
		created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
		FOREIGN KEY (note_id) REFERENCES Notes(id) ON DELETE CASCADE
	)`,
	`CREATE INDEX idx_note_history_note_id ON Note_History(note_id)`,
	`CREATE TABLE Note_Attachments (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		note_id INTEGER NOT NULL,
		file_path TEXT NOT NULL,
		file_type TEXT DEFAULT 'md',
		title TEXT,
		size_bytes INTEGER,
		is_auto_extracted INTEGER DEFAULT 0,
		created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
		FOREIGN KEY (note_id) REFERENCES Notes(id) ON DELETE CASCADE
	)`,
	`CREATE INDEX idx_attachments_note_id ON Note_Attachments(note_id)`,
	`CREATE TABLE Schema_Meta (
		key TEXT PRIMARY KEY,
		value TEXT NOT NULL
	)`,
	`INSERT INTO Schema_Meta (key, value) VALUES ('schema_version', '17')`,
	`CREATE VIRTUAL TABLE Notes_FTS USING fts5(
		title,
		content,
		content='Notes',
		content_rowid='id'
	)`,
	`CREATE TRIGGER notes_ai AFTER INSERT ON Notes BEGIN
		INSERT INTO Notes_FTS(rowid, title, content) VALUES (new.id, new.title, new.content);
	END`,
	`CREATE TRIGGER notes_ad AFTER DELETE ON Notes BEGIN
		INSERT INTO Notes_FTS(Notes_FTS, rowid, title, content) VALUES('delete', old.id, old.title, old.content);
	END`,
	`CREATE TRIGGER notes_au AFTER UPDATE ON Notes BEGIN
		INSERT INTO Notes_FTS(Notes_FTS, rowid, title, content) VALUES('delete', old.id, old.title, old.content);
		INSERT INTO Notes_FTS(rowid, title, content) VALUES (new.id, new.title, new.content);
	END`,
}

type categorySeed struct {
	name      string
	icon      string
	systemKey string
	sortOrder int
	isDefault int
}

var defaultCategorySeeds = []categorySeed{
	{"提示詞 | Prompt", "🎨", "prompt", 1, 0},
	{"筆記 | Note", "📝", "note", 2, 1},
	{"教學 | Tutorial", "📚", "tutorial", 3, 0},
	{"資料 | Data", "💾", "data", 4, 0},
	{"靈感 | Inspiration", "💡", "inspiration", 5, 0},
}

var validCategorySystemKeys = map[string]bool{
	"prompt":      true,
	"note":        true,
	"tutorial":    true,
	"data":        true,
	"inspiration": true,
}

func categorySeedForSystemKey(systemKey string) (categorySeed, bool) {
	for _, seed := range defaultCategorySeeds {
		if seed.systemKey == systemKey {
			return seed, true
		}
	}
	return categorySeed{}, false
}

func normalizeCategorySystemKey(raw string) (string, bool) {
	key := strings.TrimSpace(raw)
	if key == "" {
		return "", true
	}
	if validCategorySystemKeys[key] {
		return key, true
	}
	return "", false
}

const welcomeNoteTitle = "👋 歡迎使用 Prism"

const welcomeNoteContent = `# 歡迎使用 Prism

這是一個本地運行的個人知識庫與 AI 提示詞管理工具。

## 快速上手

- **新增筆記**：點擊左上角「新增筆記」按鈕。
- **Prompt Builder**：點擊側邊欄「Prompt Builder」建立結構化提示詞。
- **搜尋**：支援全文檢索，輸入關鍵字即可快速找到筆記。

## Markdown 支援

支援標準 Markdown 語法，例如：

- **粗體**、*斜體*
- [連結](https://example.com)
- 程式碼區塊
- 引用

## 關於資料

所有資料皆儲存在本地端的 ` + "`knowledge.db`" + ` 資料庫中，您可以隨時備份此檔案。
`

func seedDefaultCategories(tx *sql.Tx) error {
	for _, seed := range defaultCategorySeeds {
		if _, err := tx.Exec(
			`INSERT OR IGNORE INTO Categories (name, icon, system_key, sort_order, is_default, name_override) VALUES (?, ?, ?, ?, ?, NULL)`,
			seed.name,
			seed.icon,
			seed.systemKey,
			seed.sortOrder,
			seed.isDefault,
		); err != nil {
			return fmt.Errorf("seed default category %q failed: %w", seed.name, err)
		}
	}
	return nil
}

func seedWelcomeNote(tx *sql.Tx) error {
	var count int
	if err := tx.QueryRow("SELECT COUNT(*) FROM Notes").Scan(&count); err != nil {
		return err
	}
	if count != 0 {
		return nil
	}
	var categoryID int
	if err := tx.QueryRow("SELECT id FROM Categories WHERE name LIKE '%教學%' LIMIT 1").Scan(&categoryID); err != nil {
		categoryID = 3
	}
	result, err := tx.Exec(
		`INSERT INTO Notes (title, content, category_id, remarks, created_at, updated_at)
		 VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)`,
		welcomeNoteTitle,
		welcomeNoteContent,
		categoryID,
		"系統自動生成",
	)
	if err != nil {
		return err
	}
	noteID, err := result.LastInsertId()
	if err != nil {
		return err
	}
	if _, err := tx.Exec("INSERT OR IGNORE INTO Tags (name) VALUES ('Welcome')"); err != nil {
		return err
	}
	var tagID int
	if err := tx.QueryRow("SELECT id FROM Tags WHERE name = 'Welcome'").Scan(&tagID); err != nil {
		return err
	}
	if _, err := tx.Exec("INSERT INTO Note_Tags (note_id, tag_id) VALUES (?, ?)", noteID, tagID); err != nil {
		return err
	}
	return nil
}

func openDB(dbPath string, enableWrites bool) (*sql.DB, error) {
	owner, err := openSQLiteOwner(dbPath, enableWrites)
	if err != nil {
		return nil, err
	}
	return owner.db, nil
}

func verifySchemaVersion(db *sql.DB, expected int) error {
	current, err := schemaVersion(db)
	if err != nil {
		return err
	}
	if current < expected {
		return fmt.Errorf("database schema version %d is older than expected %d", current, expected)
	}
	return nil
}

func schemaVersion(db *sql.DB) (int, error) {
	var raw string
	if err := db.QueryRow("SELECT value FROM Schema_Meta WHERE key = 'schema_version'").Scan(&raw); err != nil {
		return 0, fmt.Errorf("schema version check failed: %w", err)
	}
	version, err := strconv.Atoi(raw)
	if err != nil {
		return 0, fmt.Errorf("invalid schema_version %q: %w", raw, err)
	}
	return version, nil
}

type migrationDefinition struct {
	Version    int
	Name       string
	Statements []string
}

var migrationDefinitions = []migrationDefinition{
	{1, "add_is_pinned", []string{
		"ALTER TABLE Notes ADD COLUMN is_pinned INTEGER DEFAULT 0",
	}},
	{2, "add_cover_position", []string{
		"ALTER TABLE Notes ADD COLUMN cover_position TEXT DEFAULT 'top'",
	}},
	{3, "add_editor_layout", []string{
		"ALTER TABLE Notes ADD COLUMN editor_layout TEXT DEFAULT 'single'",
	}},
	{4, "add_is_archived", []string{
		"ALTER TABLE Notes ADD COLUMN is_archived INTEGER DEFAULT 0",
		"CREATE INDEX IF NOT EXISTS idx_notes_is_archived ON Notes(is_archived)",
	}},
	{5, "add_sort_order", []string{
		"ALTER TABLE Notes ADD COLUMN sort_order INTEGER DEFAULT 0",
		"CREATE INDEX IF NOT EXISTS idx_notes_sort_order ON Notes(sort_order)",
		"UPDATE Notes SET sort_order = id WHERE sort_order = 0 OR sort_order IS NULL",
	}},
	{6, "add_category_id", []string{
		"ALTER TABLE Notes ADD COLUMN category_id INTEGER REFERENCES Categories(id)",
		"CREATE INDEX IF NOT EXISTS idx_notes_category_id ON Notes(category_id)",
	}},
	{7, "populate_category_id", []string{
		`UPDATE Notes SET category_id = (
			SELECT id FROM Categories WHERE name = Notes.type LIMIT 1
		) WHERE category_id IS NULL`,
		`UPDATE Notes SET category_id = (
			SELECT id FROM Categories WHERE is_default = 1 LIMIT 1
		) WHERE category_id IS NULL`,
		`UPDATE Notes SET category_id = (
			SELECT id FROM Categories ORDER BY sort_order LIMIT 1
		) WHERE category_id IS NULL`,
	}},
	{8, "add_note_attachments", []string{
		`CREATE TABLE IF NOT EXISTS Note_Attachments (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			note_id INTEGER NOT NULL,
			file_path TEXT NOT NULL,
			file_type TEXT DEFAULT 'md',
			title TEXT,
			size_bytes INTEGER,
			is_auto_extracted INTEGER DEFAULT 0,
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (note_id) REFERENCES Notes(id) ON DELETE CASCADE
		)`,
		"CREATE INDEX IF NOT EXISTS idx_attachments_note_id ON Note_Attachments(note_id)",
	}},
	{9, "add_text_embedding", []string{
		"ALTER TABLE Notes ADD COLUMN text_embedding BLOB",
		"ALTER TABLE Notes ADD COLUMN embedding_updated_at DATETIME",
	}},
	{10, "add_ai_metadata_and_lineage", []string{
		"ALTER TABLE Notes ADD COLUMN ai_summary TEXT",
		"ALTER TABLE Notes ADD COLUMN ai_tags TEXT",
		"ALTER TABLE Notes ADD COLUMN embedding_status TEXT",
		"ALTER TABLE Notes ADD COLUMN parent_id INTEGER REFERENCES Notes(id)",
		"CREATE INDEX IF NOT EXISTS idx_notes_parent_id ON Notes(parent_id)",
	}},
	{11, "create_embeddings_table", []string{
		`CREATE TABLE IF NOT EXISTS Embeddings (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			resource_type TEXT NOT NULL,
			resource_id INTEGER NOT NULL,
			chunk_index INTEGER DEFAULT 0,
			model_name TEXT NOT NULL,
			vector BLOB NOT NULL,
			content_hash TEXT,
			dimensions INTEGER,
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
			UNIQUE(resource_type, resource_id, chunk_index)
		)`,
		"CREATE INDEX IF NOT EXISTS idx_embeddings_resource ON Embeddings(resource_type, resource_id)",
	}},
	{12, "kill_notes_type", []string{
		`UPDATE Notes
		SET category_id = (SELECT id FROM Categories WHERE is_default = 1 LIMIT 1)
		WHERE category_id IS NULL`,
		`UPDATE Notes
		SET category_id = (SELECT id FROM Categories ORDER BY sort_order LIMIT 1)
		WHERE category_id IS NULL`,
		"DROP INDEX IF EXISTS idx_notes_type",
		"ALTER TABLE Notes DROP COLUMN type",
	}},
	{13, "create_ai_tasks_table", []string{
		`CREATE TABLE IF NOT EXISTS AI_Tasks (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			task_type TEXT NOT NULL,
			status TEXT NOT NULL DEFAULT 'pending',
			payload TEXT NOT NULL,
			result TEXT,
			retry_count INTEGER DEFAULT 0,
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
			updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
		)`,
		"CREATE INDEX IF NOT EXISTS idx_ai_tasks_status ON AI_Tasks(status)",
		"CREATE INDEX IF NOT EXISTS idx_ai_tasks_type ON AI_Tasks(task_type)",
		"CREATE INDEX IF NOT EXISTS idx_ai_tasks_created ON AI_Tasks(created_at)",
	}},
	{14, "strip_ai_features", []string{
		"ALTER TABLE Notes DROP COLUMN text_embedding",
		"ALTER TABLE Notes DROP COLUMN embedding_updated_at",
		"ALTER TABLE Notes DROP COLUMN ai_summary",
		"ALTER TABLE Notes DROP COLUMN ai_tags",
		"ALTER TABLE Notes DROP COLUMN embedding_status",
		"DROP TABLE IF EXISTS AI_Tasks",
		"DROP TABLE IF EXISTS Embeddings",
		"DROP INDEX IF EXISTS idx_ai_tasks_status",
		"DROP INDEX IF EXISTS idx_ai_tasks_type",
		"DROP INDEX IF EXISTS idx_ai_tasks_created",
		"DROP INDEX IF EXISTS idx_embeddings_resource",
	}},
	{15, "add_prompt_params", []string{
		"ALTER TABLE Notes ADD COLUMN prompt_params TEXT",
	}},
	{16, "normalize_editor_layout", []string{
		"UPDATE Notes SET editor_layout = 'single' WHERE editor_layout IS NULL OR editor_layout = 'full'",
	}},
	{17, "add_category_identity", []string{
		"ALTER TABLE Categories ADD COLUMN system_key TEXT",
		"ALTER TABLE Categories ADD COLUMN name_override TEXT",
		"UPDATE Categories SET system_key = 'prompt', name_override = NULL WHERE name = '提示詞 | Prompt' AND (system_key IS NULL OR system_key = '')",
		"UPDATE Categories SET system_key = 'note', name_override = NULL WHERE name = '筆記 | Note' AND (system_key IS NULL OR system_key = '')",
		"UPDATE Categories SET system_key = 'tutorial', name_override = NULL WHERE name = '教學 | Tutorial' AND (system_key IS NULL OR system_key = '')",
		"UPDATE Categories SET system_key = 'data', name_override = NULL WHERE name = '資料 | Data' AND (system_key IS NULL OR system_key = '')",
		"UPDATE Categories SET system_key = 'inspiration', name_override = NULL WHERE name = '靈感 | Inspiration' AND (system_key IS NULL OR system_key = '')",
		"UPDATE Categories SET name_override = NULL WHERE name_override = ''",
		"CREATE UNIQUE INDEX IF NOT EXISTS idx_categories_system_key ON Categories(system_key) WHERE system_key IS NOT NULL",
	}},
}
