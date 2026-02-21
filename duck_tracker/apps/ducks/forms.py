from django import forms

from config.settings.base import DATE_INPUT_FORMATS
from ckeditor.widgets import CKEditorWidget

from .models import Flock
from .models import Stats


class FlockForm(forms.ModelForm):
    class Meta:
        model = Flock
        fields = [
            "title",
            "number_of_ducks",
            "description",
            "started_date",
            "culled_date",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Flock name"},
            ),
            "number_of_ducks": forms.NumberInput(
                attrs={"class": "form-control", "min": "1"},
            ),
            "description": CKEditorWidget(),
            "started_date": forms.DateInput(
                attrs={"class": "form-control date-input", "type": "date"},
            ),
            "culled_date": forms.DateInput(
                attrs={"class": "form-control date-input", "type": "date"},
            ),
        }


class StatsForm(forms.ModelForm):
    def __init__(self, *args, flock=None, **kwargs):
        """Accept an optional `flock` kwarg and don't forward it to the base.

        Django's generic views will pass `**get_form_kwargs()` to the form
        constructor; if we inject `flock` there we must accept it here and
        avoid passing it to the base `ModelForm.__init__` which doesn't know
        about that argument.
        """
        super().__init__(*args, **kwargs)
        # Prefer an explicit flock argument; fall back to the instance's flock
        self.flock = flock or getattr(self.instance, "flock", None)

        if self.instance.pk:
            self.fields["date"].disabled = True  # ✅ disable instead of delete
            self.fields["date"].widget = forms.HiddenInput()

    class Meta:
        model = Stats
        fields = ["date", "harvested", "notes", "mortality", "feed_consumed"]
        widgets = {
            "date": forms.DateInput(attrs={"class": "form-control date-input", "type": "date"}),
            "harvested": forms.NumberInput(
                attrs={"class": "form-control", "type": "number", "min": "0"},
            ),
            "mortality": forms.NumberInput(
                attrs={"class": "form-control", "type": "number", "min": "0"},
            ),
            "feed_consumed": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "type": "number",
                    "min": "0",
                    "step": "0.1",
                },
            ),
            "notes": CKEditorWidget(),
        }

    def clean(self):
        cleaned = super().clean()

        # Ensure the instance has the flock set so model-level validation can run
        if self.flock:
            self.instance.flock = self.flock

        return cleaned

class FlockFilterForm(forms.Form):
    SORT_CHOICES = [
        ("title_asc", "Name (A-Z)"),
        ("title_desc", "Name (Z-A)"),
        ("started_date_asc", "Start Date (Oldest)"),
        ("started_date_desc", "Start Date (Newest)"),
    ]

    SORT_IS_ACTIVE_CHOICES = [
        ("", "All"),
        ("active", "Active"),
        ("culled", "Culled"),
    ]
    
    sort = forms.ChoiceField(
        required=False,
        label="Sort By",
        choices=SORT_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    title = forms.CharField(
        required=False,
        label="Flock Name",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Search by name"}),
    )
    is_active = forms.ChoiceField(
        required=False,
        label="Status",
        choices=SORT_IS_ACTIVE_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

class FlockIncomeForm(forms.Form):
    flock_size = forms.IntegerField(
        min_value=1,
        label="Flock Size",
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    production_percent = forms.FloatField(
        min_value=0,
        max_value=100,
        label="Egg Production (%)",
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )


class EggTypeForm(forms.Form):
    name = forms.CharField(
        label="Egg Type",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    percent = forms.FloatField(
        min_value=0,
        max_value=100,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control egg-percent",
                "step": "0.01",
            },
        ),
    )

    price = forms.DecimalField(
        min_value=0,
        decimal_places=2,
        label="Price per Egg",
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )


class BaseEggTypeFormSet(forms.BaseFormSet):
    def clean(self):
        super().clean()

        total = 0
        max_pct = 100
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue
            total += form.cleaned_data.get("percent", 0)

        if total > max_pct:
            msg = "Total egg type percentage cannot exceed 100%."
            raise forms.ValidationError(
                msg,
            )


class ExpenseTypeForm(forms.Form):
    name = forms.CharField(
        label="Expense Type",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    cost = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control expense-cost",
            },
        ),
    )


class EggProductionCostForm(forms.Form):
    name = forms.CharField(
        label="Feed Type",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    quantity_g = forms.FloatField(
        min_value=0,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        label="Quantity (g)",
    )

    price_per_sack = forms.DecimalField(
        min_value=0,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        label="Price per sack",
    )


class FeedConsumedForm(forms.Form):
    quantity_g = forms.FloatField(
        min_value=0,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        label="Quantity (g)",
    )
    price_per_sack = forms.DecimalField(
        min_value=0,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        label="Price per sack",
    )
