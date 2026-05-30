from sqlalchemy import (Column, Integer, BigInteger, String, Boolean,
                        DateTime, ForeignKey, Enum as SAEnum)
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime
import enum

class Base(DeclarativeBase): pass

class BookingStatus(enum.Enum):
    PENDING   = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    DONE      = "done"

class PaymentStatus(enum.Enum):
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    REJECTED  = "rejected"

class User(Base):
    __tablename__ = "users"
    id         = Column(BigInteger, primary_key=True)
    full_name  = Column(String, nullable=True)
    phone      = Column(String, nullable=True)
    username   = Column(String, nullable=True)
    registered = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    bookings   = relationship("Booking", back_populates="user")

class Service(Base):
    __tablename__ = "services"
    id        = Column(Integer, primary_key=True, autoincrement=True)
    name      = Column(String, nullable=False)
    price     = Column(Integer, default=0)
    duration  = Column(Integer, default=30)
    is_active = Column(Boolean, default=True)
    bookings  = relationship("Booking", back_populates="service")
    slots     = relationship("TimeSlot", back_populates="service", cascade="all, delete-orphan")

class TimeSlot(Base):
    __tablename__ = "time_slots"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    date       = Column(String, nullable=False)   # YYYY-MM-DD
    time       = Column(String, nullable=False)   # HH:MM
    is_booked  = Column(Boolean, default=False)
    service    = relationship("Service", back_populates="slots")
    bookings   = relationship("Booking", back_populates="slot")

class Booking(Base):
    __tablename__ = "bookings"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    user_id       = Column(BigInteger, ForeignKey("users.id"))
    service_id    = Column(Integer, ForeignKey("services.id"))
    slot_id       = Column(Integer, ForeignKey("time_slots.id"))
    contact_phone = Column(String, nullable=True)   # شماره تماس موقع رزرو
    status        = Column(SAEnum(BookingStatus), default=BookingStatus.PENDING)
    created_at    = Column(DateTime, default=datetime.utcnow)
    user          = relationship("User", back_populates="bookings")
    service       = relationship("Service", back_populates="bookings")
    slot          = relationship("TimeSlot", back_populates="bookings")
    payments      = relationship("Payment", back_populates="booking")

class Payment(Base):
    __tablename__ = "payments"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    booking_id   = Column(Integer, ForeignKey("bookings.id"))
    status       = Column(SAEnum(PaymentStatus), default=PaymentStatus.SUBMITTED)
    receipt_file = Column(String, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)
    booking      = relationship("Booking", back_populates="payments")

class HolidayDate(Base):
    __tablename__ = "holiday_dates"
    id        = Column(Integer, primary_key=True, autoincrement=True)
    date      = Column(String, nullable=False, unique=True)
    label     = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
