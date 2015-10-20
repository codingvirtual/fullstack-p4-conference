__author__ = 'Greg'

from protorpc import messages
from protorpc import message_types
from models import *

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

DEFAULTS = {
    "city": "Default City",
    "maxAttendees": 0,
    "seatsAvailable": 0,
    "topics": [ "Default", "Topic" ]
}

SESSION_DEFAULTS = {
    "speaker": "Unknown",
    "duration": 60,
    "typeOfSession": "Keynote",
}

OPERATORS = {
    'EQ':   '=',
    'GT':   '>',
    'GTEQ': '>=',
    'LT':   '<',
    'LTEQ': '<=',
    'NE':   '!='
}

FIELDS =    {
    'CITY': 'city',
    'TOPIC': 'topics',
    'MONTH': 'month',
    'MAX_ATTENDEES': 'maxAttendees',
}

CONF_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeConferenceKey=messages.StringField(1),
)

CONF_POST_REQUEST = endpoints.ResourceContainer(
    ConferenceForm,
    websafeConferenceKey=messages.StringField(1),
)

SESSIONS_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    conferenceKey=messages.StringField(1),
    sessionKey=messages.StringField(2)
)

SESSIONS_POST_REQUEST = endpoints.ResourceContainer(
    SessionForm,
    conferenceKey=messages.StringField(1),
)

WISHLIST_POST_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    sessionKey=messages.StringField(1, required=True),
)

SPEAKER_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    speaker=messages.StringField(1, required=True),
)

QUERY_POST_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    startTime=messages.StringField(1),
    typeOfSession=messages.StringField(2),
)
SESSION_BY_CONF_POST_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    conferenceKey=messages.StringField(1),
)

SESSION_BY_TYPE_POST_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    conferenceKey=messages.StringField(1),
    typeOfSession=messages.StringField(2),
)

SESSION_BY_SPEAKER_POST_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    speaker=messages.StringField(1),
)