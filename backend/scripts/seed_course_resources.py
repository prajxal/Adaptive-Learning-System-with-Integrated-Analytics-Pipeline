import os
import sys
import urllib.parse
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from db.database import SessionLocal
from models.course import Course
from models.course_resource import CourseResource

# Curated resources mapped by (roadmap_id, course_title)
RESOURCES = {
    ("frontend-beginner", "HTML"): [
        {"title": "HTML Full Course - freeCodeCamp", "url": "https://www.youtube.com/watch?v=pQN-pnXPaVg", "type": "video"},
        {"title": "MDN HTML Basics", "url": "https://developer.mozilla.org/en-US/docs/Learn/Getting_started_with_the_web/HTML_basics", "type": "article"},
    ],
    ("frontend-beginner", "CSS"): [
        {"title": "CSS Full Course - freeCodeCamp", "url": "https://www.youtube.com/watch?v=1Rs2ND1ryYc", "type": "video"},
        {"title": "MDN CSS First Steps", "url": "https://developer.mozilla.org/en-US/docs/Learn/CSS/First_steps", "type": "article"},
    ],
    ("frontend-beginner", "JavaScript"): [
        {"title": "JavaScript Full Course - freeCodeCamp", "url": "https://www.youtube.com/watch?v=PkZNo7MFNFg", "type": "video"},
        {"title": "MDN JavaScript Guide", "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide", "type": "article"},
    ],
    ("frontend-beginner", "Git"): [
        {"title": "Git Full Course - freeCodeCamp", "url": "https://www.youtube.com/watch?v=RGOj5yH7evk", "type": "video"},
        {"title": "Pro Git Book", "url": "https://git-scm.com/book/en/v2", "type": "article"},
    ],
    ("frontend-beginner", "GitHub"): [
        {"title": "GitHub for Beginners", "url": "https://www.youtube.com/watch?v=iv8rSLsi1xo", "type": "video"},
        {"title": "GitHub Docs - Getting Started", "url": "https://docs.github.com/en/get-started", "type": "article"},
    ],
    ("frontend-beginner", "npm"): [
        {"title": "NPM Crash Course", "url": "https://www.youtube.com/watch?v=jHDhaSSKmB0", "type": "video"},
        {"title": "npm Docs", "url": "https://docs.npmjs.com/getting-started", "type": "article"},
    ],
    ("frontend-beginner", "React"): [
        {"title": "React Full Course - freeCodeCamp", "url": "https://www.youtube.com/watch?v=bMknfKXIFA8", "type": "video"},
        {"title": "React Official Docs", "url": "https://react.dev/learn", "type": "article"},
    ],
    ("frontend-beginner", "Tailwind"): [
        {"title": "Tailwind CSS Full Course", "url": "https://www.youtube.com/watch?v=pfaSUYaSgRo", "type": "video"},
        {"title": "Tailwind CSS Docs", "url": "https://tailwindcss.com/docs/installation", "type": "article"},
    ],
    ("frontend-beginner", "Vitest"): [
        {"title": "Vitest Crash Course", "url": "https://www.youtube.com/watch?v=snCLQmINqCU", "type": "video"},
        {"title": "Vitest Official Docs", "url": "https://vitest.dev/guide/", "type": "article"},
    ],
}

def seed():
    db = SessionLocal()
    try:
        inserted = 0
        for (roadmap_id, title), resources in RESOURCES.items():
            course = db.query(Course).filter(
                Course.roadmap_id == roadmap_id,
                Course.title == title
            ).first()

            if not course:
                print(f"WARNING: Course not found — {roadmap_id}:{title}")
                continue

            for r in resources:
                exists = db.query(CourseResource).filter(
                    CourseResource.course_id == course.id,
                    CourseResource.url == r["url"]
                ).first()
                if not exists:
                    db.add(CourseResource(
                        course_id=course.id,
                        title=r["title"],
                        url=r["url"],
                        resource_type=r["type"]
                    ))
                    inserted += 1

        db.commit()
        print(f"Seeded {inserted} curated resources successfully.")
        
        # Now seed all other roadmap courses dynamically so none are empty
        all_courses = db.query(Course).all()
        dynamic_inserted = 0
        for course in all_courses:
            if (course.roadmap_id, course.title) in RESOURCES:
                continue
                
            y_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(f'{course.roadmap_id} {course.title} tutorial')}"
            m_url = f"https://medium.com/search?q={urllib.parse.quote(f'{course.title} guide')}"

            existing_count = db.query(CourseResource).filter(CourseResource.course_id == course.id).count()
            if existing_count == 0:
                # Search result URLs cannot be embedded — store as article so they open externally
                db.add(CourseResource(
                    course_id=course.id,
                    title=f"Search: {course.title} tutorials on YouTube",
                    url=y_url,
                    resource_type="article"
                ))
                db.add(CourseResource(
                    course_id=course.id,
                    title=f"{course.title} Documentation & Articles",
                    url=m_url,
                    resource_type="article"
                ))
                dynamic_inserted += 2
                
        db.commit()
        print(f"Seeded {dynamic_inserted} dynamic resources for remaining courses.")

    finally:
        db.close()

if __name__ == "__main__":
    seed()
