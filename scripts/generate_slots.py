from pathlib import Path
import sys
from datetime import datetime, timedelta
import random

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.orm import Session
from app.core.db import SessionLocal
from app.models import Location, Discipline, Trainer, ClassCategory, ClassSubcategory, ClassType, Slot


def ensure_sample_data(db: Session):
    """Ensure we have sample data for related entities before generating slots."""

    # Check if locations exist
    if not db.query(Location).first():
        locations = [
            Location(location_code="LOC001", name="Downtown Gym"),
            Location(location_code="LOC002", name="North Branch"),
        ]
        db.add_all(locations)
        print("Created sample locations")

    # Check if disciplines exist
    if not db.query(Discipline).first():
        disciplines = [
            Discipline(discipline_code="FIT001", name="Fitness", description="General fitness training"),
            Discipline(discipline_code="YOG001", name="Yoga", description="Yoga classes"),
            Discipline(discipline_code="PIL001", name="Pilates", description="Pilates training"),
        ]
        db.add_all(disciplines)
        print("Created sample disciplines")

    # Check if trainers exist
    if not db.query(Trainer).first():
        locations = db.query(Location).all()
        disciplines = db.query(Discipline).all()
        trainers = []
        for i, loc in enumerate(locations):
            trainer = Trainer(
                trainer_code=1001 + i,
                full_name=f"Trainer {i+1}",
                bio=f"Experienced trainer at {loc.name}",
                is_active=True,
                location_id=loc.id,
            )
            trainer.disciplines = random.sample(disciplines, k=random.randint(1, 2))
            trainers.append(trainer)
        db.add_all(trainers)
        print("Created sample trainers")

    # Check if class categories exist
    if not db.query(ClassCategory).first():
        locations = db.query(Location).all()
        categories = []
        for i, loc in enumerate(locations):
            category = ClassCategory(
                name=f"Category {i+1}",
                location_id=loc.id,
            )
            categories.append(category)
        db.add_all(categories)
        db.commit()  # Commit to get IDs

        # Create subcategories
        subcategories = []
        for cat in categories:
            subcat = ClassSubcategory(
                category_id=cat.id,
                name=f"Subcategory for {cat.name}",
            )
            subcategories.append(subcat)
        db.add_all(subcategories)
        db.commit()

        # Create class types
        class_types = []
        for subcat in subcategories:
            ct = ClassType(
                subcategory_id=subcat.id,
                location_id=subcat.category.location_id,
                name=f"Class Type for {subcat.name}",
                schedule_type="GROUP",
            )
            class_types.append(ct)
        db.add_all(class_types)
        print("Created sample class categories, subcategories, and types")

    db.commit()


def generate_slots(db: Session, num_slots: int = 50):
    """Generate sample slot records with proper integrity."""

    # Get existing data
    locations = db.query(Location).all()
    trainers = db.query(Trainer).all()
    disciplines = db.query(Discipline).all()
    class_types = db.query(ClassType).all()

    if not locations or not trainers:
        print("No locations or trainers found. Run ensure_sample_data first.")
        return

    # Find the latest slot datetime in the database
    latest_slot = db.query(Slot.slot_datetime).order_by(Slot.slot_datetime.desc()).first()
    if latest_slot:
        start_date = latest_slot[0].replace(hour=6, minute=0, second=0, microsecond=0)
    else:
        # If no slots exist, start from now
        start_date = datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)

    # Generate slots for the next 7 days from the latest record
    # end_date = start_date + timedelta(days=7)  # Not needed since we generate randomly within 7 days

    slots_created = 0
    attempts = 0
    max_attempts = num_slots * 10  # Prevent infinite loops
    slot_code_counter = 100  # Start from 100 like in the example

    while slots_created < num_slots and attempts < max_attempts:
        attempts += 1

        # Random slot time between 6 AM and 10 PM for the next 7 days
        slot_datetime = start_date + timedelta(
            days=random.randint(0, 6),
            hours=random.randint(0, 16),  # 6AM to 10PM
            minutes=random.choice([0, 30])  # Half-hour slots
        )

        trainer = random.choice(trainers)
        location = trainer.location or random.choice(locations)
        discipline = random.choice(trainer.disciplines) if trainer.disciplines else random.choice(disciplines)
        class_type = random.choice(class_types) if class_types else None

        # Check for unique constraint violation (same trainer, same datetime)
        existing = db.query(Slot).filter(
            Slot.trainer_id == trainer.id,
            Slot.slot_datetime == slot_datetime
        ).first()

        if existing:
            continue  # Skip this slot, try another

        # Create the slot
        slot = Slot(
            slot_datetime=slot_datetime,
            location_id=location.id,
            trainer_id=trainer.id,
            discipline_id=discipline.id,
            class_type_id=class_type.id if class_type else None,
            is_online=random.choice([True, False]),
            is_available=True,
            slot_assignment_code=f"ASG-{slot_code_counter}",
            schedule_type="REGULAR",
        )

        db.add(slot)
        db.commit()  # Commit each slot individually to avoid batch insert conflicts
        slots_created += 1
        slot_code_counter += 1  # Increment for next slot


def main():
    db = SessionLocal()
    try:
        ensure_sample_data(db)
        generate_slots(db, num_slots=50)
        print("Slot generation completed successfully!")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()