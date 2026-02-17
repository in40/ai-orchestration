-- Create new task_registry table with proper lifecycle tracking
CREATE TABLE IF NOT EXISTS task_registry (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(255) UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    
    -- Submitter information
    submitter VARCHAR(255) NOT NULL,
    submitter_type VARCHAR(50) NOT NULL CHECK (submitter_type IN ('human', 'agent', 'system', 'api')),
    
    -- Transport/channel information
    transport_channel VARCHAR(50) NOT NULL DEFAULT 'unknown' CHECK (transport_channel IN ('http', 'stdio', 'streamable-http', 'api', 'websocket', 'unknown')),
    
    -- Assignment information
    assigned_to VARCHAR(255) DEFAULT 'unassigned',
    
    -- Status tracking
    status VARCHAR(50) NOT NULL DEFAULT 'received' CHECK (status IN (
        'received',
        'pending_assignment',
        'assigned',
        'requirements_collection',
        'in_progress',
        'blocked',
        'review',
        'done',
        'failed',
        'cancelled'
    )),
    status_reason TEXT,
    
    -- Priority and timing
    priority VARCHAR(20) NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    deadline TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Source and result
    source_server VARCHAR(255),
    target_server VARCHAR(255),
    result TEXT,
    
    -- Metadata and audit trail
    metadata JSONB DEFAULT '{}',
    status_history JSONB DEFAULT '[]'
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_task_registry_task_id ON task_registry(task_id);
CREATE INDEX IF NOT EXISTS idx_task_registry_status ON task_registry(status);
CREATE INDEX IF NOT EXISTS idx_task_registry_assigned_to ON task_registry(assigned_to);
CREATE INDEX IF NOT EXISTS idx_task_registry_submitter ON task_registry(submitter);
CREATE INDEX IF NOT EXISTS idx_task_registry_priority ON task_registry(priority);
CREATE INDEX IF NOT EXISTS idx_task_registry_created_at ON task_registry(created_at);

-- Add comment
COMMENT ON TABLE task_registry IS 'Task registry with full lifecycle tracking including submitter, transport channel, assignment, and status history';
