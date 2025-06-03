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