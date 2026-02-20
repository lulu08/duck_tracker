from import_export import fields
from import_export import resources

from config.settings.base import DATE_INPUT_FORMATS

from .models import Flock
from .models import Stats
from .widgets import MultiFormatDateWidget


class FlockResource(resources.ModelResource):
    class Meta:
        model = Flock
        fields = (
            "id",
            "title",
            "number_of_ducks",
            "started_date",
            "culled_date",
            "description",
        )


class StatsResource(resources.ModelResource):
    date = fields.Field(
        column_name="date",
        attribute="date",
        widget=MultiFormatDateWidget(formats=DATE_INPUT_FORMATS),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.flock = None
        self._day_counter = None

    # 🔹 inject FK BEFORE validation
    def init_instance(self, row=None):
        instance = super().init_instance(row)
        instance.flock = self.flock
        return instance

    def before_import(self, dataset, **kwargs):
        if not self.flock:
            msg = "Flock must be set on resource before import"
            raise ValueError(msg)

        last_day = (
            Stats.objects.filter(flock=self.flock)
            .order_by("-day")
            .values_list("day", flat=True)
            .first()
        )
        self._day_counter = (last_day or 0) + 1

    def before_import_row(self, row, **kwargs):
        self._set_day(row)

    def _set_day(self, row):
        row.pop("id", None)
        row.pop("flock", None)
        if not row.get("day"):
            row["day"] = self._day_counter
            self._day_counter += 1

    class Meta:
        model = Stats
        import_id_fields = ()
        fields = (
            "date",
            "harvested",
            "percentage",
            "mortality",
            "feed_consumed",
        )
        skip_unchanged = True
        use_transactions = True
        clean_model_instances = True
