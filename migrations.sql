-- 1. Create users table if not already existing
CREATE TABLE IF NOT EXISTS users (
	id UUID NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	hashed_password VARCHAR(255), 
	is_active BOOLEAN, 
	created_at TIMESTAMP WITH TIME ZONE, 
	settings JSON, 
	PRIMARY KEY (id)
);

-- 2. Add hashed_password column to users if table already existed without it (Phase 1 fallback)
ALTER TABLE users ADD COLUMN IF NOT EXISTS hashed_password VARCHAR(255);

-- 3. Create unique index on users.email
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);

-- 4. Create events table
CREATE TABLE IF NOT EXISTS events (
	id UUID NOT NULL, 
	source VARCHAR(50) NOT NULL, 
	type VARCHAR(50) NOT NULL, 
	priority INTEGER, 
	payload JSON NOT NULL, 
	status VARCHAR(20), 
	summary TEXT, 
	timestamp TIMESTAMP WITHOUT TIME ZONE, 
	processed_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);

-- 5. Create indices on events
CREATE INDEX IF NOT EXISTS ix_events_priority ON events (priority);
CREATE INDEX IF NOT EXISTS ix_events_status ON events (status);
CREATE INDEX IF NOT EXISTS ix_events_source ON events (source);

-- 6. Create memories table
CREATE TABLE IF NOT EXISTS memories (
	id UUID NOT NULL, 
	content TEXT NOT NULL, 
	embedding VECTOR(768), 
	tags JSON, 
	importance INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);

-- 7. Create action approvals table
CREATE TABLE IF NOT EXISTS action_approvals (
	id UUID NOT NULL, 
	integration VARCHAR(50) NOT NULL, 
	action_type VARCHAR(50) NOT NULL, 
	payload JSON NOT NULL, 
	status VARCHAR(20), 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	processed_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);

-- 8. Create index on approvals
CREATE INDEX IF NOT EXISTS ix_action_approvals_status ON action_approvals (status);

-- 9. Create integrations table
CREATE TABLE IF NOT EXISTS integrations (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	provider VARCHAR(50) NOT NULL, 
	credentials JSON, 
	is_active BOOLEAN, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- 10. Create index on integrations
CREATE INDEX IF NOT EXISTS ix_integrations_provider ON integrations (provider);