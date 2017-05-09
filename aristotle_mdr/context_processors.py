from aristotle_mdr.utils import fetch_aristotle_settings
from aristotle_mdr.views.bulk_actions import get_bulk_actions


# This allows us to pass the Aristotle settings through to the final rendered page
def settings(request):
    return {
        "config": fetch_aristotle_settings(),
        'bulk_actions': get_bulk_actions(),
    }
