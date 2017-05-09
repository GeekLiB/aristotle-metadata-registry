CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "asgi_redis.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("localhost", 6379)],
        },
        "ROUTING": "aristotle_mdr.contrib.channels.routing.channel_routing",
    },
}

HAYSTACK_SIGNAL_PROCESSOR = 'aristotle_mdr.contrib.channels.signals.AristotleChannelsSignalProcessor'
