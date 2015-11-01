__author__ = 'Greg'

from protorpc import messages
from protorpc import message_types
from models import *

""" - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - """

""" Default values for a new conference. Used only if the user creating
    the conference doesn't supply values for a given field and only fields
    left empty pick up the default (in other words, if the user supplies
    a value for one of the fields below, but not the others, the one they
    supplied a value for will retain that value and only the others that
    were left empty will inherit the default values)"""
DEFAULTS = {
    "city": "Default City",
    "maxAttendees": 0,
    "seatsAvailable": 0,
    "topics": [ "Default", "Topic" ]
}

""" As above, defaults for a new session when there are fields left empty"""
SESSION_DEFAULTS = {
    "speaker": "Unknown",
    "duration": 60,
    "typeOfSession": "Keynote",
}

""" Comparison operators used for filter and query operations"""
OPERATORS = {
    'EQ':   '=',
    'GT':   '>',
    'GTEQ': '>=',
    'LT':   '<',
    'LTEQ': '<=',
    'NE':   '!='
}

""" Fields present for a conference """
FIELDS =    {
    'CITY': 'city',
    'TOPIC': 'topics',
    'MONTH': 'month',
    'MAX_ATTENDEES': 'maxAttendees',
}

""" The following list of elements each define a specific request or response
    container that is specific to a particular Model in the overall data
    scheme. A "websafe" key is a key that has been URL-encoded to preserve
    integrity of the key for transmission across the web. Google code
    can use this websafe key to get back to the "real" key in order to
    access Datastore """
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

WISHLIST_REQUEST = endpoints.ResourceContainer(
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

GET_FEATURED_SPEAKER_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    conf_key=messages.StringField(1, required=True)
)