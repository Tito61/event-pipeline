"""
Storage layer. Uses SQLite for this local demo so it runs with zero setup;
the schema and SQLAlchemy models are Postgres-compatible — swapping the
DATABASE_URL to a postgres:// connection string is the only change needed
for production (see README).
"""
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, JSON
from sqlalchemy.orm import declarative_base, sessionmaker
from typing import List
from models import Event

Base = declarative_base()


class EventRecord(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String, nullable=False)
    source_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    start_datetime = Column(DateTime, nullable=True)
    timezone = Column(String, nullable=True)
    venue = Column(String, nullable=True)
    city = Column(String, nullable=True)
    address = Column(String, nullable=True)
    category = Column(String, nullable=True)
    description = Column(String, nullable=True)
    event_url = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    ticket_info = Column(String, nullable=True)
    price_min = Column(Float, nullable=True)
    price_max = Column(Float, nullable=True)
    currency = Column(String, nullable=True)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    raw_payload = Column(JSON, nullable=True)


def get_session(db_url: str = "sqlite:///events.db"):
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def save_events(session, events: List[Event]):
    session.query(EventRecord).delete()  # demo: full refresh each run; production would upsert on source_id
    for e in events:
        session.add(EventRecord(
            source=e.source, source_id=e.source_id, name=e.name,
            start_datetime=e.start_datetime, timezone=e.timezone,
            venue=e.venue, city=e.city, address=e.address, category=e.category,
            description=e.description, event_url=e.event_url, image_url=e.image_url,
            ticket_info=e.ticket_info, price_min=e.price_min, price_max=e.price_max,
            currency=e.currency, lat=e.lat, lon=e.lon, raw_payload=e.raw_payload,
        ))
    session.commit()
