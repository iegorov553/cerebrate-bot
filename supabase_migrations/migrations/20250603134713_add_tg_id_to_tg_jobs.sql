-- Add tg_id field to link activities with users
ALTER TABLE tg_jobs ADD COLUMN tg_id BIGINT;

-- Create index for better performance
CREATE INDEX idx_tg_jobs_tg_id ON tg_jobs(tg_id);

-- Optional: Add foreign key constraint (commented out for now)
-- ALTER TABLE tg_jobs ADD CONSTRAINT fk_tg_jobs_user 
-- FOREIGN KEY (tg_id) REFERENCES users(tg_id);