from django.contrib import admin

from .models import Flock
from .models import Stats


@admin.register(Flock)
class FlockAdmin(admin.ModelAdmin):
    list_display = ("title", "number_of_ducks", "started_date", "culled_date")
    search_fields = ("title",)
    list_filter = ("started_date", "culled_date")


@admin.register(Stats)
class StatsAdmin(admin.ModelAdmin):
    list_display = (
        "flock",
        "day",
        "date",
        "harvested",
        "percentage",
        "mortality",
        "feed_consumed",
    )
    search_fields = ("flock__title",)
    list_filter = ("date",)
    ordering = ("flock", "day")
