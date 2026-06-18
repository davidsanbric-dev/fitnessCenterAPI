from __future__ import annotations

import argparse
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.tenancy import set_session_company
from app.models import ClassType, Slot, TargetCompany, Trainer

_DEFAULT_SLOTS = 50
# ASG-100 and ASG-200 are reserved by seed.py; start well clear of them.
_CODE_START = 300


def _generate_for_company(db, num_slots: int) -> int:
    """Generate slots for the company currently bound to *db*. Returns count created."""
    trainers = db.scalars(select(Trainer).where(Trainer.is_active.is_(True))).all()
    class_types = db.scalars(select(ClassType)).all()

    if not trainers:
        return 0

    # Existing codes for this company (session is already scoped).
    existing_codes: set[str] = set(
        db.scalars(
            select(Slot.slot_assignment_code).where(Slot.slot_assignment_code.isnot(None))
        ).all()
    )
    # Track (trainer_id, slot_datetime) pairs added in this batch so we never
    # produce an intra-batch duplicate before they're flushed to the DB.
    booked_pairs: set[tuple[int, datetime]] = set()

    start = datetime.utcnow().replace(hour=6, minute=0, second=0, microsecond=0) + timedelta(days=1)
    counter = _CODE_START
    created = 0
    attempts = 0

    while created < num_slots and attempts < num_slots * 10:
        attempts += 1

        slot_dt = start + timedelta(
            days=random.randint(0, 13),
            hours=random.randint(0, 16),
            minutes=random.choice([0, 30]),
        )
        trainer = random.choice(trainers)

        pair = (trainer.id, slot_dt)
        if pair in booked_pairs:
            continue

        # Check the persisted rows for the same unique constraint.
        if db.scalar(
            select(Slot).where(
                Slot.trainer_id == trainer.id,
                Slot.slot_datetime == slot_dt,
            )
        ):
            continue

        discipline = random.choice(trainer.disciplines) if trainer.disciplines else None
        class_type = random.choice(class_types) if class_types else None

        code = f"ASG-{counter}"
        while code in existing_codes:
            counter += 1
            code = f"ASG-{counter}"
        existing_codes.add(code)
        counter += 1

        db.add(
            Slot(
                slot_datetime=slot_dt,
                trainer_id=trainer.id,
                discipline_id=discipline.id if discipline else None,
                class_type_id=class_type.id if class_type else None,
                is_available=True,
                slot_assignment_code=code,
                schedule_type="GROUP",
            )
        )
        booked_pairs.add(pair)
        created += 1

    db.commit()
    return created


def main(num_slots: int = _DEFAULT_SLOTS) -> None:
    db = SessionLocal()
    try:
        # Collect company info before entering the scoped loop so that attribute
        # access on expired ORM objects after each commit is never needed.
        companies = [
            (row.id, row.slug)
            for row in db.scalars(
                select(TargetCompany).where(TargetCompany.is_active.is_(True))
            ).all()
        ]

        if not companies:
            print("No active companies found — run migrations and seed first.")
            return

        for company_id, slug in companies:
            set_session_company(db, company_id)
            count = _generate_for_company(db, num_slots)
            print(f"[{slug}] {count}/{num_slots} slots created.")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate sample slots for all active companies."
    )
    parser.add_argument(
        "--slots",
        type=int,
        default=_DEFAULT_SLOTS,
        help=f"Slots to generate per company (default: {_DEFAULT_SLOTS})",
    )
    main(num_slots=parser.parse_args().slots)
