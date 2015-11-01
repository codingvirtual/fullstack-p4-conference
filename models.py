#!/usr/bin/env python

"""models.py

Udacity conference server-side Python App Engine data & ProtoRPC models

$Id: models.py,v 1.1 2014/05/24 22:01:10 wesc Exp $

created/forked from conferences.py by wesc on 2014 may 24

"""

""" This file defines a number of data models that are essential in the overall
    "Object Relational Model" between Python (and JSON) objects and their
    counterparts as stored in Datastore. All inherit from Google's "ndb" class
    which provides the necessary functionality for Datastore operations such
    as puts, gets, etc.

    Each item stored in Datastore is represented as a "Kind" by Datastore.
    The Conference App has a number of key Kinds in its domain which include:
        Conference - the core Kind. It represents an instance of a conference
        Session - a "child" of a conference. It represents a particular
            "break-out" session during a conference. In theory, a conference
            should consist of 1 or more sessions. Together, all the sessions
            of a given conference make up the content of that conference.
        Speaker - each Session can have an associated Speaker.
        Profile - defines a User of the system. Only users can create
            conferences and sessions, though anyone can view them.

    Heirarchy:
        Profiles (users) are the top-level objects
        Conferences have a parent Profile (user). Profile is thus an ancestor
            to Conference.
        Sessions have a parent Conference. Conferences are thus ancestors to
            Sessions.
        Speakers are free-standing and do not have an ancestral heirarchy,
            though they are associated with specific sessions.

    In addition to a class defining the Kinds described above, there are
    related classes that define a form for that Kind. Forms are used as
    the mechanism for sending a Kind across the Internet and represent
    data as "form-encoded."

    You will also see a "plural" version ("Forms") for several Kinds. This
    is to allow more than one of that particular Kind to be transmitted in
    a single exchange. """

__author__ = 'wesc+api@google.com (Wesley Chun)'

import httplib
import endpoints
from protorpc import messages
from google.appengine.ext import ndb

class Session(ndb.Model):
    """Session Object - represents a specific session of a Conference"""
    sessionName     = ndb.StringProperty(required=True)
    highlights      = ndb.StringProperty()
    speaker         = ndb.StringProperty()
    duration        = ndb.IntegerProperty()
    typeOfSession   = ndb.StringProperty()
    date            = ndb.DateProperty()
    # For startTime, the assumption is made that any clients will pass
    # this to the API as a string formatted in military time such as
    # HH:MM where HH is 2 digits between 00 and 23 and MM is two digits
    # between 00 and 59.
    startTime       = ndb.TimeProperty()
    speakerKey      = ndb.StringProperty()


class SessionForm(messages.Message):
    """SessionForm -- create a Session"""
    sessionName     = messages.StringField(1)
    highlights      = messages.StringField(2)
    duration        = messages.IntegerField(4)
    typeOfSession   = messages.StringField(5)
    date            = messages.StringField(6)
    # For startTime, the assumption is made that any clients will pass
    # this to the API as a string formatted in military time such as
    # HH:MM where HH is 2 digits between 00 and 23 and MM is two digits
    # between 00 and 59.
    startTime       = messages.StringField(7)
    conferenceKey   = messages.StringField(8)
    speakerKey      = messages.StringField(9)

class SessionForms(messages.Message):
    """SessionForms -- multiple Session outbound form message"""
    items = messages.MessageField(SessionForm, 1, repeated=True)

class SessionQueryForm(messages.Message):
    field = messages.StringField(1)
    operator = messages.StringField(2)
    value = messages.StringField(3)

class SessionQueryForms(messages.Message):
    filters = messages.MessageField(SessionQueryForm, 1, repeated=True)

class SpeakerForm(messages.Message):
    """SpeakerForm -- Speaker outbound form message"""
    displayName = messages.StringField(1)
    profileKey = messages.StringField(2)
    biography = messages.StringField(3)
    websafeKey = messages.StringField(4)

class Speaker(ndb.Model):
    """Speaker -- Speaker object"""
    displayName = ndb.StringProperty(required=True)
    biography = ndb.StringProperty()

class SpeakerForms(messages.Message):
    """SpeakerForm -- multiple Speaker outbound form message"""
    items = messages.MessageField(SpeakerForm, 1, repeated=True)

class ConflictException(endpoints.ServiceException):
    """ConflictException -- exception mapped to HTTP 409 response"""
    http_status = httplib.CONFLICT

class Profile(ndb.Model):
    """Profile -- User profile object"""
    displayName = ndb.StringProperty()
    mainEmail = ndb.StringProperty()
    teeShirtSize = ndb.StringProperty(default='NOT_SPECIFIED')
    conferenceKeysToAttend = ndb.StringProperty(repeated=True)
    sessionKeysWishList = ndb.StringProperty(repeated=True)

class ProfileMiniForm(messages.Message):
    """ProfileMiniForm -- update Profile form message"""
    displayName = messages.StringField(1)
    teeShirtSize = messages.EnumField('TeeShirtSize', 2)

class ProfileForm(messages.Message):
    """ProfileForm -- Profile outbound form message"""
    displayName = messages.StringField(1)
    mainEmail = messages.StringField(2)
    teeShirtSize = messages.EnumField('TeeShirtSize', 3)
    conferenceKeysToAttend = messages.StringField(4, repeated=True)

class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    data = messages.StringField(1, required=True)

class BooleanMessage(messages.Message):
    """BooleanMessage-- outbound Boolean value message"""
    data = messages.BooleanField(1)

class Conference(ndb.Model):
    """Conference -- Conference object"""
    name                = ndb.StringProperty(required=True)
    description         = ndb.StringProperty()
    organizerUserId     = ndb.StringProperty()
    topics              = ndb.StringProperty(repeated=True)
    city                = ndb.StringProperty()
    startDate           = ndb.DateProperty()
    month               = ndb.IntegerProperty()
    endDate             = ndb.DateProperty()
    maxAttendees        = ndb.IntegerProperty()
    seatsAvailable      = ndb.IntegerProperty()

class ConferenceForm(messages.Message):
    """ConferenceForm -- Conference outbound form message"""
    name            = messages.StringField(1)
    description     = messages.StringField(2)
    organizerUserId = messages.StringField(3)
    topics          = messages.StringField(4, repeated=True)
    city            = messages.StringField(5)
    startDate       = messages.StringField(6) #DateTimeField()
    month           = messages.IntegerField(7)
    maxAttendees    = messages.IntegerField(8)
    seatsAvailable  = messages.IntegerField(9)
    endDate         = messages.StringField(10) #DateTimeField()
    websafeKey      = messages.StringField(11)
    organizerDisplayName = messages.StringField(12)

class ConferenceForms(messages.Message):
    """ConferenceForms -- multiple Conference outbound form message"""
    items = messages.MessageField(ConferenceForm, 1, repeated=True)

class TeeShirtSize(messages.Enum):
    """TeeShirtSize -- t-shirt size enumeration value"""
    NOT_SPECIFIED = 1
    XS_M = 2
    XS_W = 3
    S_M = 4
    S_W = 5
    M_M = 6
    M_W = 7
    L_M = 8
    L_W = 9
    XL_M = 10
    XL_W = 11
    XXL_M = 12
    XXL_W = 13
    XXXL_M = 14
    XXXL_W = 15

class ConferenceQueryForm(messages.Message):
    """ConferenceQueryForm -- Conference query inbound form message"""
    field = messages.StringField(1)
    operator = messages.StringField(2)
    value = messages.StringField(3)

class ConferenceQueryForms(messages.Message):
    """ConferenceQueryForms -- multiple ConferenceQueryForm inbound form message"""
    filters = messages.MessageField(ConferenceQueryForm, 1, repeated=True)

