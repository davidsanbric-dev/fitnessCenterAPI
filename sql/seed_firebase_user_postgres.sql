-- Idempotent seed for Firebase-linked API user (PostgreSQL)
-- Target email: davidsnbr@gmail.com

INSERT INTO users (
  email,
  password_hash,
  is_active,
  created_at
)
VALUES (
  'davidsnbr@gmail.com',
  'firebase_managed_account',
  TRUE,
  CURRENT_TIMESTAMP
)
ON CONFLICT (email) DO NOTHING;

INSERT INTO member_profiles (
  user_id,
  first_name,
  paternal_surname,
  maternal_surname,
  mobile_phone,
  landline_phone,
  birth_date,
  address,
  avatar_url,
  fitness_goals
)
SELECT
  u.id,
  'David',
  'Snbr',
  'Dev',
  '+569' || substring(md5(random()::text), 1, 8),
  NULL,
  DATE '1994-08-12',
  'Santiago, Chile',
  NULL,
  'Improve resistance and mobility'
FROM users u
WHERE lower(u.email) = lower('davidsnbr@gmail.com')
ON CONFLICT (user_id) DO NOTHING;
