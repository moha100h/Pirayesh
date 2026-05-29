from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum, BigInteger
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime
import enum

class Base(DeclarativeBase):
    pass

class BookingStatus(str, enum.Enum):
    PENDING   = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    DONE      = "done"

class PaymentStatus(str, enum.Enum):
    PENDING   = "pending"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    REJECTED  = "rejected"

class User(Base):
    __tablename__ = "users"
    id         = Column(BigInteger, primary_key=True)
    full_name  = Column(String(120))
    phone      = Column(String(20))
    username   = Column(String(80))
    created_at = Column(DateTime, default=datetime.utcnow)
    bookings   = relationship("Booking", back_populates="user")

class Service(Base):
    __tablename__ = "services"
    id        = Column(Integer, primary_key=True, autoincrement=True)
    name      = Column(String(100), nullable=False)
    price     = Column(Integer, nullable=False)
    duration  = Column(Integer, default=30)
    is_active = Column(Boolean, default=True)
    bookings  = relationship("Booking", back_populates="service")

class TimeSlot(Base):
    __tablename__ = "timeslots"
    id        = Column(Integer, primary_key=True, autoincrement=True)
    date      = Column(String(10), nullable=False)
    time      = Column(String(5),  nullable=False)
    is_booked = Column(Boolean, default=False)
    booking   = relationship("Booking", back_populates="slot", uselist=False)

class Booking(Base):
    __tablename__ = "bookings"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    user_id    = Column(BigInteger, ForeignKey("users.id"))
    service_id = Column(Integer, ForeignKey("services.id"))
    slot_id    = Column(Integer, ForeignKey("timeslots.id"))
    status     = Column(Enum(BookingStatus), default=BookingStatus.PENDING)
    note       = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    user       = relationship("User", back_populates="bookings")
    service    = relationship("Service", back_populates="bookings")
    slot       = relationship("TimeSlot", back_populates="booking")
    payment    = relationship("Payment", back_populates="booking", uselist=False)

class Payment(Base):
    __tablename__ = "payments"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    booking_id   = Column(Integer, ForeignKey("bookings.id"))
    amount       = Column(Integer)
    status       = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    receipt_file = Column(String(200))
    note         = Column(Text)
    created_at   = Column(DateTime, default=datetime.utcnow)
    booking      = relationship("Booking", back_populates="payment")
