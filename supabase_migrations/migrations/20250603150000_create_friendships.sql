-- Create friendships table for friend requests and relationships
CREATE TABLE friendships (
  friendship_id uuid NOT NULL DEFAULT gen_random_uuid(),
  requester_id bigint NOT NULL,
  addressee_id bigint NOT NULL,
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted')),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  
  CONSTRAINT friendships_pkey PRIMARY KEY (friendship_id),
  CONSTRAINT friendships_requester_fkey FOREIGN KEY (requester_id) REFERENCES users(tg_id),
  CONSTRAINT friendships_addressee_fkey FOREIGN KEY (addressee_id) REFERENCES users(tg_id),
  CONSTRAINT friendships_unique UNIQUE (requester_id, addressee_id),
  CONSTRAINT friendships_no_self CHECK (requester_id != addressee_id)
);

-- Create indexes for better performance
CREATE INDEX idx_friendships_requester ON friendships(requester_id);
CREATE INDEX idx_friendships_addressee ON friendships(addressee_id);
CREATE INDEX idx_friendships_status ON friendships(status);

-- RLS policies for friendships
ALTER TABLE friendships ENABLE ROW LEVEL SECURITY;

-- Users can see friendships where they are involved
CREATE POLICY "Users can see their own friendships" ON friendships
  FOR SELECT
  USING (requester_id = current_setting('request.jwt.claims', true)::json->>'tg_id'::bigint
         OR addressee_id = current_setting('request.jwt.claims', true)::json->>'tg_id'::bigint);

-- Users can create friend requests
CREATE POLICY "Users can create friend requests" ON friendships
  FOR INSERT
  WITH CHECK (requester_id = current_setting('request.jwt.claims', true)::json->>'tg_id'::bigint);

-- Users can update friendships they're involved in (accept/decline)
CREATE POLICY "Users can update their friendships" ON friendships
  FOR UPDATE
  USING (requester_id = current_setting('request.jwt.claims', true)::json->>'tg_id'::bigint
         OR addressee_id = current_setting('request.jwt.claims', true)::json->>'tg_id'::bigint);