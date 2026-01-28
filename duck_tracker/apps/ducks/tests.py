from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from .models import Flock
from .models import Stats

DEFAULT_DUCK_COUNT = 100
SMALL_DUCK_COUNT = 50

DEFAULT_HARVEST = 10
SECOND_HARVEST = 15
EXCESS_HARVEST = 101

SECOND_DAY = 2
HARVEST_DELTA = 5

ZERO = 0
REL_TOLERANCE = 1e-2


class FlockModelTests(TestCase):
    """Unit tests for Flock model."""

    def setUp(self):
        today = timezone.now().date()
        self.flock = Flock.objects.create(
            title="Test Flock",
            number_of_ducks=DEFAULT_DUCK_COUNT,
            description="A test flock",
            started_date=today - timedelta(days=10),
        )

    def test_flock_creation(self):
        assert self.flock.title == "Test Flock"
        assert self.flock.number_of_ducks == DEFAULT_DUCK_COUNT
        assert not self.flock.is_culled

    def test_flock_str(self):
        value = str(self.flock)
        assert "Test Flock" in value
        assert "Ongoing" in value

    def test_flock_culled_date_before_started_date_invalid(self):
        today = timezone.now().date()
        flock = Flock(
            title="Invalid Flock",
            number_of_ducks=DEFAULT_DUCK_COUNT,
            started_date=today,
            culled_date=today - timedelta(days=1),
        )
        with pytest.raises(ValidationError):
            flock.full_clean()

    def test_flock_auto_set_is_culled(self):
        self.flock.culled_date = timezone.now().date()
        self.flock.save()
        assert self.flock.is_culled

    def test_flock_auto_set_culled_date_when_is_culled_true(self):
        flock = Flock.objects.create(
            title="Auto Cull Flock",
            number_of_ducks=SMALL_DUCK_COUNT,
            culled_date=timezone.now().date(),
        )
        flock.refresh_from_db()
        assert flock.is_culled


class StatsModelTests(TestCase):
    """Unit tests for Stats model."""

    def setUp(self):
        today = timezone.now().date()
        self.flock = Flock.objects.create(
            title="Stats Test Flock",
            number_of_ducks=DEFAULT_DUCK_COUNT,
            started_date=today - timedelta(days=5),
        )
        self.stats1 = Stats.objects.create(
            flock=self.flock,
            date=today - timedelta(days=4),
            harvested=DEFAULT_HARVEST,
            mortality=ZERO,
        )
        self.stats2 = Stats.objects.create(
            flock=self.flock,
            date=today - timedelta(days=3),
            harvested=SECOND_HARVEST,
            mortality=1,
        )

    def test_stats_creation(self):
        assert self.stats1.harvested == DEFAULT_HARVEST
        assert self.stats1.day == 1

    def test_stats_auto_calc_percentage(self):
        expected = (DEFAULT_HARVEST / DEFAULT_DUCK_COUNT) * 100
        assert self.stats1.percentage == expected

    def test_stats_auto_set_day(self):
        assert self.stats1.day == 1
        assert self.stats2.day == SECOND_DAY

    def test_stats_harvested_exceeds_flock_size_invalid(self):
        invalid = Stats(
            flock=self.flock,
            date=timezone.now().date(),
            harvested=EXCESS_HARVEST,
        )
        with pytest.raises(ValidationError):
            invalid.full_clean()

    def test_stats_date_not_unique_per_flock_invalid(self):
        duplicate = Stats(
            flock=self.flock,
            date=self.stats1.date,
            harvested=HARVEST_DELTA,
        )
        with pytest.raises(ValidationError):
            duplicate.full_clean()

    def test_stats_date_before_flock_started_invalid(self):
        invalid = Stats(
            flock=self.flock,
            date=self.flock.started_date - timedelta(days=1),
            harvested=HARVEST_DELTA,
        )
        with pytest.raises(ValidationError):
            invalid.full_clean()

    def test_stats_date_cannot_be_changed_on_edit(self):
        self.stats1.date = timezone.now().date()
        with pytest.raises(ValidationError):
            self.stats1.full_clean()

    def test_stats_previous_property(self):
        assert self.stats2.previous.id == self.stats1.id

    def test_stats_previous_property_none_for_first(self):
        assert self.stats1.previous is None

    def test_stats_harvested_delta(self):
        assert self.stats2.harvested_delta == HARVEST_DELTA

    def test_stats_harvested_delta_none_for_first(self):
        assert self.stats1.harvested_delta is None

    def test_stats_harvested_delta_pct(self):
        expected = (HARVEST_DELTA / DEFAULT_HARVEST) * 100
        assert self.stats2.harvested_delta_pct == pytest.approx(
            expected,
            rel=REL_TOLERANCE,
        )

    def test_stats_harvested_delta_pct_none_for_first(self):
        assert self.stats1.harvested_delta_pct is None

    def test_stats_str(self):
        value = str(self.stats1)
        assert "Day 1" in value
        assert str(DEFAULT_HARVEST) in value
