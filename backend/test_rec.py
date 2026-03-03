import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from db.database import SessionLocal
from models.user import User
from routers.recommend import recommend

db = SessionLocal()
user = db.query(User).first()
if user:
    print(f"Testing with user: {user.id}")
    try:
        res = recommend(current_roadmap_id="python-developer", db=db, current_user=user)
        print("Success:")
        print(res)
    except Exception as e:
        import traceback
        traceback.print_exc()
else:
    print("No user found")
