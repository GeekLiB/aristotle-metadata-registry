from django.apps import apps
from django.conf import settings
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.http import JsonResponse

from aristotle_mdr.models import _concept


def heartbeat(request):
    service_status = {
        "aristotle": get_version(),
        "webserver": check_web(),
        "database": check_db(),
        "cache": check_cache(),
        # "channels":check_channels()
    }
    if any(True for v in service_status.values() if 'error' in v.keys()):
        status_code = 500
    else:
        status_code = 200
    service_status.update(status_code=status_code)
    return JsonResponse(service_status, status=status_code)


def get_version():
    from aristotle_mdr import __version__
    return {
        'version': __version__
    }


def check_web():
    # If the webserver is dead this won't even run
    return {
        'status': 'ok',
    }


def check_db():
    try:
        obj = _concept.objects.all().first()
        return {
            'status': 'ok',
        }
    except Exception as e:
        return {
            'status': 'notok',
            'error': str(e)
        }


def check_cache():
    from django.core.cache import cache
    try:
        key, val = 'hb', 'wubba lubba dub-dub'  # The sound of a heart beat
        cache.set(key, val, 30)
        assert cache.get(key) == val, "Key mismatch"
        return {
            'status': 'ok',
        }
    except Exception as e:
        return {
            'status': 'notok',
            'error': str(e)
        }
