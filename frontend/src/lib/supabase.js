import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://dnynpdlpdcyorqvvtqxa.supabase.co'
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'sbp_HSv_s9het49_A2HIfGYv1g_JTtbirBM'

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
