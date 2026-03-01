-- Migration: Add session_mode, title, ai_character, mode columns to practice_history
-- Run this in Supabase SQL Editor (Dashboard > SQL Editor > New Query)

ALTER TABLE practice_history ADD COLUMN IF NOT EXISTS session_mode TEXT;
ALTER TABLE practice_history ADD COLUMN IF NOT EXISTS title TEXT;
ALTER TABLE practice_history ADD COLUMN IF NOT EXISTS ai_character TEXT DEFAULT 'alex';
ALTER TABLE practice_history ADD COLUMN IF NOT EXISTS mode TEXT;
