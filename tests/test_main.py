import sys
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# --- путь к backend ---
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
sys.path.insert(0, BACKEND_DIR)

from main import app, Base, Booking

# ------------------ engine ------------------
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

# ------------------ фикстура ------------------
@pytest.fixture(autouse=True)
def override_db(monkeypatch):
    monkeypatch.setattr("main.SessionLocal", TestingSessionLocal)
    yield
    # чистим таблицы после каждого теста
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

# ------------------ клиент ------------------
client = TestClient(app)

# ------------------ ТЕСТЫ ------------------
def test_create_booking():
    response = client.post("/api/book", json={
        "name": "Test User",
        "phone": "123456",
        "email": "test@test.com",
        "service": "reinigung1",
        "start_time": "2099-12-31T12:00:00"
    })
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_booking_overlap():
    client.post("/api/book", json={
        "name": "A",
        "phone": "1",
        "email": "a@test.com",
        "service": "reinigung1",
        "start_time": "2099-12-31T10:00:00"
    })

    response = client.post("/api/book", json={
        "name": "B",
        "phone": "2",
        "email": "b@test.com",
        "service": "reinigung1",
        "start_time": "2099-12-31T10:30:00"
    })

    assert response.status_code == 400
    assert "Zeit bereits belegt" in response.json()["detail"]


def test_cancel_booking():
    # создаём бронь
    client.post("/api/book", json={
        "name": "Cancel",
        "phone": "3",
        "email": "c@test.com",
        "service": "reinigung1",
        "start_time": "2099-12-31T15:00:00"
    })

    # получаем бронь через API (а не напрямую БД!)
    response = client.get("/api/admin/bookings")
    assert response.status_code == 200

    bookings = response.json()
    assert len(bookings) == 1

    booking_id = bookings[0]["id"]

    # отмена через admin
    response = client.post(f"/api/admin/cancel/{booking_id}")
    assert response.status_code == 200
    assert response.json()["ok"] is True

