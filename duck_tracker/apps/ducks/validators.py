from django.core.exceptions import ValidationError
from django.db import models

from config.settings.base import DATE_FORMAT

# ==================================================
# FLOCK VALIDATORS
# ==================================================


def validate_flock_dates(flock):
    errors = {}

    _validate_culled_after_started(flock, errors)
    _validate_stats_against_flock_dates(flock, errors)
    _validate_flock_size(flock, errors)

    if errors:
        raise ValidationError(errors)


def _validate_culled_after_started(flock, errors):
    if flock.culled_date and flock.culled_date <= flock.started_date:
        errors["culled_date"] = (
            f"Culled date ({flock.culled_date.strftime(DATE_FORMAT)}) "
            f"cannot be before or equal to started date "
            f"({flock.started_date.strftime(DATE_FORMAT)})."
        )


def _validate_stats_against_flock_dates(flock, errors):
    if not flock.pk:
        return

    stats = flock.stats.all()

    if flock.culled_date and stats.filter(date__gt=flock.culled_date).exists():
        errors["culled_date"] = (
            f"Stats entries exist beyond the culled date "
            f"({flock.culled_date.strftime(DATE_FORMAT)})."
        )

    if stats.filter(date__lt=flock.started_date).exists():
        errors["started_date"] = (
            f"Stats entries exist before the started date "
            f"({flock.started_date.strftime(DATE_FORMAT)})."
        )
        
def _validate_flock_size(flock, errors):
    if not flock.pk:
        return
    
    stats = flock.stats.all()
    max_harvested = stats.aggregate(models.Max("harvested"))["harvested__max"] or 0 # TODO: harvested_max error
    if max_harvested > flock.number_of_ducks:
        errors["number_of_ducks"] = (
            f"The flock's number of ducks ({flock.number_of_ducks})"
            f" cannot be less than the maximum harvested value "
            f"({max_harvested}) recorded in its stats."
        )


# ==================================================
# STATS VALIDATORS
# ==================================================


def validate_stats_entry(stats):
    errors = {}

    if not stats.flock:
        return

    _validate_harvested(stats, errors)
    _validate_percentage_bounds(stats, errors)
    _validate_positive_fields(stats, errors)
    _validate_unique_date(stats, errors)
    _validate_date_bounds(stats, errors)
    _validate_date_immutability(stats, errors)
    _validate_date_gap(stats, errors)

    if errors:
        raise ValidationError(errors)


def _validate_harvested(stats, errors):
    if stats.harvested > stats.flock.number_of_ducks:
        errors.setdefault("harvested", []).append(
            f"Harvested ({stats.harvested}) cannot exceed "
            f"the flock's number of ducks "
            f"({stats.flock.number_of_ducks}).",
        )


def _validate_percentage_bounds(stats, errors):
    min_percentage = 0
    max_percentage = 100
    if stats.percentage < min_percentage or stats.percentage > max_percentage:
        errors.setdefault("percentage", []).append(
            f"Percentage ({stats.percentage}) "
            f"must be between {min_percentage} "
            f"and {max_percentage}.",
        )


def _validate_positive_fields(stats, errors):
    positive_fields = {
        "harvested": stats.harvested,
        "percentage": stats.percentage,
        "mortality": stats.mortality,
        "feed_consumed": stats.feed_consumed,
    }

    for field_name, value in positive_fields.items():
        if value < 0:
            errors.setdefault(field_name, []).append(
                f"{field_name.replace('_', ' ').capitalize()}"
                f"({value}) cannot be negative.",
            )


def _validate_unique_date(stats, errors):
    if not stats.date:
        return

    qs = type(stats).objects.filter(
        flock=stats.flock,
        date=stats.date,
    )

    if stats.pk:
        qs = qs.exclude(pk=stats.pk)

    if qs.exists():
        errors.setdefault("date", []).append(
            f"A stat entry for {stats.date.strftime(DATE_FORMAT)} "
            f"already exists for this flock.",
        )


def _validate_date_bounds(stats, errors):
    flock = stats.flock

    if stats.date < flock.started_date:
        errors.setdefault("date", []).append(
            f"Date ({stats.date.strftime(DATE_FORMAT)}) cannot be before "
            f"the flock's started date "
            f"({flock.started_date.strftime(DATE_FORMAT)}).",
        )

    if flock.culled_date and stats.date > flock.culled_date:
        errors.setdefault("date", []).append(
            f"This entry cannot be added because the flock ({flock}) has been culled.",
        )


def _validate_date_immutability(stats, errors):
    if not stats.pk:
        return

    original = type(stats).objects.get(pk=stats.pk)
    if stats.date != original.date:
        errors.setdefault("date", []).append(
            "Date cannot be changed on edit.",
        )


def _validate_date_gap(stats, errors):
    if stats.pk or not stats.date:
        return

    last_stat = type(stats).objects.filter(flock=stats.flock).order_by("-date").first()

    if not last_stat:
        return

    gap_days = (stats.date - last_stat.date).days
    if gap_days > 1:
        errors.setdefault("date", []).append(
            f"There is a gap of {gap_days - 1} day(s) after the last entry "
            f"on {last_stat.date.strftime(DATE_FORMAT)}. "
            "Please fill in missing dates before adding this entry.",
        )


# ==================================================
# Import Validators
# ==================================================


def validate_stats_import_row(row, flock):
    errors = {}

    _validate_import_date(row, flock, errors)
    _validate_import_harvested(row, flock, errors)
    _validate_import_percentage(row, errors)
    _validate_import_mortality(row, flock, errors)
    _validate_import_feed_consumed(row, errors)

    if errors:
        raise ValidationError(errors)


def _validate_import_date(row, flock, errors):
    import_date = row.get("date")
    if not import_date:
        return

    if import_date < flock.started_date:
        errors.setdefault("date", []).append(
            f"Date ({import_date.strftime(DATE_FORMAT)}) cannot be before "
            f"the flock's started date "
            f"({flock.started_date.strftime(DATE_FORMAT)}).",
        )

    if flock.culled_date and import_date > flock.culled_date:
        errors.setdefault("date", []).append(
            f"This entry cannot be added because the flock ({flock}) has been culled.",
        )

    if flock.stats.filter(date=import_date).exists():
        errors.setdefault("date", []).append(
            f"A stat entry for {import_date.strftime(DATE_FORMAT)} "
            f"already exists for this flock.",
        )


def _validate_import_harvested(row, flock, errors):
    harvested = row.get("harvested")
    if harvested is None:
        return

    if harvested > flock.number_of_ducks:
        errors.setdefault("harvested", []).append(
            f"Harvested ({harvested}) cannot exceed "
            f"the flock's number of ducks "
            f"({flock.number_of_ducks}).",
        )


def _validate_import_percentage(row, errors):
    percentage = row.get("percentage")
    if percentage is None:
        return

    min_percentage = 0
    max_percentage = 100
    if percentage < min_percentage or percentage > max_percentage:
        errors.setdefault("percentage", []).append(
            f"Percentage ({percentage}) "
            f"must be between {min_percentage} "
            f"and {max_percentage}.",
        )


def _validate_import_mortality(row, flock, errors):
    mortality = row.get("mortality")
    if mortality is None:
        return

    if mortality > flock.number_of_ducks:
        errors.setdefault("mortality", []).append(
            f"Mortality ({mortality}) cannot exceed "
            f"the flock's number of ducks "
            f"({flock.number_of_ducks}).",
        )

    if mortality < 0:
        errors.setdefault("mortality", []).append(
            f"Mortality ({mortality}) cannot be negative.",
        )


def _validate_import_feed_consumed(row, errors):
    feed_consumed = row.get("feed_consumed")
    if feed_consumed is None:
        return

    if feed_consumed < 0:
        errors.setdefault("feed_consumed", []).append(
            f"Feed consumed ({feed_consumed}) cannot be negative.",
        )
