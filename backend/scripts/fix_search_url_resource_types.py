"""
One-off migration: fix course_resources rows where resource_type="video"
but the URL is a YouTube search results page (cannot be embedded).
Changes them to resource_type="article" so the frontend opens them externally.
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from db.database import SessionLocal
from models.course_resource import CourseResource


def main():
    db = SessionLocal()
    try:
        bad_rows = db.query(CourseResource).filter(
            CourseResource.resource_type == "video",
            CourseResource.url.like("%youtube.com/results%")
        ).all()

        if not bad_rows:
            print("No bad rows found — nothing to fix.")
            return

        for row in bad_rows:
            print(f"Fixing: [{row.course_id}] {row.title[:60]}")
            row.resource_type = "article"

        db.commit()
        print(f"\nFixed {len(bad_rows)} rows.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
