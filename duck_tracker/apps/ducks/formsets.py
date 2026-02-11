from .forms import (
    BaseEggTypeFormSet,
    EggTypeForm,
    ExpenseTypeForm,
    EggProductionCostForm,
)
from django import forms

EggTypeFormSet = forms.formset_factory(
    EggTypeForm,
    formset=BaseEggTypeFormSet,
    extra=1,
    can_delete=True,
)


ExpenseTypeFormSet = forms.formset_factory(
    ExpenseTypeForm,
    extra=1,
    can_delete=True,
)

EggProductionCostFormSet = forms.formset_factory(
    EggProductionCostForm,
    extra=1,
    can_delete=True,
)
