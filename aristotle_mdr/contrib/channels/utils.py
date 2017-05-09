from channels import Channel
from django.conf import settings


def fire(channel, obj=None, **kwargs):
    from django.utils.module_loading import import_string
    message = kwargs
    if hasattr(settings, 'CHANNEL_LAYERS'):
        message.update({
            '__object___': {
                'pk': instance.pk,
                'app_label': instance._meta.app_label,
                'model_name': instance._meta.model_name,
            }
        })
        c = Channel("aristotle_mdr.contrib.channels.%s" % channel).send(message)
    else:
        message.update({'__object__': {'object': obj}})
        import_string("aristotle_mdr.contrib.channels.%s" % channel)(message)


def safe_object(message):
    __object__ = message['__object__']
    if __object__.get('object', None):
        instance = __object__['object']
    else:
        model = apps.get_model(__object__['app_label'], __object__['model_name'])
        instance = model.objects.filter(pk=__object__['pk']).first()
    return instance
