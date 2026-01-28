from django import template

from apps.ducks.constants import AGGREGATE_LABELS

register = template.Library()


@register.simple_tag
def agg_label(key):
    return AGGREGATE_LABELS.get(key, "")
