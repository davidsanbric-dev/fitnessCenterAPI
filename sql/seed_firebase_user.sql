-- Idempotent seed for Firebase-linked API user
-- Target email: davidsnbr@gmail.com

INSERT INTO users (email, password_hash, is_active, created_at)
SELECT
  'davidsnbr@gmail.com',
  'firebase_managed_account',
  1,
  CURRENT_TIMESTAMP
WHERE NOT EXISTS (
  SELECT 1
  FROM users
  WHERE lower(email) = lower('davidsnbr@gmail.com')
);

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
  '+569' || substr(hex(randomblob(6)), 1, 8),
  NULL,
  date('1994-08-12'),
  'Santiago, Chile',
  NULL,
  'Improve resistance and mobility'
FROM users u
WHERE lower(u.email) = lower('davidsnbr@gmail.com')
  AND NOT EXISTS (
    SELECT 1
    FROM member_profiles mp
    WHERE mp.user_id = u.id
  );
