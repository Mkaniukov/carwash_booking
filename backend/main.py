from fastapi import FastAPI, HTTPException, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime, timedelta, time
import uuid
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic_settings import BaseSettings, SettingsConfigDict
from fastapi_mail import ConnectionConfig
import os

# ================== SETTINGS ==================
class Settings(BaseSettings):
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    DOMAIN: str = "http://localhost:8000"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow"
    )

settings = Settings()  # создаём объект настроек

# ================== CONFIG ==================
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

WORK_START = time(7, 30)
WORK_END = time(18, 0)

DATABASE_URL = "sqlite:///./bookings.db"

# ================== SERVICES ==================
SERVICES = {
    "car_spa": {
        "name": "CAR SPA®",
        "price": 24,
        "duration": 30,
        "description": "Schnelle, günstige und schonende textile Außenwäsche. "
                       "Manuelle Vorreinigung – Aktivschaum – Shampoowäsche – "
                       "Radwäsche – maschinelles Trocknen."
    },
    "car_soft": {
        "name": "CAR SOFT",
        "price": 36,
        "duration": 30,
        "description": "Intensive, schonende textile Außenwäsche mit Felgenreinigung extra. "
                       "Manuelle Vorreinigung – händische Felgenreinigung – Aktivschaum – "
                       "Shampoowäsche – Radwäsche – maschinelle Trocknung & zusätzliche "
                       "manuelle Nachtrocknung."
    },
    "car_easy": {
        "name": "CAR EASY",
        "price": 74,
        "duration": 90,
        "description": "Einfache Außen- und Innenreinigung (ohne Kofferraum oder Ladefläche). "
                       "Manuelle Vorreinigung – händische Felgenreinigung – Aktivschaum – "
                       "Shampoowäsche – Radwäsche – maschinelle Trocknung & zusätzliche "
                       "manuelle Nachtrocknung – Reinigung von Fußmatten, Innenflächen "
                       "(nur glatte Flächen) und Armaturen – Saugen von Teppichen, Sitzen, "
                       "Seitenverkleidungen – Reinigung von Scheiben und Spiegeln – "
                       "fachgerechte Endkontrolle."
    },
    "car_wellness": {
        "name": "CAR WELLNESS",
        "price": 86,
        "duration": 120,
        "description": "Intensive Außen- und Innenreinigung (mit Kofferraum oder Ladefläche). "
                       "Manuelle Vorreinigung – händische Felgenreinigung – Aktivschaum – "
                       "Shampoowäsche – Radwäsche – maschinelle Trocknung & zusätzliche "
                       "manuelle Nachtrocknung – Reinigung von Fußmatten, Innenflächen "
                       "(nur glatte Flächen) und Armaturen – Saugen von Teppichen, Sitzen, "
                       "Seitenverkleidungen – Reinigung von Scheiben und Spiegeln – "
                       "fachgerechte Endkontrolle."
    },
    "car_intense": {
        "name": "CAR INTENSE (Innen)",
        "price": 68,
        "duration": 90,
        "description": "Intensive Innenreinigung (mit Kofferraum oder Ladefläche). "
                       "Reinigung von Fußmatten, Innenflächen (nur glatte Flächen) "
                       "und Armaturen – Saugen von Teppichen, Sitzen, Seitenverkleidungen – "
                       "Reinigung von Scheiben und Spiegeln – fachgerechte Endkontrolle."
    }
}

# ================== DATABASE ==================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

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

# ================== APP ==================
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "frontend", "static")), name="static")

# ================== EMAIL CONFIG ==================
conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,       # вместо MAIL_TLS
    MAIL_SSL_TLS=False,       # SSL/TLS не используем на порту 587
    USE_CREDENTIALS=True,
    TEMPLATE_FOLDER=os.path.join(BASE_DIR, "frontend")  # укажи реально существующую папку
)

def render_booking_email(name: str, service_name: str, start: datetime, cancel_token: str):
    cancel_url = f"{settings.DOMAIN}/cancel/{cancel_token}"
    return f"""
    <html>
    <body>
        <h2>Hallo {name},</h2>
        <p>Ihre Buchung für <b>{service_name}</b> am <b>{start.strftime('%d.%m.%Y um %H:%M')}</b> wurde erfolgreich bestätigt.</p>
        <p>Wenn Sie die Buchung stornieren möchten, klicken Sie bitte auf den folgenden Link:</p>
        <a href="{cancel_url}" style="display:inline-block;padding:10px 15px;background-color:#ff4c4c;color:white;text-decoration:none;border-radius:5px;">Buchung stornieren</a>
        <hr>
        <p>Vielen Dank für Ihre Buchung!</p>
    </body>
    </html>
    """

# ================== API ==================
@app.get("/api/services")
def get_services():
    return SERVICES

@app.get("/api/slots")
def slots():
    db = SessionLocal()
    data = db.query(Booking).filter(Booking.status == "confirmed").all()
    db.close()
    return [{"start_time": b.start_time.isoformat(), "end_time": b.end_time.isoformat()} for b in data]

@app.post("/api/book")
async def book(data: dict):
    service = SERVICES[data["service"]]
    start = datetime.fromisoformat(data["start_time"])
    end = start + timedelta(minutes=service["duration"])

    if start < datetime.now():
        raise HTTPException(400, "Termin liegt in der Vergangenheit")
    if start.time() < WORK_START or end.time() > WORK_END:
        raise HTTPException(400, "Außerhalb der Arbeitszeiten")

    db = SessionLocal()
    overlap = db.query(Booking).filter(
        Booking.status == "confirmed",
        Booking.start_time < end,
        Booking.end_time > start
    ).first()
    if overlap:
        db.close()
        raise HTTPException(400, "Zeit bereits belegt")

    booking = Booking(
        name=data["name"],
        phone=data["phone"],
        email=data["email"],
        service=data["service"],
        start_time=start,
        end_time=end,
        cancel_token=str(uuid.uuid4())
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    db.close()

    # Отправка email
    html_body = render_booking_email(
        name=data["name"],
        service_name=service["name"],
        start=start,
        cancel_token=booking.cancel_token
    )
    message = MessageSchema(
        subject="Bestätigung Ihrer Buchung",
        recipients=[data["email"]],
        body=html_body,
        subtype="html"
    )
    fm = FastMail(conf)

    try:
        await fm.send_message(message)
    except Exception as e:
        # Логируем ошибку, но не ломаем сервер
        print(f"Ошибка при отправке email: {e}")

    # Отправка email администратору
    admin_email = settings.MAIL_USERNAME  # или любой другой, если админ отдельный
    html_body_admin = f"""
    <html>
    <body>
        <h2>Neue Buchung</h2>
        <p>Service: {service['name']}</p>
        <p>Name: {data['name']}</p>
        <p>Telefon: {data['phone']}</p>
        <p>Email: {data['email']}</p>
        <p>Datum & Uhrzeit: {start.strftime('%d.%m.%Y um %H:%M')}</p>
    </body>
    </html>
    """
    message_admin = MessageSchema(
        subject="Neue Buchung eingegangen",
        recipients=[admin_email],
        body=html_body_admin,
        subtype="html"
    )

    try:
        await fm.send_message(message_admin)
    except Exception as e:
        print(f"Ошибка при отправке email администратору: {e}")

# ================== CANCEL ==================
@app.get("/cancel/{token}", response_class=HTMLResponse)
def cancel_booking(token: str):
    db = SessionLocal()
    booking = db.query(Booking).filter(Booking.cancel_token == token).first()
    if not booking:
        db.close()
        return "<h3>Buchung nicht gefunden oder bereits storniert.</h3>"

    booking.status = "canceled"
    db.commit()
    db.close()

    return f"""
    <h3>Ihre Buchung für {SERVICES.get(booking.service, {'name': booking.service})['name']} 
    am {booking.start_time.strftime('%d.%m.%Y um %H:%M')} wurde erfolgreich storniert.</h3>
    """

# ================== PAGES ==================
@app.get("/", response_class=HTMLResponse)
def index():
    return open(os.path.join(BASE_DIR, "frontend", "index.html"), encoding="utf-8").read()

@app.get("/success", response_class=HTMLResponse)
def success():
    return open(os.path.join(BASE_DIR, "frontend", "success.html"), encoding="utf-8").read()

@app.get("/admin", response_class=HTMLResponse)
def admin():
    return open(os.path.join(BASE_DIR, "frontend", "admin.html"), encoding="utf-8").read()

@app.post("/admin/login")
def admin_login(user: str = Form(...), password: str = Form(...)):
    if user == ADMIN_USER and password == ADMIN_PASS:
        return {"ok": True}
    raise HTTPException(401)

@app.get("/api/admin/bookings")
def admin_bookings():
    db = SessionLocal()
    data = db.query(Booking).all()
    db.close()
    result = []
    for b in data:
        service_name = SERVICES.get(b.service, {"name": b.service})["name"]
        result.append({
            "id": b.id,
            "name": b.name,
            "phone": b.phone,
            "service": service_name,
            "date": b.start_time.strftime("%d.%m.%Y") if b.start_time else "–",
            "time": b.start_time.strftime("%H:%M") if b.start_time else "–",
            "status": b.status
        })
    return result

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
