from datetime import datetime

from import_export.widgets import Widget


class MultiFormatDateWidget(Widget):
    def __init__(self, formats=None):
        self.formats = formats or ["%Y-%m-%d"]

    def clean(self, value, row=None, *args, **kwargs):
        if not value:
            return None
        for fmt in self.formats:
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        msg = f"Date '{value}' does not match any of the formats: {self.formats}"
        raise ValueError(msg)

    def render(self, value, obj=None):
        if value:
            # Always output in first format for export
            return value.strftime(self.formats[0])
        return ""
