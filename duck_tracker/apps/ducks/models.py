from decimal import Decimal

from django.db import models
from django.utils import timezone

from config.settings.base import DATE_FORMAT

from .validators import validate_flock_dates
from .validators import validate_stats_entry


def today():
    return timezone.now().date()


class Flock(models.Model):
    title = models.CharField(max_length=100)
    number_of_ducks = models.PositiveIntegerField()
    description = models.TextField(blank=True, verbose_name="Notes")
    started_date = models.DateField(default=today)
    culled_date = models.DateField(blank=True, null=True)
    is_culled = models.BooleanField(default=False)

    class Meta:
        ordering = ["started_date"]
        verbose_name_plural = "Flocks"

    def __str__(self):
        cull = self.culled_date.strftime(DATE_FORMAT) if self.culled_date else "Ongoing"
        return f"{self.title} ({self.started_date.strftime(DATE_FORMAT)} - {cull})"

    def save(self, *args, **kwargs):
        # Auto-set is_culled
        self.is_culled = self.culled_date is not None

        # Auto-set culled_date if marked culled
        if self.is_culled and self.culled_date is None:
            self.culled_date = today()

        super().save(*args, **kwargs)

    def clean(self):
        validate_flock_dates(self)

    @property
    def total_harvested(self):
        return (
            self.stats.aggregate(
                total=models.Sum("harvested"),
            )["total"]
            or 0
        )

    @property
    def avg_harvested(self):
        days_count = self.stats.count()
        if days_count == 0:
            return 0
        return self.total_harvested // days_count

    @property
    def total_mortality(self):
        return (
            self.stats.aggregate(
                total=models.Sum("mortality"),
            )["total"]
            or 0
        )

    @property
    def average_percentage(self):
        return self.stats.aggregate(
            average=models.Avg("percentage"),
        )["average"] or Decimal("0.00")

    @property
    def total_feed_consumed(self):
        return (
            self.stats.aggregate(
                total=models.Sum("feed_consumed"),
            )["total"]
            or 0.0
        )

    @property
    def avg_daily_feed_consumed(self):
        days_count = self.stats.count()
        if days_count == 0:
            return 0.0
        return self.total_feed_consumed / days_count


class Stats(models.Model):
    flock = models.ForeignKey(
        Flock,
        on_delete=models.CASCADE,
        related_name="stats",
    )
    day = models.PositiveIntegerField(blank=True, null=True)
    date = models.DateField(default=today)
    harvested = models.PositiveBigIntegerField(default=0)
    percentage = models.DecimalField(
        blank=True,
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    notes = models.TextField(blank=True)
    mortality = models.PositiveBigIntegerField(default=0)
    feed_consumed = models.FloatField(
        help_text="Feed consumed (sacks)",
        default=0.0,
    )

    class Meta:
        ordering = ["day"]
        verbose_name_plural = "Stats"

    def __str__(self):
        return f"Day {self.day}: {self.harvested} harvested"

    def save(self, *args, **kwargs):
        # Auto-set day
        if self.day is None:
            last_stat = (
                type(self).objects.filter(flock=self.flock).order_by("-day").first()
            )
            self.day = (last_stat.day + 1) if last_stat else 1

        # Auto-calc percentage
        if self.flock.number_of_ducks > 0:
            self.percentage = (self.harvested / self.flock.number_of_ducks) * 100
        else:
            self.percentage = 0

        super().save(*args, **kwargs)

    def clean(self):
        validate_stats_entry(self)

    @property
    def previous(self):
        return (
            type(self)
            .objects.filter(
                flock=self.flock,
                date__lt=self.date,
            )
            .order_by("-date")
            .first()
        )

    @property
    def harvested_delta(self):
        prev = self.previous
        if not prev:
            return None
        return int(self.harvested) - int(prev.harvested)

    @property
    def harvested_delta_pct(self):
        prev = self.previous
        if not prev or prev.harvested == 0:
            return None
        return ((self.harvested - prev.harvested) / prev.harvested) * 100
