-- ============================================
-- CoAct AI - Complete Database Schema
-- Run this in Supabase SQL Editor
-- ============================================

-- ============================================
-- TABLE 1: profiles
-- Stores extended user profile information
-- Links to Supabase auth.users via user_id
-- ============================================
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT,
    email TEXT,
    avatar_url TEXT,
    organization TEXT,
    role TEXT DEFAULT 'user',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Auto-create profile when user signs up
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, full_name, email)
    VALUES (
        NEW.id,
        NEW.raw_user_meta_data->>'full_name',
        NEW.email
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger: auto-create profile on signup
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ============================================
-- TABLE 2: practice_history
-- Stores all coaching/assessment session data
-- Links to profiles via user_id
-- ============================================
CREATE TABLE IF NOT EXISTS practice_history (
    session_id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    scenario_type TEXT DEFAULT 'custom',
    session_mode TEXT,
    title TEXT,
    ai_character TEXT DEFAULT 'alex',
    mode TEXT,
    role TEXT,
    ai_role TEXT,
    scenario TEXT,
    framework JSONB,
    transcript JSONB DEFAULT '[]'::jsonb,
    report_data JSONB DEFAULT '{}'::jsonb,
    completed BOOLEAN DEFAULT FALSE,
    score NUMERIC,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- TABLE 3: feedback
-- Stores user feedback on sessions/reports
-- Links to practice_history and profiles
-- ============================================
CREATE TABLE IF NOT EXISTS feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    session_id TEXT REFERENCES practice_history(session_id) ON DELETE SET NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    feedback_type TEXT DEFAULT 'general',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- TABLE 4: contact_submissions
-- Stores Contact Sales form submissions
-- No auth required (public form)
-- ============================================
CREATE TABLE IF NOT EXISTS contact_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    company TEXT,
    team_size TEXT,
    message TEXT,
    status TEXT DEFAULT 'new',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDEXES
-- ============================================
CREATE INDEX IF NOT EXISTS idx_profiles_email ON profiles(email);
CREATE INDEX IF NOT EXISTS idx_practice_history_user_id ON practice_history(user_id);
CREATE INDEX IF NOT EXISTS idx_practice_history_created_at ON practice_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_practice_history_scenario_type ON practice_history(scenario_type);
CREATE INDEX IF NOT EXISTS idx_practice_history_completed ON practice_history(completed);
CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_session_id ON feedback(session_id);

-- ============================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================

-- Profiles
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own profile" ON profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON profiles FOR UPDATE USING (auth.uid() = id);
CREATE POLICY "Service role full access profiles" ON profiles FOR ALL USING (auth.role() = 'service_role');

-- Practice History
ALTER TABLE practice_history ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own sessions" ON practice_history FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own sessions" ON practice_history FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own sessions" ON practice_history FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own sessions" ON practice_history FOR DELETE USING (auth.uid() = user_id);
CREATE POLICY "Service role full access sessions" ON practice_history FOR ALL USING (auth.role() = 'service_role');

-- Feedback
ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own feedback" ON feedback FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own feedback" ON feedback FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Service role full access feedback" ON feedback FOR ALL USING (auth.role() = 'service_role');
