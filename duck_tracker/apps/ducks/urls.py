from django.urls import path

from .views import FlockCreateUpdateView
from .views import FlockDeleteView
from .views import FlockDetailView
from .views import FlockListView
from .views import FlockStatsExportView
from .views import FlockStatsImportView
from .views import StatsCreateUpdateView
from .views import StatsImportTemplateView
from .views import FlockIncomeCalculatorView

app_name = "ducks"
urlpatterns = [
    path("", FlockListView.as_view(), name="flock-list"),
    path("flock/<int:pk>/", FlockDetailView.as_view(), name="flock-detail"),
    path("flock/add/", FlockCreateUpdateView.as_view(), name="flock-add"),
    path("flock/<int:pk>/edit/", FlockCreateUpdateView.as_view(), name="flock-edit"),
    path("delete/<int:pk>/", FlockDeleteView.as_view(), name="flock-delete"),
    path("stats/add/", StatsCreateUpdateView.as_view(), name="stats-add"),
    path("stats/<int:pk>/edit/", StatsCreateUpdateView.as_view(), name="stats-edit"),
    path(
        "flocks/<int:pk>/export/",
        FlockStatsExportView.as_view(),
        name="flock-export",
    ),
    path(
        "flocks/<int:pk>/import/",
        FlockStatsImportView.as_view(),
        name="flock-import",
    ),
    path(
        "flocks/<int:pk>/import/template/",
        StatsImportTemplateView.as_view(),
        name="stats-import-template",
    ),
    path(
        "flocks/income-calculator/",
        FlockIncomeCalculatorView.as_view(),
        name="income-calculator",
    ),
]