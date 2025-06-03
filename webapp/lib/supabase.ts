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
    const { data, error } = await supabase
      .from('friendships')
      .select(`
        *, 
        requester:users!friendships_requester_id_fkey(tg_id, tg_username, tg_first_name, tg_last_name),
        addressee:users!friendships_addressee_id_fkey(tg_id, tg_username, tg_first_name, tg_last_name)
      `)
      .eq('status', 'accepted')
      .or(`requester_id.eq.${userId},addressee_id.eq.${userId}`);

    if (error) throw error;

    const friends: FriendRecord[] = [];
    
    for (const friendship of data || []) {
      // Add the friend (not the current user)
      if (friendship.requester_id === userId) {
        friends.push(friendship.addressee);
      } else {
        friends.push(friendship.requester);
      }
    }

    return friends;
  } catch (error) {
    console.error('Error fetching friends:', error);
    return [];
  }
}