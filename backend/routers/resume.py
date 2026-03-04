from fastapi import APIRouter, UploadFile, File, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
import os

from core.security import get_current_user
from db.database import get_db, SessionLocal
from services.resume_parser import ingest_resume
from models.user import User

router = APIRouter()

UPLOAD_DIR = "uploads/resumes"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def process_resume_background(user_id: str, file_bytes: bytes, filename: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return

        print(f"\n[ResumeAPI] Background task started for User: {user_id}")
        file_path = f"{UPLOAD_DIR}/{user_id}_{filename}"

        with open(file_path, "wb") as buffer:
            buffer.write(file_bytes)
            print(f"[ResumeAPI] File successfully saved to disk: {file_path}")

        # EXISTING pdfplumber extraction logic
        # EXISTING SkillWeight insertion logic
        ingest_resume(file_path, str(user_id), db)

        user.resume_status = "completed"
        db.commit()

    except Exception as e:
        print(f"[ResumeAPI] Resume processing failed for User: {user_id}. Error: {e}")
        db.rollback()
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.resume_status = "failed"
            db.commit()

    finally:
        db.close()


@router.post("/upload", status_code=202)
async def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    print(f"\n[ResumeAPI] Received Resume upload request from User: {current_user.id}")
    
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    file_bytes = await file.read()

    current_user.resume_status = "processing"
    db.commit()
    db.refresh(current_user)

    background_tasks.add_task(
        process_resume_background,
        str(current_user.id),
        file_bytes,
        file.filename
    )

    return {"status": "processing"}


@router.get("/status")
def get_resume_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return {"status": current_user.resume_status}
