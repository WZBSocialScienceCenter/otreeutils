from channels.routing import route_class

from otree.channels.routing import channel_routing

from .channels_consumers import ExportDataChannelsExtension

# exclude oTree's original ExportData consumer
channel_routing = [route for route in channel_routing if route.consumer.__name__ != 'ExportData']

# add extension
channel_routing.append(route_class(
    ExportDataChannelsExtension,
    path=r"^/export/$")
)
