from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
	JSON,
	Boolean,
	Column,
	Date,
	DateTime,
	ForeignKey,
	Integer,
	Numeric,
	String,
	Table,
	Text,
	UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


# Adapted associations: clinic Professional/Specialty and Prevision relations -> gym Trainer/Discipline and MembershipPlan relations.
trainer_disciplines = Base.metadata.tables.get("trainer_disciplines")
if trainer_disciplines is None:
	trainer_disciplines = Table(
		"trainer_disciplines",
		Base.metadata,
		Column("trainer_id", ForeignKey("trainers.id"), primary_key=True),
		Column("discipline_id", ForeignKey("disciplines.id"), primary_key=True),
	)


trainer_membership_plans = Base.metadata.tables.get("trainer_membership_plans")
if trainer_membership_plans is None:
	trainer_membership_plans = Table(
		"trainer_membership_plans",
		Base.metadata,
		Column("trainer_id", ForeignKey("trainers.id"), primary_key=True),
		Column("membership_plan_id", ForeignKey("membership_plans.id"), primary_key=True),
	)


membership_plan_categories = Base.metadata.tables.get("membership_plan_categories")
if membership_plan_categories is None:
	membership_plan_categories = Table(
		"membership_plan_categories",
		Base.metadata,
		Column("membership_plan_id", ForeignKey("membership_plans.id"), primary_key=True),
		Column("class_category_id", ForeignKey("class_categories.id"), primary_key=True),
	)


class TimestampMixin:
	created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Role(Base):
	__tablename__ = "roles"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	uid: Mapped[str] = mapped_column(String(36), unique=True, index=True)
	name: Mapped[str] = mapped_column(String(50), unique=True)

	users: Mapped[list[User]] = relationship(back_populates="role")


# Adapted from clinic Patient account context -> gym authenticated User.
class User(TimestampMixin, Base):
	__tablename__ = "users"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
	is_active: Mapped[bool] = mapped_column(Boolean, default=True)
	role_id: Mapped[int | None] = mapped_column(ForeignKey("roles.id"), nullable=True)

	role: Mapped[Role | None] = relationship(back_populates="users")
	profile: Mapped[MemberProfile | None] = relationship(back_populates="user", uselist=False)
	bookings: Mapped[list[Booking]] = relationship(back_populates="user")
	notifications: Mapped[list[Notification]] = relationship(back_populates="user")
	device_tokens: Mapped[list[DeviceToken]] = relationship(back_populates="user")
	membership: Mapped[MemberMembership | None] = relationship(back_populates="user", uselist=False)


class MemberProfile(Base):
	# Adapted from clinic Patient demographic/contact fields -> gym Member profile fields.
	__tablename__ = "member_profiles"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
	first_name: Mapped[str] = mapped_column(String(120))
	paternal_surname: Mapped[str] = mapped_column(String(120))
	maternal_surname: Mapped[str] = mapped_column(String(120))
	mobile_phone: Mapped[str] = mapped_column(String(30))
	landline_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
	birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
	address: Mapped[str | None] = mapped_column(String(255), nullable=True)
	avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
	fitness_goals: Mapped[str | None] = mapped_column(Text, nullable=True)

	user: Mapped[User] = relationship(back_populates="profile")


class Location(Base):
	# Adapted from clinic Branch/Sucursal -> gym Location/Facility.
	__tablename__ = "locations"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	location_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
	name: Mapped[str] = mapped_column(String(120))

	trainers: Mapped[list[Trainer]] = relationship(back_populates="location")
	categories: Mapped[list[ClassCategory]] = relationship(back_populates="location")
	class_types: Mapped[list[ClassType]] = relationship(back_populates="location")
	slots: Mapped[list[Slot]] = relationship(back_populates="location")
	bookings: Mapped[list[Booking]] = relationship(back_populates="location")


class Discipline(Base):
	# Adapted from clinic Specialty/Especialidad -> gym Discipline.
	__tablename__ = "disciplines"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	discipline_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
	name: Mapped[str] = mapped_column(String(120), index=True)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	icon_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

	trainers: Mapped[list[Trainer]] = relationship(secondary=trainer_disciplines, back_populates="disciplines")
	slots: Mapped[list[Slot]] = relationship(back_populates="discipline")
	bookings: Mapped[list[Booking]] = relationship(back_populates="discipline")


class Trainer(Base):
	# Adapted from clinic Professional/Profesional -> gym Trainer.
	__tablename__ = "trainers"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	trainer_code: Mapped[int] = mapped_column(Integer, unique=True, index=True)
	full_name: Mapped[str] = mapped_column(String(150), index=True)
	bio: Mapped[str | None] = mapped_column(Text, nullable=True)
	photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
	certifications: Mapped[list[str]] = mapped_column(JSON, default=list)
	is_active: Mapped[bool] = mapped_column(Boolean, default=True)
	location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"), nullable=True)

	location: Mapped[Location | None] = relationship(back_populates="trainers")
	disciplines: Mapped[list[Discipline]] = relationship(secondary=trainer_disciplines, back_populates="trainers")
	membership_plans: Mapped[list[MembershipPlan]] = relationship(
		secondary=trainer_membership_plans,
		back_populates="trainers",
	)
	slots: Mapped[list[Slot]] = relationship(back_populates="trainer")
	bookings: Mapped[list[Booking]] = relationship(back_populates="trainer")


class ClassCategory(Base):
	# Adapted from clinic Capabilities query type "1" (Groups) -> gym ClassCategory.
	__tablename__ = "class_categories"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	name: Mapped[str] = mapped_column(String(120))
	icon_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
	location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"), nullable=True)

	location: Mapped[Location | None] = relationship(back_populates="categories")
	subcategories: Mapped[list[ClassSubcategory]] = relationship(back_populates="category")
	membership_plans: Mapped[list[MembershipPlan]] = relationship(
		secondary=membership_plan_categories,
		back_populates="allowed_categories",
	)
	bookings: Mapped[list[Booking]] = relationship(back_populates="category")


class ClassSubcategory(Base):
	# Adapted from clinic Capabilities query type "2" (Subgroups) -> gym ClassSubcategory.
	__tablename__ = "class_subcategories"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	category_id: Mapped[int] = mapped_column(ForeignKey("class_categories.id"), index=True)
	name: Mapped[str] = mapped_column(String(120))

	category: Mapped[ClassCategory] = relationship(back_populates="subcategories")
	class_types: Mapped[list[ClassType]] = relationship(back_populates="subcategory")


class ClassType(Base):
	# Adapted from clinic Service/Prestacion and Capabilities query type "3" -> gym ClassType.
	__tablename__ = "class_types"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	subcategory_id: Mapped[int] = mapped_column(ForeignKey("class_subcategories.id"), index=True)
	location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"), nullable=True)
	name: Mapped[str] = mapped_column(String(120))
	schedule_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
	preparation_info: Mapped[str | None] = mapped_column(Text, nullable=True)
	pdf_code: Mapped[str | None] = mapped_column(String(50), nullable=True)

	subcategory: Mapped[ClassSubcategory] = relationship(back_populates="class_types")
	location: Mapped[Location | None] = relationship(back_populates="class_types")
	slots: Mapped[list[Slot]] = relationship(back_populates="class_type")
	bookings: Mapped[list[Booking]] = relationship(back_populates="class_type")


class Slot(Base):
	# Adapted from clinic available appointments/service appointments DTOs -> gym Slot availability.
	__tablename__ = "slots"
	__table_args__ = (
		UniqueConstraint("trainer_id", "slot_datetime", name="uq_slot_trainer_datetime"),
	)

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	slot_datetime: Mapped[datetime] = mapped_column(DateTime, index=True)
	location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"), nullable=True)
	trainer_id: Mapped[int | None] = mapped_column(ForeignKey("trainers.id"), nullable=True)
	discipline_id: Mapped[int | None] = mapped_column(ForeignKey("disciplines.id"), nullable=True)
	class_type_id: Mapped[int | None] = mapped_column(ForeignKey("class_types.id"), nullable=True)
	is_online: Mapped[bool] = mapped_column(Boolean, default=False)
	is_available: Mapped[bool] = mapped_column(Boolean, default=True)
	slot_assignment_code: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
	schedule_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

	location: Mapped[Location | None] = relationship(back_populates="slots")
	trainer: Mapped[Trainer | None] = relationship(back_populates="slots")
	discipline: Mapped[Discipline | None] = relationship(back_populates="slots")
	class_type: Mapped[ClassType | None] = relationship(back_populates="slots")
	bookings: Mapped[list[Booking]] = relationship(back_populates="slot")


class Booking(Base):
	# Adapted from clinic Appointment/Cita aggregate -> gym Booking aggregate.
	__tablename__ = "bookings"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
	slot_id: Mapped[int | None] = mapped_column(ForeignKey("slots.id"), nullable=True)
	booking_status: Mapped[str] = mapped_column(String(50), default="CONFIRMED", index=True)
	booking_datetime: Mapped[datetime] = mapped_column(DateTime, index=True)
	scheduled_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
	updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
	session_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
	is_online: Mapped[bool] = mapped_column(Boolean, default=False)
	online_session_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
	preparation_info: Mapped[str | None] = mapped_column(Text, nullable=True)
	has_pdf: Mapped[bool] = mapped_column(Boolean, default=False)
	pdf_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
	notes: Mapped[str | None] = mapped_column(Text, nullable=True)
	is_overbooking: Mapped[bool] = mapped_column(Boolean, default=False)
	trainer_id: Mapped[int | None] = mapped_column(ForeignKey("trainers.id"), nullable=True)
	discipline_id: Mapped[int | None] = mapped_column(ForeignKey("disciplines.id"), nullable=True)
	class_type_id: Mapped[int | None] = mapped_column(ForeignKey("class_types.id"), nullable=True)
	category_id: Mapped[int | None] = mapped_column(ForeignKey("class_categories.id"), nullable=True)
	location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"), nullable=True)
	slot_assignment_code: Mapped[str | None] = mapped_column(String(50), nullable=True)

	user: Mapped[User] = relationship(back_populates="bookings")
	slot: Mapped[Slot | None] = relationship(back_populates="bookings")
	trainer: Mapped[Trainer | None] = relationship(back_populates="bookings")
	discipline: Mapped[Discipline | None] = relationship(back_populates="bookings")
	class_type: Mapped[ClassType | None] = relationship(back_populates="bookings")
	category: Mapped[ClassCategory | None] = relationship(back_populates="bookings")
	location: Mapped[Location | None] = relationship(back_populates="bookings")


class MembershipPlan(Base):
	# Adapted from clinic Prevision/HealthInsurance filter -> gym first-class MembershipPlan entity.
	__tablename__ = "membership_plans"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	name: Mapped[str] = mapped_column(String(120), unique=True)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
	duration_days: Mapped[int] = mapped_column(Integer, default=30)
	features: Mapped[list[str]] = mapped_column(JSON, default=list)
	max_bookings_per_month: Mapped[int] = mapped_column(Integer, default=0)
	includes_personal_training: Mapped[bool] = mapped_column(Boolean, default=False)

	member_memberships: Mapped[list[MemberMembership]] = relationship(back_populates="plan")
	allowed_categories: Mapped[list[ClassCategory]] = relationship(
		secondary=membership_plan_categories,
		back_populates="membership_plans",
	)
	trainers: Mapped[list[Trainer]] = relationship(
		secondary=trainer_membership_plans,
		back_populates="membership_plans",
	)


class MemberMembership(Base):
	# Gym extension mapped from clinic prevision linkage semantics -> member active membership record.
	__tablename__ = "member_memberships"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
	membership_plan_id: Mapped[int] = mapped_column(ForeignKey("membership_plans.id"))
	start_date: Mapped[date] = mapped_column(Date)
	end_date: Mapped[date] = mapped_column(Date)
	status: Mapped[str] = mapped_column(String(50), default="ACTIVE")
	bookings_used: Mapped[int] = mapped_column(Integer, default=0)

	user: Mapped[User] = relationship(back_populates="membership")
	plan: Mapped[MembershipPlan] = relationship(back_populates="member_memberships")


class Notification(TimestampMixin, Base):
	# Gym-specific extension with lifecycle events derived from adapted booking flow.
	__tablename__ = "notifications"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
	title: Mapped[str] = mapped_column(String(150))
	body: Mapped[str] = mapped_column(Text)
	type: Mapped[str] = mapped_column(String(50), index=True)
	is_read: Mapped[bool] = mapped_column(Boolean, default=False)
	data: Mapped[dict] = mapped_column(JSON, default=dict)

	user: Mapped[User] = relationship(back_populates="notifications")


class DeviceToken(Base):
	# Gym-specific extension for mobile push delivery tokens.
	__tablename__ = "device_tokens"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
	token: Mapped[str] = mapped_column(String(255), unique=True)
	platform: Mapped[str] = mapped_column(String(20))

	user: Mapped[User] = relationship(back_populates="device_tokens")
