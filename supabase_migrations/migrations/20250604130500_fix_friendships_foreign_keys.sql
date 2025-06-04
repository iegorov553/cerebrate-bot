-- Fix foreign key relationships for friendships table
-- This ensures the relationships work correctly with PostgREST

-- First, let's ensure the friendship table has the correct structure
-- and foreign keys are properly defined

-- Drop existing foreign key constraints if they exist
ALTER TABLE friendships DROP CONSTRAINT IF EXISTS friendships_requester_fkey;
ALTER TABLE friendships DROP CONSTRAINT IF EXISTS friendships_addressee_fkey;

-- Recreate foreign key constraints with proper naming
ALTER TABLE friendships 
ADD CONSTRAINT friendships_requester_id_fkey 
FOREIGN KEY (requester_id) REFERENCES users(tg_id) ON DELETE CASCADE;

ALTER TABLE friendships 
ADD CONSTRAINT friendships_addressee_id_fkey 
FOREIGN KEY (addressee_id) REFERENCES users(tg_id) ON DELETE CASCADE;

-- Update RLS policies to allow anonymous access for bot operations
DROP POLICY IF EXISTS "Users can see their own friendships" ON friendships;
DROP POLICY IF EXISTS "Users can create friend requests" ON friendships;
DROP POLICY IF EXISTS "Users can update their friendships" ON friendships;

-- Create simple policy for anonymous access (for service role operations)
CREATE POLICY "Allow anonymous access to friendships" ON friendships
  FOR ALL TO anon USING (true);

-- Refresh the schema cache
NOTIFY pgrst, 'reload schema';