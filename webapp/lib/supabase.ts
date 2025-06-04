import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

export type ActivityRecord = {
  job_uid: string
  tg_name: string
  jobs_timestamp: string
  job_text: string
}

export type UserRecord = {
  user_id: string
  tg_id: number
  tg_username: string
  tg_first_name: string
  tg_last_name: string
  enabled: boolean
  window_start: string
  window_end: string
  interval_min: number
  created_at: string
  updated_at: string
  last_notification_sent: string | null
}

export type FriendRecord = {
  tg_id: number
  tg_username?: string
  tg_first_name?: string
  tg_last_name?: string
}

// Function to get user's friends list
export async function getFriendsList(userId: number): Promise<FriendRecord[]> {
  try {
    // Get accepted friendships where user is either requester or addressee
    const { data: friendshipsData, error: friendshipsError } = await supabase
      .from('friendships')
      .select('requester_id, addressee_id')
      .eq('status', 'accepted')
      .or(`requester_id.eq.${userId},addressee_id.eq.${userId}`);

    if (friendshipsError) throw friendshipsError;

    const friends: FriendRecord[] = [];
    const friendIds: number[] = [];
    
    // Collect friend IDs
    for (const friendship of friendshipsData || []) {
      if (friendship.requester_id === userId) {
        friendIds.push(friendship.addressee_id);
      } else {
        friendIds.push(friendship.requester_id);
      }
    }

    // Get user info for each friend in batch
    if (friendIds.length > 0) {
      const { data: usersData, error: usersError } = await supabase
        .from('users')
        .select('tg_id, tg_username, tg_first_name, tg_last_name')
        .in('tg_id', friendIds);

      if (usersError) throw usersError;

      friends.push(...(usersData || []));
    }

    return friends;
  } catch (error) {
    console.error('Error fetching friends:', error);
    return [];
  }
}