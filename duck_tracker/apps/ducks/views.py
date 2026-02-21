from decimal import Decimal

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Avg
from django.db.models import FloatField
from django.db.models import IntegerField
from django.db.models import Max
from django.db.models import Min
from django.db.models import Sum
from django.db.models import Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.urls import reverse_lazy
from django.views import View
from django.views import generic
from import_export.exceptions import ImportError as ImportExportError
from import_export.forms import ExportForm
from tablib import Dataset
from tablib.core import UnsupportedFormat

from .formsets import EggProductionCostFormSet
from .formsets import EggTypeFormSet
from .formsets import ExpenseTypeFormSet
from .forms import FeedConsumedForm
from .forms import FlockForm
from .forms import FlockIncomeForm
from .forms import StatsForm
from .forms import FlockFilterForm
from .models import Flock
from .models import Stats
from .resources import StatsResource
from .utils import get_default_formats


class FlockListView(generic.ListView):
    model = Flock
    template_name = "ducks/flock_list.html"
    context_object_name = "flocks"
    form_class = FlockFilterForm

    def apply_filters(self, queryset):
        self.form = self.form_class(self.request.GET)
        if not self.form.is_valid():
            return queryset  # ignore invalid filters
        
        data = self.form.cleaned_data

        title = data.get("title")
        if title:
            queryset = queryset.filter(title__icontains=title)

        sort = data.get("sort")
        sort_fields = {
            "title_asc": "title",
            "title_desc": "-title",
            "started_date_asc": "started_date",
            "started_date_desc": "-started_date",
        }        
        if sort in sort_fields:
            queryset = queryset.order_by(sort_fields[sort])

        is_active = data.get("is_active")
        is_active_choices = {
            "active": True,
            "culled": False,
        }
        if is_active in is_active_choices:
            queryset = queryset.filter(
                culled_date__isnull=is_active_choices[is_active],
            )
        return queryset

    def get_queryset(self):
        queryset = super().get_queryset().prefetch_related("stats")
        return self.apply_filters(queryset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        days = int(self.request.GET.get("days", 30))
        context["days"] = days

        chart_data = []

        for flock in context["flocks"]:
            stats = flock.stats.filter(day__lte=days).order_by("day")

            chart_data.append(
                {
                    "label": flock.title,
                    "data": [s.percentage for s in stats],
                },
            )

        context["chart_data"] = chart_data
        context["chart_days"] = list(range(1, days + 1))
        context["form"] = self.form

        return context


class FlockDetailView(generic.DetailView):
    model = Flock
    template_name = "ducks/flock_detail.html"
    context_object_name = "flock"
    resource_class = StatsResource

    def apply_filters(self, queryset):
        """Apply any filtering based on GET parameters."""
        start_date = self.request.GET.get("start_date")
        end_date = self.request.GET.get("end_date")
        max_day = self.request.GET.get("day")
        sort = self.request.GET.get("sort")

        if start_date and end_date and end_date < start_date:
            end_date = None

        if start_date:
            queryset = queryset.filter(date__gte=start_date)
            # if filtering by start_date, ignore max_day
            max_day = None
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
            # if filtering by end_date, ignore max_day
            max_day = None
        if max_day and not start_date and not end_date:
            queryset = queryset.filter(day__lte=max_day)

        sort_fields = {
            "day_asc": "day",
            "day_desc": "-day",
        }
        if sort in sort_fields:
            queryset = queryset.order_by(sort_fields[sort])
        else:
            queryset = queryset.order_by("day", "id")

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        flock = context["flock"]

        base_qs = flock.stats.all().order_by("day", "id")
        stats_qs = self.apply_filters(base_qs)
        all_mortality_zero = not stats_qs.exclude(mortality=0).exists()
        all_feed_zero = not stats_qs.exclude(feed_consumed=0).exists()

        # --- Aggregates (FULL filtered queryset, not paginated) ---
        aggregates = stats_qs.aggregate(
            total_harvested=Coalesce(
                Sum("harvested"),
                Value(0),
                output_field=IntegerField(),
            ),
            avg_harvested=Coalesce(
                Avg("harvested"),
                Value(0.0),
                output_field=FloatField(),
            ),
            average_percentage=Coalesce(
                Avg("percentage"),
                Value(0.0),
                output_field=FloatField(),
            ),
            total_feed_consumed=Coalesce(
                Sum("feed_consumed"),
                Value(0),
                output_field=IntegerField(),
            ),
            avg_daily_feed_consumed=Coalesce(
                Avg("feed_consumed"),
                Value(0.0),
                output_field=FloatField(),
            ),
            total_mortality=Coalesce(
                Sum("mortality"),
                Value(0),
                output_field=IntegerField(),
            ),
        )

        # --- Pagination ---
        paginator = Paginator(stats_qs, 10)
        page_number = self.request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        date_bounds = base_qs.aggregate(
            min_date=Min("date"),
            max_date=Max("date"),
        )

        # Serialize for chart
        chart_data = list(
            stats_qs.values(
                "day",
                "date",
                "harvested",
                "percentage",
                "mortality",
                "feed_consumed",
            ),
        )

        context.update(
            {
                "all_mortality_zero": all_mortality_zero,
                "all_feed_zero": all_feed_zero,
                "flock": flock,
                "flock_stats_json": chart_data,  # for JS
                "context_stats": page_obj,  # optional
                "stats": page_obj.object_list,  # ✅ FIX
                "flock_stats": stats_qs,  # ✅ full queryset for charts
                "aggregates": aggregates,
                "has_date_filter": bool(
                    self.request.GET.get("start_date")
                    or self.request.GET.get("end_date"),
                ),
                "min_date": date_bounds["min_date"],
                "max_date": date_bounds["max_date"],
                "form": StatsForm(flock=flock),
                "export_form": self.get_export_form(),
            },
        )

        return context

    def get_export_form(self):
        return ExportForm(
            formats=get_default_formats(),
            resources=[self.resource_class()],
        )

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            page_obj = context["context_stats"]  # use the Page object

            html = render_to_string(
                "components/stats_rows.html",
                {
                    "stats": page_obj.object_list,  # ✅ FIX
                    "flock": context["flock"],
                },
                request=self.request,
            )

            return JsonResponse(
                {
                    "html": html,
                    "has_next": page_obj.has_next(),
                },
            )

        return super().render_to_response(context, **response_kwargs)


class FlockCreateUpdateView(generic.UpdateView):
    model = Flock
    form_class = FlockForm
    template_name = "ducks/flock_form.html"

    def get_object(self, queryset=None):
        self.creating = "pk" not in self.kwargs  # Creating if no pk in URL
        if self.creating:
            return None  # Create new instance
        return super().get_object(queryset)  # Update existing instance

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object:
            context["page_title"] = f"Update Flock: {self.object.title}"
        else:
            context["page_title"] = "Create New Flock"

        return context

    def get_success_url(self):
        return reverse("ducks:flock-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        self.object = form.save()
        title = self.object.title
        message = (
            f"Flock {title} created successfully."
            if self.creating
            else f"Flock {title} updated successfully."
        )
        messages.success(self.request, message)
        return redirect(
            self.get_success_url(),
        )  # Redirect to success URL


class FlockDeleteView(generic.DeleteView):
    model = Flock
    template_name = "ducks/flock_confirm_delete.html"
    success_url = "ducks:flock-list"

    def get_success_url(self):
        messages.success(
            self.request,
            f"Flock {self.object.title} deleted successfully.",
        )
        return reverse(self.success_url)


class StatsCreateUpdateView(generic.UpdateView):
    model = Stats
    form_class = StatsForm
    template_name = "ducks/stats_form.html"

    def get_form_kwargs(self):
        # Inject `flock` into the form kwargs so the form and model clean
        # methods can validate using the flock before the instance is saved.
        kwargs = super().get_form_kwargs()
        # Determine flock for create (GET/POST param) or update (instance)
        flock = None
        if getattr(self, "creating", False):
            flock_id = self.request.GET.get("flock") or self.request.POST.get("flock")
            if flock_id:
                flock = get_object_or_404(Flock, pk=flock_id)
        else:
            flock = getattr(self.object, "flock", None)

        if flock:
            kwargs["flock"] = flock

        return kwargs

    def get_object(self, queryset=None):
        self.creating = "pk" not in self.kwargs  # Creating if no pk in URL
        if self.creating:
            return None  # Create new instance
        return super().get_object(queryset)  # Update existing instance

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # allow flock to be provided via GET params (?flock=1)
        flock_id = self.request.GET.get("flock")
        flock = get_object_or_404(Flock, pk=flock_id)
        context["flock"] = flock
        if self.object:
            context["page_title"] = (
                f"Update Stats Entry: Date "
                f"{self.object.date.strftime('%b %d, %Y')} "
                f"for Flock {self.object.flock.title}"
            )
        else:
            context["page_title"] = f"Add Stats Entry for Flock {flock.title}"
            # ensure the form in the template is initialized with the flock
            context["form"] = self.get_form()

        # always ensure a form is available in context (bound to instance or flock)
        if "form" not in context:
            context["form"] = self.get_form()

        return context

    def get_success_url(self):
        # allow flock to be provided via GET params (?flock=1)
        flock_id = self.request.GET.get("flock")
        return reverse("ducks:flock-detail", kwargs={"pk": flock_id})

    def form_valid(self, form):
        # For create, accept flock via kwargs or GET param;
        # for update, object already has flock
        if getattr(self, "creating", False):
            flock_id = self.request.GET.get("flock") or self.request.POST.get("flock")
            if not flock_id:
                form.add_error(
                    None,
                    "No flock specified. Please provide a `flock` parameter.",
                )
                return self.form_invalid(form)
            flock = get_object_or_404(Flock, pk=flock_id)
            self.object = form.save(commit=False)
            # also prefer the form-provided flock if present
            self.object.flock = getattr(form, "flock", flock)
            self.object.save()
            messages.success(self.request, "Stats entry created successfully.")
            return redirect(self.get_success_url())

        # update existing stats
        self.object = form.save()
        messages.success(self.request, f"{self.object} updated successfully.")
        return redirect(self.get_success_url())


class StatsImportTemplateView(generic.TemplateView):
    template_name = "ducks/stats_import_template.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["flock"] = get_object_or_404(Flock, pk=self.kwargs["pk"])
        return context


class FlockStatsExportView(View):
    """
    Export only Stats for a given flock.
    """

    def apply_filters(self, queryset):
        """Apply any filtering based on GET parameters."""
        start_date = self.request.POST.get("start_date")
        end_date = self.request.POST.get("end_date")
        max_day = self.request.POST.get("day")
        sort = self.request.POST.get("sort")

        if start_date:
            queryset = queryset.filter(date__gte=start_date)
            # if filtering by start_date, ignore max_day
            max_day = None
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
            # if filtering by end_date, ignore max_day
            max_day = None
        if max_day and not start_date and not end_date:
            queryset = queryset.filter(day__lte=max_day)

        sort_fields = {
            "day_asc": "day",
            "day_desc": "-day",
        }
        if sort in sort_fields:
            queryset = queryset.order_by(sort_fields[sort]) 

        return queryset

    resource_class = StatsResource

    def post(self, request, pk):
        flock = get_object_or_404(Flock, pk=pk)
        stats_qs = Stats.objects.filter(flock=flock)
        stats_qs = self.apply_filters(stats_qs)

        # Validate export form
        export_form = ExportForm(
            formats=get_default_formats(),
            resources=[self.resource_class()],
            data=request.POST,
        )

        if not export_form.is_valid():
            messages.error(request, "Invalid export options.")
            return redirect("ducks:flock-detail", pk=pk)

        # Resolve selected format
        file_format = self.get_file_format(export_form)
        ext = file_format.get_extension()

        # Export stats only
        stats_dataset = StatsResource().export(stats_qs)
        export_data = file_format.export_data(stats_dataset)

        response = HttpResponse(
            export_data,
            content_type=file_format.get_content_type(),
        )
        response["Content-Disposition"] = (
            f'attachment; filename="flock_{flock.title}_stats.{ext}"'
        )
        return response

    @staticmethod
    def get_file_format(export_form):
        format_index = int(export_form.cleaned_data["format"])
        return get_default_formats()[format_index]()


class FlockStatsImportView(View):
    resource_class = StatsResource

    def post(self, request, pk):
        flock = get_object_or_404(Flock, pk=pk)

        file = request.FILES.get("file")

        if not file:
            messages.error(request, "Please select a CSV file.")
            return redirect("ducks:flock-detail", pk=flock.pk)

        # ❌ Hard-block non-CSV uploads
        if not file.name.lower().endswith(".csv"):
            messages.error(request, "Only CSV files are allowed.")
            return redirect("ducks:flock-detail", pk=flock.pk)

        dataset = Dataset()

        try:
            raw = file.read().decode("utf-8-sig")
            dataset.load(raw, format="csv")
        except (UnicodeDecodeError, UnsupportedFormat) as e:
            messages.error(request, f"Could not read CSV file: {e}")
            return redirect("ducks:stats-import-template", pk=flock.pk)

        resource = self.resource_class()
        resource.flock = flock  # REQUIRED

        result = resource.import_data(
            dataset,
            dry_run=True,
            raise_errors=False,
        )

        if result.has_errors():
            errors = [
                f"Row {row}: {err.error}"
                for row, row_errors in result.row_errors()
                for err in row_errors
            ]
            messages.error(
                request,
                "Import failed:\n" + "\n".join(errors[:5]),
            )
            return redirect("ducks:stats-import-template", pk=flock.pk)

        try:
            resource.import_data(
                dataset,
                dry_run=False,
                raise_errors=True,
            )
        except ImportExportError as e:
            # Run each row error through messages
            messages.error(request, f"Import failed: {e.args[0]}")

            return redirect("ducks:stats-import-template", pk=flock.pk)

        messages.success(request, "Stats imported successfully.")
        return redirect("ducks:flock-detail", pk=flock.pk)

class FlockIncomeCalculatorView(generic.FormView):
    template_name = "ducks/flock_income_calculator.html"
    form_class = FlockIncomeForm
    success_url = reverse_lazy("ducks:flock-income-calculator")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.POST:
            # Bind EggType, ExpenseType formset and Feed form to POST
            context["eggType_formset"] = EggTypeFormSet(self.request.POST, prefix="eggs")
            context["expense_formset"] = ExpenseTypeFormSet(
                self.request.POST,
                prefix="expenses",
            )
            context["production_cost_formset"] = EggProductionCostFormSet(
                self.request.POST,
                prefix="production-cost",
            )
            context["feed_form"] = FeedConsumedForm(self.request.POST, prefix="feed")
        else:
            # Pre-fill the first EggType row with "Good"
            initial_data = [{"name": "Good"}]
            context["eggType_formset"] = EggTypeFormSet(initial=initial_data, prefix="eggs")
            context["expense_formset"] = ExpenseTypeFormSet(prefix="expenses")
            context["production_cost_formset"] = EggProductionCostFormSet(
                prefix="production-cost",
            )
            context["feed_form"] = FeedConsumedForm(prefix="feed")

        return context

    def form_valid(self, form):
        context = self.get_context_data()
        eggType_formset = context["eggType_formset"]
        feed_form = context["feed_form"]
        expense_formset = context["expense_formset"]

        if (
            not eggType_formset.is_valid()
            or not feed_form.is_valid()
            or not expense_formset.is_valid()

        ):
            return self.form_invalid(form)

        flock_size = form.cleaned_data["flock_size"]
        production_percent = form.cleaned_data["production_percent"]
        total_eggs = flock_size * (production_percent / 100)

        # Egg type calculation
        breakdown = []
        total_income = 0
        percent_total = 0

        for egg_form in eggType_formset:
            if not egg_form.cleaned_data or egg_form.cleaned_data.get("DELETE"):
                continue

            name = egg_form.cleaned_data["name"]
            percent = egg_form.cleaned_data["percent"]
            price = egg_form.cleaned_data["price"]

            percent_total += percent
            eggs = total_eggs * (percent / 100)
            income = eggs * float(price)

            breakdown.append(
                {
                    "name": name,
                    "percent": percent,
                    "eggs": round(eggs, 2),
                    "price": price,
                    "income": round(income, 2),
                },
            )
            total_income += income

        # Expense Calculation
        expense_breakdown = []
        total_cost = 0
        for expense_form in expense_formset:
            if not expense_form.cleaned_data or expense_form.cleaned_data.get("DELETE"):
                continue

            name = expense_form.cleaned_data["name"]
            cost = expense_form.cleaned_data["cost"]

            total_cost += cost
            expense_breakdown.append(
                {
                    "name": name,
                    "cost": cost,
                },
            )

        # Feed calculation
        feed_qty = feed_form.cleaned_data["quantity_g"]
        feed_price = feed_form.cleaned_data["price_per_sack"]
        # first, take the overall feed consumed in grams by flock size
        feed_overall = feed_qty * flock_size
        # feed_qty is grams, convert first to kg
        feed_kg = feed_overall / 1000  # since there are 1000 grams in 1 kg
        # convert to sack (50 kg each)
        feed_sack = feed_kg / 50
        feed_cost = Decimal(feed_sack) * Decimal(feed_price)

        # Net income
        net_income = Decimal(total_income) - (Decimal(feed_cost) + Decimal(total_cost))

        # Production cost calculation
        # Get the price per kg by dividing it by the kg of a sack
        feed_price_per_kg = feed_price / 50
        # Get the price per g next
        feed_price_per_g = feed_price_per_kg / 1000
        # Last, multiply it by the quantity_g
        production_cost_feed = feed_price_per_g * Decimal(feed_qty)
        production_cost_expenses = Decimal(total_cost) / Decimal(total_eggs) if total_eggs > 0 else Decimal("0.00")

        egg_production_cost_breakdown = {
            "egg_production_cost_feed": production_cost_feed,
            "egg_production_cost_expenses": production_cost_expenses,
            "total_egg_production_cost": (
                production_cost_feed
                + production_cost_expenses
            )
        }



        context["result"] = {
            "total_eggs": round(total_eggs, 2),
            "breakdown": breakdown,
            "expense_breakdown": expense_breakdown,
            "total_income": round(total_income, 2),
            "percent_total": percent_total,
            "expenses_total": total_cost,
            "feed": {
                "quantity": feed_qty,
                "feed_sack": feed_sack,
                "price_per_sack": feed_price,
                "cost": round(feed_cost, 2),
            },
            "net_income": round(net_income, 2),
            "egg_production_cost": egg_production_cost_breakdown
        }

        return self.render_to_response(context)
