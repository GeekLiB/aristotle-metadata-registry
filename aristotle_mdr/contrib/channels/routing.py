from channels.routing import route, route_class, include
from haystack_channels.routing import channel_routing as haystack_routing


def module_route(mod_route):
    return route(mod_route, mod_route)


channel_routing = [
    module_route("aristotle_mdr.contrib.channels.concept_changes.concept_saved"),
    module_route("aristotle_mdr.contrib.channels.concept_changes.new_comment_created"),
    module_route("aristotle_mdr.contrib.channels.concept_changes.new_post_created"),
    include(haystack_routing)
]
