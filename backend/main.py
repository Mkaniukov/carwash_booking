from fastapi import FastAPI, HTTPException, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime, timedelta, time
import uuid
import smtplib
from fastapi.middleware.cors import CORSMiddleware
import os

# ================= CONFIG =================
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

WORK_START = time(7, 30)
WORK_END = time(18, 0)

DATABASE_URL = "sqlite:///./bookings.db"

# ==========================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Монтируем статические файлы (JS, CSS) из frontend/static
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "frontend", "static")), name="static")

# ================= MODEL ==================
class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    phone = Column(String)
    email = Column(String)
    service = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    status = Column(String, default="confirmed")
    cancel_token = Column(String, unique=True)

Base.metadata.create_all(engine)

# ================= EMAIL ==================
def send_email(to, subject, body):
    try:
        with smtplib.SMTP("localhost", 1025) as server:
            server.sendmail(
                "noreply@carwash.at",
                to,
                f"Subject: {subject}\n\n{body}"
            )
    except Exception as e:
        print("Email konnte nicht gesendet werden:", e)

# ================= API ====================
@app.get("/api/slots")
def slots():
    db = SessionLocal()
    data = db.query(Booking).filter(Booking.status=="confirmed").all()
    db.close()
    return [
        {
            "start_time": b.start_time.isoformat(),
            "end_time": b.end_time.isoformat()
        }
        for b in data
    ]

@app.post("/api/book")
async def book(data: dict):
    db = SessionLocal()
    start = datetime.fromisoformat(data["start_time"])
    duration_map = {"reinigung1": 60, "reinigung2": 90, "reinigung3": 120}
    duration = duration_map[data["service"]]
    end = start + timedelta(minutes=duration)

    now = datetime.now()
    if start < now:
        raise HTTPException(400, "Sie können keine Termine in der Vergangenheit buchen.")
    if start.time() < WORK_START or end.time() > WORK_END:
        raise HTTPException(
            400, 
            f"Dieser Termin passt nicht in die Arbeitszeiten: {WORK_START.strftime('%H:%M')}–{WORK_END.strftime('%H:%M')}."
        )

    # Проверка пересечения
    overlap = db.query(Booking).filter(
        Booking.status=="confirmed",
        Booking.start_time < end,
        Booking.end_time > start
    ).first()
    if overlap:
        db.close()
        raise HTTPException(400, "Zeit bereits belegt")

    token = str(uuid.uuid4())
    booking = Booking(
        name=data["name"],
        phone=data["phone"],
        email=data["email"],
        service=data["service"],
        start_time=start,
        end_time=end,
        cancel_token=token
    )
    db.add(booking)
    db.commit()
    db.close()
    return {"ok": True}

@app.get("/", response_class=HTMLResponse)
def index():
    frontend_path = os.path.join(BASE_DIR, "frontend", "index.html")
    with open(frontend_path, encoding="utf-8") as f:
        return f.read()

@app.get("/api/cancel/{token}")
def cancel(token: str):
    db = SessionLocal()
    booking = db.query(Booking).filter(Booking.cancel_token==token).first()
    if not booking:
        raise HTTPException(404)
    booking.status = "canceled"
    db.commit()
    db.close()
    return {"ok": True}

# ================= ADMIN ==================
@app.get("/admin", response_class=HTMLResponse)
def admin_page():
    frontend_path = os.path.join(BASE_DIR, "frontend", "admin.html")
    with open(frontend_path, encoding="utf-8") as f:
        return f.read()

@app.post("/admin/login")
def admin_login(user: str = Form(...), password: str = Form(...)):
    if user == ADMIN_USER and password == ADMIN_PASS:
        return {"ok": True}
    raise HTTPException(401, "Invalid credentials")

@app.get("/api/admin/bookings")
def admin_bookings():
    db = SessionLocal()
    bookings = db.query(Booking).all()
    db.close()
    return [
        {
            "id": b.id,
            "name": b.name,
            "service": b.service,
            "start": b.start_time.isoformat(),
            "end": b.end_time.isoformat(),
            "status": b.status
        }
        for b in bookings
    ]

@app.post("/api/admin/cancel/{id}")
def admin_cancel(id: int):
    db = SessionLocal()
    b = db.query(Booking).get(id)
    if not b:
        raise HTTPException(404)
    b.status = "canceled"
    db.commit()
    db.close()
    return {"ok": True}
