from __future__ import annotations

import uuid

import sqlalchemy as sa

from app.core.config import settings

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
	SELECT :cid, (NOW() + INTERVAL '1 day' + INTERVAL '7 hours')::timestamptz,
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
	SELECT :cid, (NOW() + INTERVAL '2 days' + INTERVAL '18 hours')::timestamptz,
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
	for role_name in ("admin", "manager", "member"):
		bind.execute(
			sa.text(
				"INSERT INTO roles (uid, name) VALUES (:uid, :name) "
				"ON CONFLICT (name) DO NOTHING"
			),
			{"uid": str(uuid.uuid4()), "name": role_name},
		)


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
			first_name = (local_part[:1].upper() + local_part[1:]) if local_part else "Demo"

			bind.execute(
				sa.text(
					"INSERT INTO users (email, is_active, created_at, role_id, company_id) "
					"SELECT :email, TRUE, CURRENT_TIMESTAMP, r.id, :cid FROM roles r WHERE r.name = :role "
					"ON CONFLICT (email) DO NOTHING"
				),
				{"email": email, "role": role_name, "cid": company_id},
			)

			bind.execute(
				sa.text(
					"INSERT INTO member_profiles ("
					"  user_id, company_id, first_name, paternal_surname, maternal_surname, "
					"  mobile_phone, landline_phone, birth_date, address, avatar_url, fitness_goals"
					") "
					"SELECT u.id, :cid, :first_name, 'Demo', 'User', "
					"  '+569' || substring(md5(random()::text), 1, 8), "
					"  NULL, NULL, NULL, NULL, NULL "
					"FROM users u WHERE lower(u.email) = :email "
					"ON CONFLICT (user_id) DO NOTHING"
				),
				{"first_name": first_name, "email": email, "cid": company_id},
			)
