from __future__ import annotations

from alembic import op

revision = "20260525_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
	op.execute(
		"""
		-- Unified seed for Gym Scheduling API (PostgreSQL)
		-- Combines reference data and Firebase-linked user seed
		-- Idempotent: safe to run multiple times

		-- =============================================================================
		-- LOCATIONS (location_code is unique)
		-- =============================================================================
		INSERT INTO locations (location_code, name) VALUES
		  ('LOC001', 'Downtown Gym'),
		  ('LOC002', 'North Branch')
		ON CONFLICT (location_code) DO NOTHING;

		-- =============================================================================
		-- DISCIPLINES (discipline_code is unique)
		-- =============================================================================
		INSERT INTO disciplines (discipline_code, name, description, icon_url) VALUES
		  ('YOGA', 'Yoga', 'Mobility and mindful movement', '/icons/yoga.svg'),
		  ('CROSSFIT', 'CrossFit', 'High intensity functional training', '/icons/crossfit.svg'),
		  ('PILATES', 'Pilates', 'Core strength and posture', '/icons/pilates.svg')
		ON CONFLICT (discipline_code) DO NOTHING;

		-- =============================================================================
		-- MEMBERSHIP PLANS (name is unique)
		-- =============================================================================
		INSERT INTO membership_plans (
		  name, description, price, duration_days, features,
		  max_bookings_per_month, includes_personal_training
		) VALUES
		  ('Basic', 'Access to essential classes', 29.99, 30, '["Gym floor access", "2 group classes per week"]'::json, 8, FALSE),
		  ('Premium', 'Unlimited classes and amenities', 59.99, 30, '["Unlimited classes", "Sauna access", "Nutrition webinar"]'::json, 30, TRUE),
		  ('VIP', 'All access with premium coaching', 89.99, 30, '["Unlimited classes", "2 PT sessions", "Priority booking"]'::json, 50, TRUE)
		ON CONFLICT (name) DO NOTHING;

		-- =============================================================================
		-- CLASS CATEGORIES (use sequential IDs for idempotency via exclusion)
		-- =============================================================================
		-- Mind & Body category
		DO $$
		BEGIN
		  IF NOT EXISTS (SELECT 1 FROM class_categories WHERE name = 'Mind & Body') THEN
			INSERT INTO class_categories (name, icon_url, location_id)
			VALUES ('Mind & Body', '/icons/mind-body.svg', (SELECT id FROM locations WHERE location_code = 'LOC001'));
		  END IF;
		END $$;

		-- Performance category
		DO $$
		BEGIN
		  IF NOT EXISTS (SELECT 1 FROM class_categories WHERE name = 'Performance') THEN
			INSERT INTO class_categories (name, icon_url, location_id)
			VALUES ('Performance', '/icons/performance.svg', (SELECT id FROM locations WHERE location_code = 'LOC002'));
		  END IF;
		END $$;

		-- =============================================================================
		-- CLASS SUBCATEGORIES
		-- =============================================================================
		DO $$
		BEGIN
		  IF NOT EXISTS (SELECT 1 FROM class_subcategories WHERE name = 'Yoga Flow') THEN
			INSERT INTO class_subcategories (name, category_id)
			VALUES ('Yoga Flow', (SELECT id FROM class_categories WHERE name = 'Mind & Body'));
		  END IF;
		END $$;

		DO $$
		BEGIN
		  IF NOT EXISTS (SELECT 1 FROM class_subcategories WHERE name = 'Strength') THEN
			INSERT INTO class_subcategories (name, category_id)
			VALUES ('Strength', (SELECT id FROM class_categories WHERE name = 'Performance'));
		  END IF;
		END $$;

		-- =============================================================================
		-- CLASS TYPES
		-- =============================================================================
		DO $$
		BEGIN
		  IF NOT EXISTS (SELECT 1 FROM class_types WHERE name = 'Sunrise Yoga') THEN
			INSERT INTO class_types (name, subcategory_id, location_id, schedule_type, preparation_info, pdf_code)
			VALUES (
			  'Sunrise Yoga',
			  (SELECT id FROM class_subcategories WHERE name = 'Yoga Flow'),
			  (SELECT id FROM locations WHERE location_code = 'LOC001'),
			  'GROUP',
			  'Bring a yoga mat and water bottle.',
			  'YOGA-001'
			);
		  END IF;
		END $$;

		DO $$
		BEGIN
		  IF NOT EXISTS (SELECT 1 FROM class_types WHERE name = 'CrossFit Starter') THEN
			INSERT INTO class_types (name, subcategory_id, location_id, schedule_type, preparation_info, pdf_code)
			VALUES (
			  'CrossFit Starter',
			  (SELECT id FROM class_subcategories WHERE name = 'Strength'),
			  (SELECT id FROM locations WHERE location_code = 'LOC002'),
			  'GROUP',
			  'Arrive 10 minutes early for warm-up.',
			  'CF-010'
			);
		  END IF;
		END $$;

		-- =============================================================================
		-- TRAINERS (trainer_code is unique)
		-- =============================================================================
		INSERT INTO trainers (trainer_code, full_name, bio, photo_url, certifications, is_active, location_id)
		VALUES (
		  1001,
		  'Sofia Ramirez',
		  'Yoga instructor focused on flexibility and balance.',
		  '/images/trainers/sofia.jpg',
		  '["RYT-500", "Mobility Coach"]'::json,
		  TRUE,
		  (SELECT id FROM locations WHERE location_code = 'LOC001')
		)
		ON CONFLICT (trainer_code) DO NOTHING;

		INSERT INTO trainers (trainer_code, full_name, bio, photo_url, certifications, is_active, location_id)
		VALUES (
		  1002,
		  'Diego Herrera',
		  'Cross-training coach with performance background.',
		  '/images/trainers/diego.jpg',
		  '["CrossFit Level 2", "TRX Coach"]'::json,
		  TRUE,
		  (SELECT id FROM locations WHERE location_code = 'LOC002')
		)
		ON CONFLICT (trainer_code) DO NOTHING;

		-- =============================================================================
		-- TRAINER-DISCIPLINE ASSOCIATIONS (compound PK: trainer_id + discipline_id)
		-- =============================================================================
		INSERT INTO trainer_disciplines (trainer_id, discipline_id)
		SELECT t.id, d.id
		FROM trainers t
		JOIN disciplines d ON (t.trainer_code = 1001 AND d.discipline_code IN ('YOGA', 'PILATES'))
		                   OR (t.trainer_code = 1002 AND d.discipline_code = 'CROSSFIT')
		ON CONFLICT DO NOTHING;

		-- =============================================================================
		-- TRAINER-MEMBERSHIP PLAN ASSOCIATIONS (compound PK: trainer_id + membership_plan_id)
		-- =============================================================================
		INSERT INTO trainer_membership_plans (trainer_id, membership_plan_id)
		SELECT t.id, mp.id
		FROM trainers t
		JOIN membership_plans mp ON TRUE
		WHERE t.trainer_code = 1001
		   OR (t.trainer_code = 1002 AND mp.name IN ('Premium', 'VIP'))
		ON CONFLICT DO NOTHING;

		-- =============================================================================
		-- MEMBERSHIP PLAN - CATEGORY ASSOCIATIONS (compound PK: membership_plan_id + class_category_id)
		-- =============================================================================
		INSERT INTO membership_plan_categories (membership_plan_id, class_category_id)
		SELECT mp.id, cc.id
		FROM membership_plans mp
		CROSS JOIN class_categories cc
		WHERE (cc.name = 'Mind & Body' AND mp.name IN ('Basic', 'Premium', 'VIP'))
		   OR (cc.name = 'Performance' AND mp.name IN ('Premium', 'VIP'))
		ON CONFLICT DO NOTHING;

		-- =============================================================================
		-- SLOTS (unique constraint: uq_slot_trainer_datetime on trainer_id + slot_datetime)
		-- =============================================================================
		INSERT INTO slots (
		  slot_datetime, location_id, trainer_id, discipline_id,
		  class_type_id, is_online, is_available, slot_assignment_code, schedule_type
		)
		SELECT
		  (NOW() + INTERVAL '1 day' + INTERVAL '7 hours')::timestamptz,
		  l.id, t.id, d.id, ct.id, FALSE, TRUE, 'ASG-100', 'GROUP'
		FROM locations l
		JOIN trainers t ON t.trainer_code = 1001
		JOIN disciplines d ON d.discipline_code = 'YOGA'
		JOIN class_types ct ON ct.name = 'Sunrise Yoga'
		WHERE l.location_code = 'LOC001'
		ON CONFLICT (trainer_id, slot_datetime) DO NOTHING;

		INSERT INTO slots (
		  slot_datetime, location_id, trainer_id, discipline_id,
		  class_type_id, is_online, is_available, slot_assignment_code, schedule_type
		)
		SELECT
		  (NOW() + INTERVAL '2 days' + INTERVAL '18 hours')::timestamptz,
		  l.id, t.id, d.id, ct.id, TRUE, TRUE, 'ASG-200', 'GROUP'
		FROM locations l
		JOIN trainers t ON t.trainer_code = 1002
		JOIN disciplines d ON d.discipline_code = 'CROSSFIT'
		JOIN class_types ct ON ct.name = 'CrossFit Starter'
		WHERE l.location_code = 'LOC002'
		ON CONFLICT (trainer_id, slot_datetime) DO NOTHING;

		-- =============================================================================
		-- FIREBASE-LINKED USER (email is unique)
		-- =============================================================================
		INSERT INTO users (email, password_hash, is_active, created_at)
		VALUES ('davidsnbr@gmail.com', 'firebase_managed_account', TRUE, CURRENT_TIMESTAMP)
		ON CONFLICT (email) DO NOTHING;

		-- =============================================================================
		-- MEMBER PROFILE FOR FIREBASE USER (user_id is unique)
		-- =============================================================================
		INSERT INTO member_profiles (
		  user_id, first_name, paternal_surname, maternal_surname,
		  mobile_phone, landline_phone, birth_date, address, avatar_url, fitness_goals
		)
		SELECT
		  u.id, 'David', 'Snbr', 'Dev',
		  '+569' || substring(md5(random()::text), 1, 8),
		  NULL, DATE '1994-08-12', 'Santiago, Chile', NULL, 'Improve resistance and mobility'
		FROM users u
		WHERE lower(u.email) = lower('davidsnbr@gmail.com')
		ON CONFLICT (user_id) DO NOTHING;
		"""
	)


def downgrade() -> None:
	pass
