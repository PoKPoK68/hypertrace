"""
tests/test_reader.py

Tests de base pour le DataReader (mode mock uniquement).
"""

import time

import pytest

from lmu_app.api.reader import DataReader, LMUSnapshot, MockReader


def test_mock_reader_starts_and_stops():
    reader = MockReader(update_hz=50)
    reader.start()
    time.sleep(0.1)
    assert reader.is_connected
    reader.stop()


def test_mock_reader_provides_snapshot():
    reader = MockReader(update_hz=50)
    reader.start()
    time.sleep(0.15)  # laisser le temps à quelques ticks

    snap = reader.get()
    assert isinstance(snap, LMUSnapshot)
    assert snap.game_running is True
    assert snap.vehicle.speed_kmh >= 0.0
    assert snap.vehicle.rpm >= 0.0
    assert snap.session.track_name != ""

    reader.stop()


def test_data_reader_mock_mode():
    reader = DataReader(mock=True, update_hz=50)
    reader.start()
    time.sleep(0.1)

    snap = reader.get()
    assert snap.vehicle.fuel_capacity == 100.0
    assert 0.0 <= snap.vehicle.throttle <= 1.0
    assert 0.0 <= snap.vehicle.brake <= 1.0

    reader.stop()


def test_snapshot_tyres():
    reader = MockReader(update_hz=50)
    reader.start()
    time.sleep(0.15)

    snap = reader.get()
    assert len(snap.tyres.temp_surface) == 4
    assert len(snap.tyres.wear) == 4
    for t in snap.tyres.temp_surface:
        assert 50.0 <= t <= 150.0

    reader.stop()
