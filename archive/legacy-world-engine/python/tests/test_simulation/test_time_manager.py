"""
Tests for the TimeManager.
"""
import pytest
from src.simulation.environment.time_manager import TimeManager


class TestTimeManagerInit:
    def test_default_construction(self):
        tm = TimeManager()
        assert tm.day == 1
        assert tm.hour == 0
        assert tm.minute == 0
        assert tm.speed_multiplier == 1.0
        assert tm.total_minutes_elapsed == 0

    def test_custom_construction(self):
        tm = TimeManager(start_day=3, start_hour=14, start_minute=30, speed_multiplier=5.0)
        assert tm.day == 3
        assert tm.hour == 14
        assert tm.minute == 30
        assert tm.speed_multiplier == 5.0
        assert tm.total_minutes_elapsed == (3 - 1) * 1440 + 14 * 60 + 30

    def test_clamps_init_hour_minute(self):
        tm = TimeManager(start_hour=25, start_minute=70)
        assert tm.hour == 23
        assert tm.minute == 59


class TestTimeManagerAdvance:
    def test_advance_minutes(self):
        tm = TimeManager(start_hour=10, start_minute=0)
        tm.advance(90)
        assert tm.hour == 11
        assert tm.minute == 30

    def test_advance_crosses_day_boundary(self):
        tm = TimeManager(start_day=1, start_hour=23, start_minute=30)
        tm.advance(60)
        assert tm.day == 2
        assert tm.hour == 0
        assert tm.minute == 30

    def test_total_minutes_elapsed_increases(self):
        tm = TimeManager(start_hour=10)
        initial = tm.total_minutes_elapsed
        tm.advance(60)
        assert tm.total_minutes_elapsed == initial + 60

    def test_advance_fractional(self):
        tm = TimeManager(start_hour=10, start_minute=0)
        tm.advance(0.5)
        assert tm.minute == 0  # rounds to 0


class TestTimeManagerSetTime:
    def test_set_time_same_day(self):
        tm = TimeManager(start_hour=10, start_minute=0)
        tm.set_time(15, 45)
        assert tm.hour == 15
        assert tm.minute == 45

    def test_set_time_preserves_day(self):
        tm = TimeManager(start_day=5, start_hour=10)
        tm.advance(120)
        tm.set_time(8, 0)
        assert tm.day == 5  # Same day
        assert tm.hour == 8

    def test_set_time_invalid_hour(self):
        tm = TimeManager()
        with pytest.raises(ValueError):
            tm.set_time(25, 0)

    def test_set_time_invalid_minute(self):
        tm = TimeManager()
        with pytest.raises(ValueError):
            tm.set_time(10, 60)


class TestTimeManagerProperties:
    def test_is_daytime_morning(self):
        tm = TimeManager(start_hour=10)
        assert tm.is_daytime is True

    def test_is_daytime_evening(self):
        tm = TimeManager(start_hour=22)
        assert tm.is_daytime is False

    def test_is_daytime_boundary_morning(self):
        tm = TimeManager(start_hour=5)
        assert tm.is_daytime is False

    def test_is_daytime_boundary_evening(self):
        tm = TimeManager(start_hour=19)
        assert tm.is_daytime is True

    def test_day_of_week_monday(self):
        tm = TimeManager(start_day=1)
        assert tm.day_of_week == "Monday"

    def test_day_of_week_sunday(self):
        tm = TimeManager(start_day=7)
        assert tm.day_of_week == "Sunday"

    def test_weekend_true(self):
        tm = TimeManager(start_day=6)  # Saturday
        assert tm.weekend is True

    def test_weekend_false(self):
        tm = TimeManager(start_day=1)  # Monday
        assert tm.weekend is False

    def test_day_of_week_wraps(self):
        tm = TimeManager(start_day=8)
        assert tm.day_of_week == "Monday"
        assert tm.day == 8


class TestTimeManagerSpeed:
    def test_set_speed_valid(self):
        tm = TimeManager()
        tm.set_speed(5.0)
        assert tm.speed_multiplier == 5.0

    def test_set_speed_zero_raises(self):
        tm = TimeManager()
        with pytest.raises(ValueError):
            tm.set_speed(0)

    def test_set_speed_negative_raises(self):
        tm = TimeManager()
        with pytest.raises(ValueError):
            tm.set_speed(-1)


class TestTimeManagerSerialization:
    def test_to_dict(self):
        tm = TimeManager(start_day=3, start_hour=14, start_minute=30, speed_multiplier=5.0)
        d = tm.to_dict()
        assert d["day"] == 3
        assert d["hour"] == 14
        assert d["minute"] == 30
        assert d["speed_multiplier"] == 5.0
        assert d["total_minutes_elapsed"] == (3 - 1) * 1440 + 14 * 60 + 30
        assert d["start_day"] == 3
        assert d["start_hour"] == 14
        assert d["start_minute"] == 30

    def test_from_dict_roundtrip(self):
        tm = TimeManager(start_day=5, start_hour=8, start_minute=15, speed_multiplier=20.0)
        tm.advance(300)
        d = tm.to_dict()
        tm2 = TimeManager.from_dict(d)
        assert tm2.day == tm.day
        assert tm2.hour == tm.hour
        assert tm2.minute == tm.minute
        assert tm2.speed_multiplier == tm.speed_multiplier
        assert tm2.total_minutes_elapsed == tm.total_minutes_elapsed
