"""Gives every page the two cut off points, so no page has them typed in by hand."""
from . import scoring


def cutoffs(request):
    amber_from, red_from = scoring.thresholds()
    return {"amber_from": amber_from, "red_from": red_from, "amber_to": red_from - 1}
