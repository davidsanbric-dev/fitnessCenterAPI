from __future__ import annotations

import hashlib
import uuid

import sqlalchemy as sa

from app.core.config import settings


def _rut_check_digit(body: int) -> str:
	# Standard Chilean RUT verifier digit (modulo 11), so seeded RUTs are
	# well-formed and pass client-side validation/formatting.
	total = 0
	factor = 2
	for digit in reversed(str(body)):
		total += int(digit) * factor
		factor = 2 if factor == 7 else factor + 1
	remainder = 11 - (total % 11)
	if remainder == 11:
		return "0"
	if remainder == 10:
		return "K"
	return str(remainder)


def _deterministic_rut(email: str) -> str:
	# Deterministic 8-digit RUT body derived from the email so re-running the
	# seed/backfill always yields the same value for a given member (idempotent)
	# without a random() that would drift between runs.
	body = 10_000_000 + (int(hashlib.md5(email.encode()).hexdigest()[:8], 16) % 15_000_000)
	return f"{body}-{_rut_check_digit(body)}"

# Advisory-lock key serialising concurrent seeders (e.g. multiple workers running
# lifespan startup at once). Held for the duration of the calling transaction, it
# prevents the NOT EXISTS category inserts below from racing into duplicates.
_SEED_LOCK_KEY = 478_215_001


# Per-company catalog statements. Each is a single, idempotent statement scoped
# to :cid (the TargetCompany id) so the *same* dataset is provisioned in every
# company's isolated environment. ON CONFLICT targets use the company-scoped
# composite unique constraints defined on the models; the category/subcategory/
# class-type inserts (which have no business unique key) guard with NOT EXISTS.
# Idempotent on re-run, so adding a company to DEMO_USERS and restarting seeds
# only the new company without disturbing existing ones.
_COMPANY_CATALOG_SQL: list[str] = [
	# -------------------------------------------------------------------------
	# LOCATIONS (unique per company_id + location_code)
	# -------------------------------------------------------------------------
	"""
	INSERT INTO locations (company_id, location_code, name) VALUES
	  (:cid, 'LOC001', 'Downtown Gym'),
	  (:cid, 'LOC002', 'North Branch')
	ON CONFLICT (company_id, location_code) DO NOTHING
	""",
	# -------------------------------------------------------------------------
	# DISCIPLINES (unique per company_id + discipline_code)
	# -------------------------------------------------------------------------
	"""
	INSERT INTO disciplines (company_id, discipline_code, name, description, icon_url) VALUES
	  (:cid, 'YOGA', 'Yoga', 'Mobility and mindful movement', '/icons/yoga.svg'),
	  (:cid, 'CROSSFIT', 'CrossFit', 'High intensity functional training', '/icons/crossfit.svg'),
	  (:cid, 'PILATES', 'Pilates', 'Core strength and posture', '/icons/pilates.svg')
	ON CONFLICT (company_id, discipline_code) DO NOTHING
	""",
	# -------------------------------------------------------------------------
	# MEMBERSHIP PLANS (unique per company_id + name)
	# -------------------------------------------------------------------------
	"""
	INSERT INTO membership_plans (
	  company_id, name, description, price, duration_days, features,
	  max_bookings_per_month, includes_personal_training
	) VALUES
	  (:cid, 'Basic', 'Access to essential classes', 29.99, 30, '["Gym floor access", "2 group classes per week"]'::json, 8, FALSE),
	  (:cid, 'Premium', 'Unlimited classes and amenities', 59.99, 30, '["Unlimited classes", "Sauna access", "Nutrition webinar"]'::json, 30, TRUE),
	  (:cid, 'VIP', 'All access with premium coaching', 89.99, 30, '["Unlimited classes", "2 PT sessions", "Priority booking"]'::json, 50, TRUE)
	ON CONFLICT (company_id, name) DO NOTHING
	""",
	# -------------------------------------------------------------------------
	# CLASS CATEGORIES (no business unique key -> guard with NOT EXISTS per company)
	# -------------------------------------------------------------------------
	"""
	INSERT INTO class_categories (company_id, name, icon_url, location_id)
	SELECT :cid, 'Mind & Body', '/icons/mind-body.svg', l.id
	FROM locations l
	WHERE l.company_id = :cid AND l.location_code = 'LOC001'
	  AND NOT EXISTS (
	    SELECT 1 FROM class_categories cc WHERE cc.company_id = :cid AND cc.name = 'Mind & Body'
	  )
	""",
	"""
	INSERT INTO class_categories (company_id, name, icon_url, location_id)
	SELECT :cid, 'Performance', '/icons/performance.svg', l.id
	FROM locations l
	WHERE l.company_id = :cid AND l.location_code = 'LOC002'
	  AND NOT EXISTS (
	    SELECT 1 FROM class_categories cc WHERE cc.company_id = :cid AND cc.name = 'Performance'
	  )
	""",
	# -------------------------------------------------------------------------
	# CLASS SUBCATEGORIES
	# -------------------------------------------------------------------------
	"""
	INSERT INTO class_subcategories (company_id, name, category_id)
	SELECT :cid, 'Yoga Flow', cc.id
	FROM class_categories cc
	WHERE cc.company_id = :cid AND cc.name = 'Mind & Body'
	  AND NOT EXISTS (
	    SELECT 1 FROM class_subcategories sc WHERE sc.company_id = :cid AND sc.name = 'Yoga Flow'
	  )
	""",
	"""
	INSERT INTO class_subcategories (company_id, name, category_id)
	SELECT :cid, 'Strength', cc.id
	FROM class_categories cc
	WHERE cc.company_id = :cid AND cc.name = 'Performance'
	  AND NOT EXISTS (
	    SELECT 1 FROM class_subcategories sc WHERE sc.company_id = :cid AND sc.name = 'Strength'
	  )
	""",
	# -------------------------------------------------------------------------
	# CLASS TYPES
	# -------------------------------------------------------------------------
	"""
	INSERT INTO class_types (company_id, name, subcategory_id, location_id, schedule_type, preparation_info, pdf_code)
	SELECT :cid, 'Sunrise Yoga', sc.id, l.id, 'GROUP', 'Bring a yoga mat and water bottle.', 'YOGA-001'
	FROM class_subcategories sc
	JOIN locations l ON l.company_id = :cid AND l.location_code = 'LOC001'
	WHERE sc.company_id = :cid AND sc.name = 'Yoga Flow'
	  AND NOT EXISTS (
	    SELECT 1 FROM class_types ct WHERE ct.company_id = :cid AND ct.name = 'Sunrise Yoga'
	  )
	""",
	"""
	INSERT INTO class_types (company_id, name, subcategory_id, location_id, schedule_type, preparation_info, pdf_code)
	SELECT :cid, 'CrossFit Starter', sc.id, l.id, 'GROUP', 'Arrive 10 minutes early for warm-up.', 'CF-010'
	FROM class_subcategories sc
	JOIN locations l ON l.company_id = :cid AND l.location_code = 'LOC002'
	WHERE sc.company_id = :cid AND sc.name = 'Strength'
	  AND NOT EXISTS (
	    SELECT 1 FROM class_types ct WHERE ct.company_id = :cid AND ct.name = 'CrossFit Starter'
	  )
	""",
	# -------------------------------------------------------------------------
	# TRAINERS (unique per company_id + trainer_code)
	# -------------------------------------------------------------------------
	"""
	INSERT INTO trainers (company_id, trainer_code, full_name, bio, photo_url, certifications, is_active, location_id)
	SELECT :cid, 1001, 'Sofia Ramirez', 'Yoga instructor focused on flexibility and balance.',
	       '/images/trainers/sofia.jpg', '["RYT-500", "Mobility Coach"]'::json, TRUE, l.id
	FROM locations l
	WHERE l.company_id = :cid AND l.location_code = 'LOC001'
	ON CONFLICT (company_id, trainer_code) DO NOTHING
	""",
	"""
	INSERT INTO trainers (company_id, trainer_code, full_name, bio, photo_url, certifications, is_active, location_id)
	SELECT :cid, 1002, 'Diego Herrera', 'Cross-training coach with performance background.',
	       '/images/trainers/diego.jpg', '["CrossFit Level 2", "TRX Coach"]'::json, TRUE, l.id
	FROM locations l
	WHERE l.company_id = :cid AND l.location_code = 'LOC002'
	ON CONFLICT (company_id, trainer_code) DO NOTHING
	""",
	# -------------------------------------------------------------------------
	# TRAINER-DISCIPLINE ASSOCIATIONS (both sides scoped to :cid)
	# -------------------------------------------------------------------------
	"""
	INSERT INTO trainer_disciplines (trainer_id, discipline_id)
	SELECT t.id, d.id
	FROM trainers t
	JOIN disciplines d ON d.company_id = :cid AND (
	       (t.trainer_code = 1001 AND d.discipline_code IN ('YOGA', 'PILATES'))
	    OR (t.trainer_code = 1002 AND d.discipline_code = 'CROSSFIT')
	)
	WHERE t.company_id = :cid
	ON CONFLICT DO NOTHING
	""",
	# -------------------------------------------------------------------------
	# TRAINER-MEMBERSHIP PLAN ASSOCIATIONS (both sides scoped to :cid)
	# -------------------------------------------------------------------------
	"""
	INSERT INTO trainer_membership_plans (trainer_id, membership_plan_id)
	SELECT t.id, mp.id
	FROM trainers t
	JOIN membership_plans mp ON mp.company_id = :cid
	WHERE t.company_id = :cid
	  AND (t.trainer_code = 1001 OR (t.trainer_code = 1002 AND mp.name IN ('Premium', 'VIP')))
	ON CONFLICT DO NOTHING
	""",
	# -------------------------------------------------------------------------
	# MEMBERSHIP PLAN - CATEGORY ASSOCIATIONS (both sides scoped to :cid)
	# -------------------------------------------------------------------------
	"""
	INSERT INTO membership_plan_categories (membership_plan_id, class_category_id)
	SELECT mp.id, cc.id
	FROM membership_plans mp
	JOIN class_categories cc ON cc.company_id = :cid
	WHERE mp.company_id = :cid AND (
	       (cc.name = 'Mind & Body' AND mp.name IN ('Basic', 'Premium', 'VIP'))
	    OR (cc.name = 'Performance' AND mp.name IN ('Premium', 'VIP'))
	)
	ON CONFLICT DO NOTHING
	""",
	# -------------------------------------------------------------------------
	# SLOTS (unique constraint: uq_slot_trainer_datetime on trainer_id + slot_datetime)
	# -------------------------------------------------------------------------
	"""
	INSERT INTO slots (
	  company_id, slot_datetime, location_id, trainer_id, discipline_id,
	  class_type_id, is_available, slot_assignment_code, schedule_type
	)
	SELECT :cid, date_trunc('minute', (NOW() + INTERVAL '1 day' + INTERVAL '7 hours')::timestamptz),
	       l.id, t.id, d.id, ct.id, TRUE, 'ASG-100', 'GROUP'
	FROM locations l
	JOIN trainers t ON t.company_id = :cid AND t.trainer_code = 1001
	JOIN disciplines d ON d.company_id = :cid AND d.discipline_code = 'YOGA'
	JOIN class_types ct ON ct.company_id = :cid AND ct.name = 'Sunrise Yoga'
	WHERE l.company_id = :cid AND l.location_code = 'LOC001'
	  AND NOT EXISTS (
	    SELECT 1 FROM slots s WHERE s.company_id = :cid AND s.slot_assignment_code = 'ASG-100'
	  )
	ON CONFLICT (trainer_id, slot_datetime) DO NOTHING
	""",
	"""
	INSERT INTO slots (
	  company_id, slot_datetime, location_id, trainer_id, discipline_id,
	  class_type_id, is_available, slot_assignment_code, schedule_type
	)
	SELECT :cid, date_trunc('minute', (NOW() + INTERVAL '2 days' + INTERVAL '18 hours')::timestamptz),
	       l.id, t.id, d.id, ct.id, TRUE, 'ASG-200', 'GROUP'
	FROM locations l
	JOIN trainers t ON t.company_id = :cid AND t.trainer_code = 1002
	JOIN disciplines d ON d.company_id = :cid AND d.discipline_code = 'CROSSFIT'
	JOIN class_types ct ON ct.company_id = :cid AND ct.name = 'CrossFit Starter'
	WHERE l.company_id = :cid AND l.location_code = 'LOC002'
	  AND NOT EXISTS (
	    SELECT 1 FROM slots s WHERE s.company_id = :cid AND s.slot_assignment_code = 'ASG-200'
	  )
	ON CONFLICT (trainer_id, slot_datetime) DO NOTHING
	""",
	# -------------------------------------------------------------------------
	# BLOG ENTRIES (no business unique key -> guard with NOT EXISTS per company)
	# -------------------------------------------------------------------------
	"""
	INSERT INTO blogs (company_id, title, hero_image_path, text, created_at, updated_at)
	SELECT :cid,
	       'CrossFit: Unlock Your Full Athletic Potential',
	       'crossfit_blog_hero_image.webp',
	       'CrossFit combines strength training, cardiovascular conditioning, and functional movements into high-intensity workouts designed to challenge both body and mind. Whether you''re a beginner looking to improve your fitness or an experienced athlete seeking new challenges, every session is scalable to your current level.'
	       || chr(10) || chr(10) ||
	       'Beyond the physical benefits, CrossFit fosters a supportive community that motivates you to push further, celebrate progress, and develop lasting healthy habits. If you''re ready to build strength, endurance, and confidence simultaneously, CrossFit offers a proven path forward.',
	       CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
	WHERE NOT EXISTS (
	  SELECT 1 FROM blogs b WHERE b.company_id = :cid AND b.title = 'CrossFit: Unlock Your Full Athletic Potential'
	)
	""",
	"""
	INSERT INTO blogs (company_id, title, hero_image_path, text, created_at, updated_at)
	SELECT :cid,
	       'Yoga: Find Balance, Strength, and Inner Calm',
	       'yoga_blog_hero_image.webp',
	       'Yoga is more than stretching—it''s a holistic practice that connects movement, breathing, and mindfulness. Through carefully guided postures and controlled breathing techniques, yoga helps improve flexibility, posture, mobility, and mental clarity.'
	       || chr(10) || chr(10) ||
	       'In today''s fast-paced world, yoga provides a valuable opportunity to slow down, reduce stress, and reconnect with yourself. Whether your goal is relaxation, recovery, or enhanced athletic performance, regular practice can bring lasting benefits to both body and mind.',
	       CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
	WHERE NOT EXISTS (
	  SELECT 1 FROM blogs b WHERE b.company_id = :cid AND b.title = 'Yoga: Find Balance, Strength, and Inner Calm'
	)
	""",
	"""
	INSERT INTO blogs (company_id, title, hero_image_path, text, created_at, updated_at)
	SELECT :cid,
	       'Pilates: Build Strength from the Core Out',
	       'pilates_blog_hero_image.webp',
	       'Pilates focuses on controlled movements that strengthen the body''s core muscles while improving posture, balance, and overall body awareness. Every exercise emphasizes precision and proper alignment, helping create a strong foundation for daily activities and athletic performance alike.'
	       || chr(10) || chr(10) ||
	       'Suitable for all fitness levels, Pilates is particularly effective for developing functional strength, reducing muscular imbalances, and enhancing flexibility. By training smarter rather than harder, Pilates helps you move with greater confidence, control, and efficiency in every aspect of life.',
	       CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
	WHERE NOT EXISTS (
	  SELECT 1 FROM blogs b WHERE b.company_id = :cid AND b.title = 'Pilates: Build Strength from the Core Out'
	)
	""",
]


def seed_reference_data(bind) -> None:
	"""Provision the per-company reference dataset. Fully idempotent.

	Safe to run on every startup and after editing DEMO_USERS: existing companies
	are left untouched (ON CONFLICT / NOT EXISTS) while any newly added company
	gets the same isolated dataset -- no DB recreation required.

	``bind`` is a SQLAlchemy Connection (Alembic's ``op.get_bind()`` or a
	connection from ``engine.begin()``); both run inside a transaction, which the
	advisory lock below relies on.
	"""
	# Serialise concurrent seeders for the rest of this transaction.
	bind.execute(sa.text("SELECT pg_advisory_xact_lock(:k)"), {"k": _SEED_LOCK_KEY})

	# Defensive: guarantee the trainer<->user link column exists before the staff
	# trainer seed references it. Idempotent, and covers the case where the seed
	# migration runs standalone (``alembic upgrade``) before ``create_all`` has
	# provisioned the column on a fresh database.
	bind.execute(
		sa.text("ALTER TABLE trainers ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)")
	)

	# Likewise guarantee the member RUT column exists before the demo-member seed
	# writes it. Idempotent; covers existing databases provisioned before the RUT
	# field was added to MemberProfile (create_all never alters existing tables).
	bind.execute(
		sa.text("ALTER TABLE member_profiles ADD COLUMN IF NOT EXISTS rut VARCHAR(20)")
	)

	# Defensive: ``slots.is_online`` is a NOT NULL column present in some databases
	# (schema drift -- it is absent from the Slot model) but with no server default,
	# while the catalog/staff slot inserts below never set it. Without a default the
	# whole seed transaction aborts at the first real slot insert (e.g. the staff
	# trainer's), rolling back every preceding insert -- including the RUT and
	# membership seeding. Backfilling a default makes those inserts well-formed.
	# Idempotent and a no-op on databases where the column does not exist.
	bind.execute(
		sa.text(
			"DO $$ BEGIN "
			"IF EXISTS (SELECT 1 FROM information_schema.columns "
			"WHERE table_name = 'slots' AND column_name = 'is_online') THEN "
			"ALTER TABLE slots ALTER COLUMN is_online SET DEFAULT FALSE; "
			"UPDATE slots SET is_online = FALSE WHERE is_online IS NULL; "
			"END IF; END $$"
		)
	)

	company_id_by_slug = _seed_companies(bind)
	_seed_roles(bind)

	for company_id in company_id_by_slug.values():
		for statement in _COMPANY_CATALOG_SQL:
			bind.execute(sa.text(statement), {"cid": company_id})

	_seed_demo_users(bind, company_id_by_slug)


def _seed_companies(bind) -> dict[str, int]:
	# Provision one TargetCompany per DEMO_USERS group (slug = the JSON key).
	for slug in settings.demo_companies:
		bind.execute(
			sa.text(
				"INSERT INTO target_companies (slug, name, is_active, created_at) "
				"VALUES (:slug, :name, TRUE, CURRENT_TIMESTAMP) "
				"ON CONFLICT (slug) DO NOTHING"
			),
			{"slug": slug, "name": slug.replace("_", " ").title()},
		)

	rows = bind.execute(sa.text("SELECT id, slug FROM target_companies")).mappings().all()
	known = set(settings.demo_companies.keys())
	return {row["slug"]: row["id"] for row in rows if row["slug"] in known}


def _seed_roles(bind) -> None:
	# Roles are the global authorization catalogue (not company-scoped). The
	# catalogue must cover every role the API can resolve (see
	# AuthService._PERMISSIONS_BY_ROLE), even those no demo user currently uses.
	for role_name in ("admin", "manager", "member", "trainer"):
		bind.execute(
			sa.text(
				"INSERT INTO roles (uid, name) VALUES (:uid, :name) "
				"ON CONFLICT (name) DO NOTHING"
			),
			{"uid": str(uuid.uuid4()), "name": role_name},
		)


# Hardcoded personal-data for known demo member accounts, keyed by lower-case
# email. Mirrors how _STAFF_TRAINER_SQL supplies specific values for Jordan Pike
# instead of leaving fields as placeholders or random-generated.
_DEMO_MEMBER_PROFILES: dict[str, dict[str, object]] = {
	"member@otrofyjobapply.com": {
		"first_name": "Alex",
		"paternal_surname": "Torres",
		"maternal_surname": "Vega",
		"rut": "18765432-7",
		"mobile_phone": "+56912340001",
		"landline_phone": None,
		"birth_date": "1993-07-22",
		"address": "Av. Providencia 456, Santiago",
		"avatar_url": "/images/members/demo_member.jpg",
		"fitness_goals": "Build endurance and increase overall strength through consistent group classes.",
	},
}


def _seed_demo_users(bind, company_id_by_slug: dict[str, int]) -> None:
	# Firebase-linked demo users + profiles, scoped to their company. Email is
	# globally unique and is the key that resolves a user back to its company at
	# login (see app.core.dependencies.get_current_user).
	for slug, members in settings.demo_companies.items():
		company_id = company_id_by_slug.get(slug)
		if company_id is None:
			continue
		for role_name, email, _password in members:
			local_part = email.split("@", 1)[0]
			default_first = (local_part[:1].upper() + local_part[1:]) if local_part else "Demo"

			bind.execute(
				sa.text(
					"INSERT INTO users (email, is_active, created_at, role_id, company_id) "
					"SELECT :email, TRUE, CURRENT_TIMESTAMP, r.id, :cid FROM roles r WHERE r.name = :role "
					"ON CONFLICT (email) DO NOTHING"
				),
				{"email": email, "role": role_name, "cid": company_id},
			)

			# The trainer demo user owns a Trainer record (its personal data) rather
			# than a member profile; everyone else (admin/member) gets a member
			# profile as before.
			if role_name == "trainer":
				_seed_trainer_staff(bind, company_id, email)
				continue

			profile = _DEMO_MEMBER_PROFILES.get(email.lower(), {})
			# Deterministic phone fallback for emails not in _DEMO_MEMBER_PROFILES so
			# the NOT NULL mobile_phone column is always satisfied without random().
			fallback_phone = "+569" + hashlib.md5(email.encode()).hexdigest()[:8]
			# Hardcoded RUT when known, otherwise a deterministic well-formed value.
			member_rut = profile.get("rut") or _deterministic_rut(email)
			bind.execute(
				sa.text(
					"INSERT INTO member_profiles ("
					"  user_id, company_id, first_name, paternal_surname, maternal_surname, "
					"  rut, mobile_phone, landline_phone, birth_date, address, avatar_url, fitness_goals"
					") "
					"SELECT u.id, :cid, :first_name, :paternal_surname, :maternal_surname, "
					"  :rut, :mobile_phone, :landline_phone, CAST(:birth_date AS DATE), :address, :avatar_url, :fitness_goals "
					"FROM users u WHERE lower(u.email) = :email "
					"ON CONFLICT (user_id) DO NOTHING"
				),
				{
					"first_name": profile.get("first_name", default_first),
					"paternal_surname": profile.get("paternal_surname", "Demo"),
					"maternal_surname": profile.get("maternal_surname", "User"),
					"rut": member_rut,
					"mobile_phone": profile.get("mobile_phone") or fallback_phone,
					"landline_phone": profile.get("landline_phone"),
					"birth_date": profile.get("birth_date"),
					"address": profile.get("address"),
					"avatar_url": profile.get("avatar_url"),
					"fitness_goals": profile.get("fitness_goals"),
					"email": email,
					"cid": company_id,
				},
			)

			# Backfill the RUT on pre-existing profiles whose row predates the column
			# (ON CONFLICT above leaves existing rows untouched). Only fills NULLs, so
			# it never overwrites a value a member may have edited.
			bind.execute(
				sa.text(
					"UPDATE member_profiles SET rut = :rut "
					"FROM users u "
					"WHERE member_profiles.user_id = u.id AND lower(u.email) = :email "
					"  AND member_profiles.rut IS NULL"
				),
				{"rut": member_rut, "email": email},
			)

			# Members get a Basic plan subscription so the mobile app can surface it
			# and the booking allowance can be enforced. Idempotent: skipped when the
			# member already has a membership (user_id is unique on the table).
			if role_name == "member":
				bind.execute(
					sa.text(
						"INSERT INTO member_memberships ("
						"  company_id, user_id, membership_plan_id, start_date, end_date, status, bookings_used"
						") "
						"SELECT :cid, u.id, mp.id, CURRENT_DATE, CURRENT_DATE + mp.duration_days, 'ACTIVE', 0 "
						"FROM users u "
						"JOIN membership_plans mp ON mp.company_id = :cid AND mp.name = 'Basic' "
						"WHERE lower(u.email) = :email "
						"  AND NOT EXISTS ("
						"    SELECT 1 FROM member_memberships m WHERE m.user_id = u.id"
						"  )"
					),
					{"email": email, "cid": company_id},
				)


# Reserved trainer_code for the single staff trainer seeded per company and linked
# to the "trainer" demo user. Kept clear of the catalog directory trainers
# (1001/1002) so the two never collide on the (company_id, trainer_code) key.
_STAFF_TRAINER_CODE = 2001

# Per-company staff-trainer provisioning. Each statement is idempotent and scoped
# to :cid (company) and :email (the trainer demo user resolved to its User row).
_STAFF_TRAINER_SQL: list[str] = [
	# -------------------------------------------------------------------------
	# TRAINER RECORD (hardcoded non-credential fields; linked to the trainer user).
	# unique per (company_id, trainer_code). Anchored at LOC001.
	# -------------------------------------------------------------------------
	"""
	INSERT INTO trainers (
	  company_id, trainer_code, full_name, bio, photo_url, certifications,
	  is_active, location_id, user_id
	)
	SELECT :cid, 2001, 'Jordan Pike',
	       'Personal trainer managing one-on-one sessions and availability.',
	       '/images/trainers/staff.jpg', '["NASM-CPT", "Strength & Conditioning"]'::json,
	       TRUE,
	       (SELECT id FROM locations WHERE company_id = :cid AND location_code = 'LOC001'),
	       u.id
	FROM users u
	WHERE lower(u.email) = :email
	ON CONFLICT (company_id, trainer_code) DO NOTHING
	""",
	# -------------------------------------------------------------------------
	# TRAINER-DISCIPLINE ASSOCIATION (gives the staff trainer a discipline so its
	# slots are meaningful). Scoped to :cid on both sides.
	# -------------------------------------------------------------------------
	"""
	INSERT INTO trainer_disciplines (trainer_id, discipline_id)
	SELECT t.id, d.id
	FROM trainers t
	JOIN disciplines d ON d.company_id = :cid AND d.discipline_code = 'YOGA'
	WHERE t.company_id = :cid AND t.trainer_code = 2001
	ON CONFLICT DO NOTHING
	""",
	# -------------------------------------------------------------------------
	# 6 AVAILABLE SLOTS, one per day starting two days after creation (09:00).
	# Idempotent via the slot_assignment_code guard, so re-running on a later day
	# does not append new slots at shifted times.
	# -------------------------------------------------------------------------
	"""
	INSERT INTO slots (
	  company_id, slot_datetime, location_id, trainer_id, discipline_id,
	  is_available, slot_assignment_code, schedule_type
	)
	SELECT :cid,
	       date_trunc('minute', (NOW() + INTERVAL '2 days' + (gs.n || ' days')::interval + INTERVAL '9 hours')::timestamptz),
	       t.location_id, t.id, d.id, TRUE, 'TRN2001-' || gs.n, 'PERSONAL'
	FROM generate_series(0, 5) AS gs(n)
	CROSS JOIN trainers t
	CROSS JOIN disciplines d
	WHERE t.company_id = :cid AND t.trainer_code = 2001
	  AND d.company_id = :cid AND d.discipline_code = 'YOGA'
	  AND NOT EXISTS (
	    SELECT 1 FROM slots s
	    WHERE s.company_id = :cid AND s.slot_assignment_code = 'TRN2001-' || gs.n
	  )
	ON CONFLICT (trainer_id, slot_datetime) DO NOTHING
	""",
]


def _seed_trainer_staff(bind, company_id: int, email: str) -> None:
	"""Provision the single staff trainer for a company and its 6 starter slots.

	Idempotent: the trainer record keys on (company_id, trainer_code) and the
	slots guard on their assignment code, so repeated runs are no-ops.
	"""
	for statement in _STAFF_TRAINER_SQL:
		bind.execute(sa.text(statement), {"cid": company_id, "email": email})
