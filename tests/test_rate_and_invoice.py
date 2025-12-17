import os
import tempfile
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, crud, database


@pytest.fixture
def in_memory_db():
    engine = create_engine('sqlite:///:memory:', connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    models.Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_rate_calculation_fixed(in_memory_db):
    db = in_memory_db
    # default RATE_PER_UNIT env not used for fixed
    rc = crud.set_rate_config(db, 'fixed', 2.0)
    eff = crud.get_effective_rate(db)
    assert eff == 2.0


def test_rate_calculation_percent(in_memory_db, monkeypatch):
    db = in_memory_db
    monkeypatch.setenv('RATE_PER_UNIT', '1.5')
    rc = crud.set_rate_config(db, 'percent', 10.0)
    eff = crud.get_effective_rate(db)
    assert abs(eff - 1.65) < 1e-6


def test_invoice_generation_uses_rate(in_memory_db):
    db = in_memory_db
    # create customer and two readings
    c = models.Customer(name='Test', phone='+1000000000')
    db.add(c)
    db.commit()
    db.refresh(c)
    r1 = models.MeterReading(customer_id=c.id, reading_value=100.0)
    r2 = models.MeterReading(customer_id=c.id, reading_value=130.0)
    db.add_all([r2, r1])
    db.commit()
    # set rate
    crud.set_rate_config(db, 'fixed', 2.0)
    rate = crud.get_effective_rate(db)
    calc = crud.calculate_amount_from_readings(db, c.id, rate)
    assert calc is not None
    amount, _, _ = calc
    # usage 30 * 2.0 = 60
    assert abs(amount - 60.0) < 1e-6
