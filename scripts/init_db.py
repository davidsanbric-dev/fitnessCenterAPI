from pathlib import Path
import sys
from app.core.db import Base, engine
from app import models  # noqa: F401 - Ensure models are imported so they are registered with SQLAlchemy's metadata (even if not used directly in this script)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))



def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("Database schema initialized.")


if __name__ == "__main__":
    main()
