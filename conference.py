#!/usr/bin/env python

"""
conference.py -- Udacity conference server-side Python App Engine API;
    uses Google Cloud Endpoints

$Id: conference.py,v 1.25 2014/05/24 23:42:19 wesc Exp wesc $

Originally created by wesc on 2014 apr 21
Modified for Udacity class by Greg Palen, October 2015

"""

__author__ = 'wesc+api@google.com (Wesley Chun)'

"""

    This file represents the core functionality of the Conference API.
    Internal "private" methods are all prefixed with an underscore ( _ )
    to clarify their use.

    For each exposed method/endpoint, an annotation describes the request
    container expected, the response container to be returned, the path,
    the Endpoint name, and the HTTP method.

    settings.py contains relevant key informations such as client and api keys.

"""

from datetime import datetime

from collections import Counter

import endpoints
from protorpc import messages
from protorpc import message_types
from protorpc import remote

from google.appengine.api import memcache
from google.appengine.api import taskqueue
from google.appengine.ext import ndb

from constants import *
from models import *

from settings import WEB_CLIENT_ID
from settings import ANDROID_CLIENT_ID
from settings import IOS_CLIENT_ID
from settings import ANDROID_AUDIENCE

from utils import getUserId

EMAIL_SCOPE = endpoints.EMAIL_SCOPE
API_EXPLORER_CLIENT_ID = endpoints.API_EXPLORER_CLIENT_ID
MEMCACHE_ANNOUNCEMENTS_KEY = "RECENT_ANNOUNCEMENTS"
MEMCACHE_SPEAKER_KEY = "FEATURED_SPEAKER"
ANNOUNCEMENT_TPL = ('Last chance to attend! The following conferences '
                    'are nearly sold out: %s')


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

""" Overall API definition required by Cloud Endpoints. """
@endpoints.api(name='conference', version='v1', audiences=[ANDROID_AUDIENCE],
               allowed_client_ids=[WEB_CLIENT_ID,
                                   API_EXPLORER_CLIENT_ID,
                                   ANDROID_CLIENT_ID,
                                   IOS_CLIENT_ID],
               scopes=[EMAIL_SCOPE])

class ConferenceApi(remote.Service):
    """ Conference API to facilitate creating and managing Conferences
        and the Sessions and Speakers associated with them. """
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    @endpoints.method(SESSIONS_POST_REQUEST, SessionForm,
                      path='createSession/{conferenceKey}',
                      name='createSession',
                      http_method='POST')
    def createSession (self, request):
        """ Create new Session for a specific Conference. Provide the
            'websafe' ConferenceKey in the parameter. Returns the newly created
            Session object
        """
        return self._createSessionObject(request)

    def _createSessionObject (self, request):
        """ This method requires a logged-in user. First, get the user
            and throw an error if there is no authorized user. """
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        # Next, validate that a name for the session was passed in
        if not request.sessionName:
            raise endpoints.BadRequestException(
                "Session name is required")

        conf = ndb.Key(urlsafe=request.conferenceKey)

        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % request.conferenceKey)

        if conf.parent() != ndb.Key(Profile, getUserId(user)):
            raise endpoints.ForbiddenException(
                'You must be the conference organizer to be able to create'
                'sessions for this conference.'
            )

        # copy SessionForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name)
                for field in request.all_fields()}
        del data['conferenceKey']

        # convert date from strings to Date objects
        if data['date']:
            data['date'] = datetime.strptime(data['date'][:10],
                                             "%Y-%m-%d").date()

        if data['startTime']:
            data['startTime'] = datetime.strptime(
                data['startTime'], "%H:%M").time()

        # generate Conf Key
        wsck = request.conferenceKey
        conf_key = ndb.Key(urlsafe=wsck)

        # get the conference entity
        conf = conf_key.get()

        # if not found, raise an error and abort
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % wsck)

        # create a unique session ID
        s_id = Session.allocate_ids(size=1, parent=conf_key)[0]

        # create a key from the ID and save it to the dictionary
        s_key = ndb.Key(Session, s_id, parent=conf_key)
        data['key'] = s_key

        # create Session & save to Datastore
        sess = Session(**data)
        sess.put()

        """ add a task to the background queue that will determine if the
            Speaker for this Session should be the Featured Speaker.
            NOTE: if there is no Speaker defined for this Session, do not
            call the task. The endpoint for this is at
            /tasks/set_featured_speaker """
        if data['speakerKey']:
            taskqueue.add(params=
                      {'c_key': wsck}, url='/tasks/set_featured_speaker')
        return self._copySessionToForm(s_key.get())

    @endpoints.method(SESSIONS_GET_REQUEST, SessionForms,
                      path='getConferenceSessions/{conferenceKey}',
                      http_method='GET', name='getConferenceSessions')
    def getConferenceSessions (self, request):
        """ Returns all Sessions associated with a particular Conference.
            Provide the websafe ConferenceKey for the Conference to retrieve
            sessions for as the parameter to the request.
        """
        wsck = request.conferenceKey
        conf_key = ndb.Key(urlsafe=wsck)
        confSessions = Session.query(ancestor=conf_key)
        return SessionForms(
            items=[self._copySessionToForm(sess)
                   for sess in confSessions]
        )

    @endpoints.method(SESSION_BY_TYPE_POST_REQUEST, SessionForms,
                      path='session/{conferenceKey}/{typeOfSession}',
                      http_method='POST', name='getConferenceSessionsByType')
    def getConferenceSessionsByType (self, request):
        """ Returns a list of Sessions for a given Conference.
            Provide the conferenceKey parameter to specify which Conference
            you want Sessions for, and specify the type of Session desired
            ('Class', 'Workshop,' etc.) using the typeOfSession parameter."""

        """ first, build the key to the conference based  on the websafe key
            that was in the request """
        c_key = ndb.Key(urlsafe=request.conferenceKey)

        """ retrieve the conference. If not found, raise an
            exception and quit """
        if not c_key.get():
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % request.conferenceKey)

        """ now find all child sessions for this conference with
            ancestor query that will find all sessions with the selected
            conference as a parent """
        sessions = Session.query(ancestor=c_key) \
            .filter(Session.typeOfSession == request.typeOfSession)

        # return result(s)
        return SessionForms(
            items=[self._copySessionToForm(sess) for sess in sessions]
        )

    """ Utility method to copy a given Session object to a SessionForm response
        container. This method is called multiple times for queries that return
        multiple sessions. The calling method is responsible for aggregating
        the individual Sessions this method returns into a SessonForms (plural)
        response object """
    def _copySessionToForm (self, sess):
        sf = SessionForm()
        for field in sf.all_fields():
            if hasattr(sess, field.name):
                # convert Date to date string; just copy others
                if field.name.endswith('date'):
                    setattr(sf, field.name, str(getattr(sess, field.name)))
                elif field.name == 'startTime':
                    setattr(sf, field.name, str(getattr(sess, field.name)))
                else:
                    setattr(sf, field.name, getattr(sess, field.name))
            if field.name == 'sessionKey':
                setattr(sf, field.name, sess.key.urlsafe())
        sf.check_initialized()
        return sf



    @endpoints.method(SESSION_BY_SPEAKER_POST_REQUEST, SessionForms,
                      path='session_by_speaker/{speaker}', http_method='POST',
                      name='getSessionsBySpeaker')
    def getSessionsBySpeaker (self, request):
        """ Returns all Sessions that a particular Speaker is speaking at.
            Provide the websafe key for the Speaker in the request parameter.
        """
        sessions = Session.query(Session.speakerKey == request.speakerKey)

        return SessionForms(
            items=[self._copySessionToForm(sess) for sess in sessions]
        )

    @endpoints.method(SessionQueryForms, SessionForms,
                      path='querySessions', http_method='POST',
                      name='querySessions')
    def querySessions (self, request):
        """ Returns all Sessions that match the filters specified in the
            SessionQueryForms POST body. See source code for details on
            how to construct and use the filters. """
        sessions = self._sessionQueryFactory(request)

        return SessionForms(
            items=[self._copySessionToForm(sess) for sess in sessions]
        )

    @endpoints.method(WISHLIST_REQUEST, BooleanMessage,
                      path='wishlist', http_method='POST',
                      name='addSessionToWishlist')
    def addSessionToWishlist (self, request):
        """ Adds a particular Session of a Conference to the current user's
            'wishlist' of Sessions (which is part of their Profile).
            In the request body, provide the websafe Session Key for
            the Session to attach to the Wishlist. A Session can only
            be added once (no duplicates allowed). """
        return self._addSessionToWishlist(request)

    def _addSessionToWishlist (self, request):
        # adds a session to a the current user's wish list
        result = None

        # get the user's profile
        prof = self._getProfileFromUser()

        # get the key for the session that will be added to the wishlist
        wssk = request.sessionKey

        # retrieve the session from Datastore
        sess = ndb.Key(urlsafe=wssk).get()

        """ if we get no results on the session query, throw an exception.
            Otherwise, check to see if the session is already in the wish-
            list and if it is, throw an error preventing a duplicate entry """
        if not sess:
            raise endpoints.NotFoundException(
                'No Session found with key: %s' % wssk)
        if wssk in prof.sessionKeysWishList:
            raise ConflictException(
                "You have already added for this session")

        """ If we get here, all is good, so add the session to the user's
            wish list, which is part of their profile """
        prof.sessionKeysWishList.append(wssk)
        result = True

        # Save the profile back to Datastore
        prof.put()

        return BooleanMessage(data=result)

    @endpoints.method(WISHLIST_REQUEST, BooleanMessage,
                      path='wishlist',
                      http_method='DELETE', name='removeSessionFromWishlist')
    def removeSessionFromWishlist (self, request):
        """ Removes a specific Session from the current user's wishlist of
        Sessions. Specify which session to remove by providing the websafe
        Session Key in the request body. """
        return self._removeSessionFromWishlist(request)

    def _removeSessionFromWishlist (self, request):
        """ Takes a session in the request body and if present in the user's
            wish list, removes it. """
        result = None

        # get the user's profile which contains the wishlist
        prof = self._getProfileFromUser()

        """ Now use the websafe key in the request to find and load the
            session the user wants to remove """
        wssk = request.sessionKey
        sess = ndb.Key(urlsafe=wssk).get()

        """ If the session was not found, or if the session was not in the
            user's wishlist already, return an error """
        if not sess:
            raise endpoints.NotFoundException(
                'No Session found with key: %s' % wssk)
        if wssk in prof.sessionKeysWishList:
            prof.sessionKeysWishlist.remove(wssk)
            result = True
        else:
            result = False

        """ If we get to this point, all is good. Now safe the updated
            profile """
        prof.put()
        return BooleanMessage(data=result)

    @endpoints.method(message_types.VoidMessage, SessionForms,
                      http_method='POST', name='getSessionsInWishlist')
    def getSessionsInWishlist (self, request):
        """ Returns a the current user's wishlist of sessions. """
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        prof = self._getProfileFromUser()

        # Now get the session keys in their wishlist
        sessions = prof.sessionKeysWishList

        # return the collection of sessions
        return SessionForms(
            items=[self._copySessionToForm(ndb.Key(urlsafe=session).get())
                   for session in sessions]
        )

    def _sessionQueryFactory (self, request):
        # Return formatted session query from the submitted filters
        q = Session.query()
        inequality_filter, filters = self._formatFilters(request.filters)

        # If exists, sort on inequality filter first
        if not inequality_filter:
            q = q.order(Session.name)
        else:
            q = q.order(ndb.GenericProperty(inequality_filter))
            q = q.order(Session.name)

        for filtr in filters:
            if filtr["field"] in ["duration", "startTime"]:
                filtr["value"] = int(filtr["value"])
            formatted_query = ndb.query.FilterNode(filtr["field"],
                                                   filtr["operator"],
                                                   filtr["value"])
            q = q.filter(formatted_query)
        return q

    """
        The following method satisfies:
            Requirement 4.2: Come up with 2 additional queries

        This method searches for sessions based on a combination of both
        the session time and the session type. Both the time and the type
        are contained in the body of the POST request.

        The endpoint will return all sessions that match the type of the
        request AND occur BEFORE the time specified in the request.
    """
    @endpoints.method(QUERY_POST_REQUEST, SessionForms,
                      path='sessionsByTypeLessThanTime',
                      http_method='POST',
                      name='sessionsByTypeLessThanTime')
    def sessionsByTypeLessThanTime (self, request):
        """ Returns all Sessions (spanning all Conferences) that are of a
            specified type and that occur strictly before a specified time
            (strictly meaning NOT "at or before," but just "before").
            In the POST request body, the typeOfSession field should be
            set to the type of session to search for (e.g. 'workshop,'
            'lecture,' etc.) and the startTime field should contain a
            properly formatted Time string ('HH:MM' in 24 hour format).
        """
        """ startTime is stored as a string and is in 24-hour HH:MM format
            so a less-than search will yield the correct results.
            For this to work, a query with a subsequent filter is needed.
            First, all sessions (regardless of which conference they are part
            of) will be queried to find the subset of sessions that match the
            type defined by the request. From there, that query will be
            filtered to contain only those sessions that start strictly
            before the time specified in the request (meaning NOT "at or
            before," but purely before. So if the request startTime is 19:00:00
            then a session starting at exactly that time will NOT be returned.

            First build a query for all sessions that match the session type in
            the request and sort it by typeOfSession """
        matchingSessions = Session.query(
            Session.typeOfSession == request.typeOfSession).filter(
            Session.startTime < datetime.strptime(
                request.startTime, "%H:%M").time()
        )

        """ Now copy the matching sessions into the SessionForms and return
            them """
        return SessionForms(
            items=[self._copySessionToForm(sess)
                   for sess in matchingSessions]
        )

    """
        The following method satisfies:
            Requirement 4.2: Come up with 2 additional queries
            Requirement 4.4: Student proposes one or more solutions to the
                problematic query

        This method searches for sessions based on a combination of both
        the session time and the session type. Both the time and the type
        are contained in the body of the POST request.

        The endpoint will return all sessions that DO NOT match the session
        type specified in the request and that occur BEFORE the start time
        specified in the request.
    """
    @endpoints.method(QUERY_POST_REQUEST, SessionForms,
                      path='queryProblem',
                      http_method='POST',
                      name='queryProblem')
    def queryProblem (self, request):
        """ Returns all Sessions (across all Conferences) that do NOT match
            the specified typeOfSession and that DO occur strictly before
            (not "at or before") the specified startTime.\n

            typeOfSession is a string that identifies the specific type
            of session to EXCLUDE from the search (e.g. 'workshop,' or
            'lecture').\n

            startTime is a string in proper Time format (HH:MM) specified
            using 24 hour time. """

        """ First, start by getting all of the sessions that do NOT match
            the type specified in the query. Then, iterate over the results
            and build a new list that contains only those sessions that start
            before the specified time.

            First build a query for all sessions that do not match the session
            type in the request """
        sessionsByType = Session.query(
            Session.typeOfSession != request.typeOfSession)

        """ Using the sessions that were retrieved by the query above, set up
            a new list to contain only those sessions that start before the
            specified startTime and then iterate over the query results,
            appending only those sessions that start before the time specified
            in the request """
        matchingSessions = []
        for sess in sessionsByType:
            """ make sure that there is a valid startTime and that the
                starTime is less than the specified time """
            if sess.startTime and (sess.startTime < datetime.strptime(
                    request.startTime, "%H:%M").time()):
                matchingSessions.append(sess)

        """ Now copy the matching sessions into the SessionForms and return
            them """
        return SessionForms(
            items=[self._copySessionToForm(sess)
                   for sess in matchingSessions]
        )

# - - - Speaker objects - - - - - - - - - - - - - - - - -

    @endpoints.method(SpeakerForm, SpeakerForm, path='speaker',
                      http_method='POST', name='addSpeaker')
    def addSpeaker (self, request):
        # Create a new speaker
        return self._createSpeakerObject(request)

    def _createSpeakerObject (self, request):
        """ Creates a new Speaker in the system and returns the newly created
            Speaker object as evidence of success. """
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        """ If we got here, the user is authorized. Now confirm that they
            have a Display Name set in their profile """
        if not request.displayName:
            raise endpoints.BadRequestException(
                "Speaker 'displayName' field required")

        # Set up a dictionary containing the speaker object fields
        data = {field.name: getattr(request, field.name)
                for field in request.all_fields()}

        # don't use the websafekey - it's not part of the speaker
        del data['websafeKey']

        # generate a unique ID as a key for this speaker
        sp_id = Speaker.allocate_ids(size=1)[0]
        sp_key = ndb.Key(Speaker, sp_id)

        # now save the new key to the dictionary
        data['key'] = sp_key
        del data['profileKey']

        """ create the Speaker object, passing in the dictionary to the
            constructor. The returned object will be the new Speaker object
            with the relevant fields filled in. """
        sp = Speaker(**data)

        # Save the speaker to Datastore
        sp.put()
        return self._copySpeakerToForm(sp)

    def _copySpeakerToForm (self, speaker):
        # Copy relevant fields from Speaker to SpeakerForm
        sf = SpeakerForm()
        for field in sf.all_fields():
            if hasattr(speaker, field.name):
                setattr(sf, field.name, getattr(speaker, field.name))
            elif field.name == "websafeKey":
                setattr(sf, field.name, speaker.key.urlsafe())
        sf.check_initialized()
        return sf

    @endpoints.method(GET_FEATURED_SPEAKER_REQUEST, FeaturedSpeakerData,
                      path='getFeaturedSpeaker/{conf_key}',
                      http_method='GET', name='getFeaturedSpeaker')
    def getFeaturedSpeaker (self, request):
        """ Returns information about the Featured Speaker for a particular
            Conference. In the request, specify the Conference for which
            the Featured Speaker information is desired.\n

            If a Featured Speaker is set for the specified Conference, this
            will return a FeaturedSpeakerData object that contains a field
            for the Speaker key (uniquely identifies the Speaker in the system)
            and a list of Session Names that the Speaker is speaking at.\n

            THe "Featured Speaker" is defined as the Speaker at a Conference
            who is speaking at the most Sessions. If there are multiple
            Speakers that are "tied" for the most Sessions, an arbitrary
            Speaker is chosen from the Speakers in the tie.\n

             See _setFeaturedSpeaker() in the source code for more details."""
        featuredSpeakerMessage = memcache.get(
            MEMCACHE_SPEAKER_KEY + request.conf_key)
        return FeaturedSpeakerData(
            speakerKey=featuredSpeakerMessage['key'],
            items=[self._copySpeakerSessionToForm(sess)
                   for sess in featuredSpeakerMessage['sessionName']])


    def _copySpeakerSessionToForm (self, sess):
        sf = FeaturedSpeakerSession()
        # Copy relevant fields from Speaker to SpeakerForm
        sf.sessionName = sess
        sf.check_initialized()
        return sf

    @endpoints.method(message_types.VoidMessage, SpeakerForms,
                      path='speakers',
                      http_method='GET', name='getAllSpeakers')
    def getAllSpeakers (self, request):
        """ Returns a list of all the Speakers that are in the system. """
        speakers = Speaker.query()
        return SpeakerForms(items=[self._copySpeakerToForm(speaker)
                                   for speaker in speakers])

# - - - Conference objects - - - - - - - - - - - - - - - - -
    def _copyConferenceToForm (self, conf, displayName):
        # Copy relevant fields from Conference to ConferenceForm.
        cf = ConferenceForm()
        for field in cf.all_fields():
            if hasattr(conf, field.name):
                """ convert Date to date string; just copy others """
                if field.name.endswith('Date'):
                    setattr(cf, field.name, str(getattr(conf, field.name)))
                else:
                    setattr(cf, field.name, getattr(conf, field.name))
            elif field.name == "websafeKey":
                setattr(cf, field.name, conf.key.urlsafe())
        if displayName:
            setattr(cf, 'organizerDisplayName', displayName)
        cf.check_initialized()
        return cf

    def _createConferenceObject (self, request):
        """ Create or update Conference object,
            returning ConferenceForm/request."""

        """ Check that there is a currently logged-in user (authorized) and
            if not, raise an exception. """
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        """ The 'name' field of the Conference object is a required field.
            Here, we check to make sure that the data passed in does include
            a filled-in name field. Raise an exception if it's blank. """
        if not request.name:
            raise endpoints.BadRequestException(
                "Conference 'name' field required")

        # copy ConferenceForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name)
                for field in request.all_fields()}
        del data['websafeKey']
        del data['organizerDisplayName']

        """ add default values for those missing
            (both data model & outbound Message) """
        for df in DEFAULTS:
            if data[df] in (None, []):
                data[df] = DEFAULTS[df]
                setattr(request, df, DEFAULTS[df])

        """ convert dates from strings to Date objects;
             set month based on start_date """
        if data['startDate']:
            data['startDate'] = datetime.strptime(data['startDate'][:10],
                                                  "%Y-%m-%d").date()
            data['month'] = data['startDate'].month
        else:
            data['month'] = 0
        if data['endDate']:
            data['endDate'] = datetime.strptime(data['endDate'][:10],
                                                "%Y-%m-%d").date()

        # set seatsAvailable to be same as maxAttendees on creation
        if data["maxAttendees"] > 0:
            data["seatsAvailable"] = data["maxAttendees"]

        # get Profile Key based on user ID
        p_key = ndb.Key(Profile, user_id)

        """ generate a unique conference ID with the profile
            as the ancestor """
        c_id = Conference.allocate_ids(size=1, parent=p_key)[0]

        # generate the conference key with the ancestor profile
        c_key = ndb.Key(Conference, c_id, parent=p_key)

        # store the key and the organizer ID in the dictionary
        data['key'] = c_key
        data['organizerUserId'] = request.organizerUserId = user_id

        # Save the Conference to Datastore
        Conference(**data).put()

        """ Now send email to organizer confirming
            creation of Conference & return (modified) ConferenceForm """
        taskqueue.add(params={'email': user.email(),
                              'conferenceInfo': repr(request)},
                      url='/tasks/send_confirmation_email'
                      )
        return request

    @ndb.transactional()
    def _updateConferenceObject (self, request):
        # This method updates an existing conference
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        # update existing conference
        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()

        # check that conference exists
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' %
                request.websafeConferenceKey)

        # check that user is owner
        if user_id != conf.organizerUserId:
            raise endpoints.ForbiddenException(
                'Only the owner can update the conference.')

        """ Not getting all the fields, so don't create a new object; just
            copy relevant fields from ConferenceForm to Conference object """
        for field in request.all_fields():
            data = getattr(request, field.name)
            # only copy fields where we get data
            if data not in (None, []):
                # special handling for dates (convert string to Date)
                if field.name in ('startDate', 'endDate'):
                    data = datetime.strptime(data, "%Y-%m-%d").date()
                    if field.name == 'startDate':
                        conf.month = data.month
                # write to Conference object
                setattr(conf, field.name, data)

        # save Conference to Datastore
        conf.put()
        prof = ndb.Key(Profile, user_id).get()
        return self._copyConferenceToForm(conf, getattr(prof, 'displayName'))

    @endpoints.method(ConferenceForm, ConferenceForm,
                      path='conference', http_method='POST',
                      name='createConference')
    def createConference (self, request):
        """ Create a new Conference in the system. """
        return self._createConferenceObject(request)

    @endpoints.method(CONF_POST_REQUEST, ConferenceForm,
                      path='conference/{websafeConferenceKey}',
                      http_method='PUT', name='updateConference')
    def updateConference (self, request):
        """ Updates an existing Conference (as identified by the
            websafeConferenceKey parameter) with the data provided in the
            request body. Returns the udpated Conference object. """
        return self._updateConferenceObject(request)

    @endpoints.method(CONF_GET_REQUEST, ConferenceForm,
                      path='conference/{websafeConferenceKey}',
                      http_method='GET', name='getConference')
    def getConference (self, request):
        """ Returns the Conference object identified by the
            websafeConferenceKey parameter or an exception if the specified
            Conference key does not exist. """
        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' %
                request.websafeConferenceKey)
        prof = conf.key.parent().get()

        # return ConferenceForm
        return self._copyConferenceToForm(conf, getattr(prof, 'displayName'))

    @endpoints.method(message_types.VoidMessage, ConferenceForms,
                      path='getConferencesCreated',
                      http_method='POST', name='getConferencesCreated')
    def getConferencesCreated (self, request):
        """ Return a list of all Conferences that the current user has
            created/organized. """
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        # create ancestor query for all key matches for this user#
        confs = Conference.query(ancestor=ndb.Key(Profile, user_id))
        prof = ndb.Key(Profile, user_id).get()

        # return set of ConferenceForm objects per Conference
        return ConferenceForms(
            items=[self._copyConferenceToForm(
                conf, getattr(prof, 'displayName')) for conf in confs]
        )

    def _getQuery (self, request):
        # Return formatted query from the submitted filters
        q = Conference.query()
        inequality_filter, filters = self._formatFilters(request.filters)

        # If exists, sort on inequality filter first
        if not inequality_filter:
            q = q.order(Conference.name)
        else:
            q = q.order(ndb.GenericProperty(inequality_filter))
            q = q.order(Conference.name)

        for filtr in filters:
            if filtr["field"] in ["month", "maxAttendees"]:
                filtr["value"] = int(filtr["value"])
            formatted_query = ndb.query.FilterNode(
                filtr["field"], filtr["operator"], filtr["value"])
            q = q.filter(formatted_query)
        return q

    def _formatFilters (self, filters):
        # Parse, check validity and format user supplied filters
        formatted_filters = []
        inequality_field = None

        """ loop through the filters that were provided and make sure that
            each in the dictionary is actually a valid filter identifier.
            See Constants.py for the list of defined filters """
        for f in filters:
            filtr = {field.name: getattr(f, field.name)
                     for field in f.all_fields()}

            try:
                filtr["field"] = FIELDS[filtr["field"]]
                filtr["operator"] = OPERATORS[filtr["operator"]]
            except KeyError:
                raise endpoints.BadRequestException(
                    "Filter contains invalid field or operator.")

            # Every operation except "=" is an inequality
            if filtr["operator"] != "=":
                """ check  if inequality op has been used in previous filters
                    disallow filter if inequality was performed
                        on different field before
                    track the field on which the inequality
                      operation is performed """
                if inequality_field and inequality_field != filtr["field"]:
                    raise endpoints.BadRequestException(
                        "Inequality filter is allowed on only one field.")
                else:
                    inequality_field = filtr["field"]

            formatted_filters.append(filtr)
        return (inequality_field, formatted_filters)

    @endpoints.method(ConferenceQueryForms, ConferenceForms,
                      path='queryConferences', http_method='POST',
                      name='queryConferences')
    def queryConferences (self, request):
        """ Returns a list of Conferences that satisfy the query specifications
            provided by the request body. See the source code for specifics
            on how to specify the query terms. """
        conferences = self._getQuery(request)

        """ need to fetch organiser displayName from profiles.
            Get all keys and use get_multi for speed """
        organisers = [(ndb.Key(Profile, conf.organizerUserId))
                      for conf in conferences]
        profiles = ndb.get_multi(organisers)

        # put display names in a dict for easier fetching
        names = {}
        for profile in profiles:
            names[profile.key.id()] = profile.displayName

        # copy conference objects to form that can return multiple confs
        return ConferenceForms(
            items=[self._copyConferenceToForm(
                conf, names[conf.organizerUserId])
                   for conf in conferences]
        )

# - - - Profile objects - - - - - - - - - - - - - - - - - - -

    def _copyProfileToForm (self, prof):
        """ Copy relevant fields from Profile to ProfileForm.
            Create a new, blank profile form to populate """
        pf = ProfileForm()
        for field in pf.all_fields():
            """ loop through the fields of the form and populate them with
                data from the request """
            if hasattr(prof, field.name):
                # convert t-shirt string to Enum; just copy others
                if field.name == 'teeShirtSize':
                    setattr(pf, field.name, getattr(
                        TeeShirtSize, getattr(prof, field.name)))
                else:
                    setattr(pf, field.name, getattr(prof, field.name))
        pf.check_initialized()
        return pf

    def _getProfileFromUser (self):
        """ Return user Profile from datastore,
            creating new one if non-existent.
            Verify a logged-in user (auth) and return an error if not """
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        # get the user's Profile based on their user ID
        user_id = getUserId(user)
        p_key = ndb.Key(Profile, user_id)
        profile = p_key.get()

        # create new Profile if one was not retrieved by the above query
        if not profile:
            profile = Profile(
                key=p_key,
                displayName=user.nickname(),
                mainEmail=user.email(),
                teeShirtSize=str(TeeShirtSize.NOT_SPECIFIED),
            )
            profile.put()

        # return the profile fully populated
        return profile

    def _doProfile (self, save_request=None):
        """ Get user Profile and return to user, possibly updating it first.
            Get user Profile """
        prof = self._getProfileFromUser()

        """ if this request is to save an udpated profile, then store the
            user-modifiable data into the existing fields and then save
            the profile back to Datastore """
        if save_request:
            for field in ('displayName', 'teeShirtSize'):
                if hasattr(save_request, field):
                    val = getattr(save_request, field)
                    if val:
                        setattr(prof, field, str(val))
            prof.put()

        # return ProfileForm
        return self._copyProfileToForm(prof)

    @endpoints.method(message_types.VoidMessage, ProfileForm,
                      path='profile', http_method='GET', name='getProfile')
    def getProfile (self, request):
        """ Returns the Profile of the current user. """
        return self._doProfile()

    @endpoints.method(ProfileMiniForm, ProfileForm,
                      path='profile', http_method='POST', name='saveProfile')
    def saveProfile (self, request):
        """ Updates the Profile of the current user with the data provided
            in the request body. """
        return self._doProfile(request)

# - - - Announcements - - - - - - - - - - - - - - - - - - - -

    @staticmethod
    def _cacheAnnouncement ():
        """ Create Announcement & assign to memcache; used by
            memcache cron job & putAnnouncement().
        """
        confs = Conference.query(ndb.AND(
            Conference.seatsAvailable <= 5,
            Conference.seatsAvailable > 0)
        ).fetch(projection=[Conference.name])

        if confs:
            """ If there are almost sold out conferences,
                format announcement and set it in memcache """
            announcement = ANNOUNCEMENT_TPL % (
                ', '.join(conf.name for conf in confs))
            memcache.set(MEMCACHE_ANNOUNCEMENTS_KEY, announcement)
        else:
            """ If there are no sold out conferences,
                delete the memcache announcements entry """
            announcement = ""
            memcache.delete(MEMCACHE_ANNOUNCEMENTS_KEY)

        return announcement

    @staticmethod
    def _setFeaturedSpeaker(self, request):
        """
            For the purposes of this project, there will be only one Featured
            Speaker for each conference. The Featured Speaker will be the
            speaker who has the MOST speaking sessions at this conference.

            This was a conscious design decision to define Featured Speaker
            more "robustly" than the project requirements. I chose to do this
            in order to learn how to create and return more sophisticated
            Message objects (in this case, one that contained a string and
            a list that had to be built up).
        """

        # Create a key based on the c_key parameter passed in.
        c_key = ndb.Key(urlsafe=request.get('c_key'))

        # Limit the projection to minimize data transfer - only need 2 fields.
        qo = ndb.QueryOptions(projection=['speakerKey', 'sessionName'])

        # Construct the query - all Sessions for the specified Conference
        q = Session.query(ancestor=c_key)

        # Perform the query
        results = q.fetch(options=qo)

        # Set up a few variables to hold the processed results

        """ speakerSummary will contain a list of Speaker keys. If a Speaker
            is speaking at more than one Session, their key will appear
            in the list once for every Session they are speaking at. This
            fact will be used to count their "appearances" later. """
        speakerSummary = []

        """ sessions will contain a list of tuples that each contain the key
            for the Speakera and the name of the Session they are speaking
            at. This list will be used later to extract the session names
            for whichever Speaker is determined to be the Featured Speaker."""
        sessions = []
        featuredMessage = {}

        # the 'key' element will hold the websafe key for the Speaker object
        featuredMessage['key'] = ""

        """ The 'sessionName' list will contain a list of the Session names
            that this Speaker is speaking at """
        featuredMessage['sessionName'] = []

        """ To determine the Featured Speaker, an intermediate data object is
            needed as there is no query-based way to do a summarized count
            by Speaker. With traditional SQL, one could use a group-by
            constraint combined with a count() method in the query to retrieve
            these same results very easily. Datastore's "GQL" language does
            not support this type of query, so it has to be derived
            programatically. The overall approach is to retrieve all Sessions
            for a particular Conference then iterate over the results and
            build up an interim data structure that has a single "row" for
            each Speaker that contains their websafe key and a count of how
            many Sessions they are speaking at. From there, the Speaker
            with the highest count can be easily extracted and the Memcache
            entry defined accordingly. """

        # Iterate over results and build a set of lists for later processing
        for row in results:
            # Update the two lists if there is a Speaker associated
            if row.speakerKey is not None:
                speakerSummary.append(row.speakerKey)
                sessions.append(row)

        """ The Counter class takes the speakerSummary list and creates a tuple
            for each Speaker. The tuple consists of the Speaker's key as the
              first element and the count of how many times that key appeared
              in the speakerSummary list as the 2nd data element. """
        summary = Counter(speakerSummary)

        """ this method is a utility method that returns the count which will
            be the 2nd element of the tuple. The Counter class is responsible
             for creating these tuples. """
        def get_count(tuple):
            return tuple[1]

        """ This creates the summary list object by taking the summary object
            that Counter created above and sorting it in reverse order (so
            the Speaker with the MOST entries will be 1st in the list). A
            key/value pair is created where the key is the count and the
            value is the Speaker key associated with that count. """
        sortedSummary = sorted(summary.items(), key=get_count, reverse=True)

        """ Make sure there are ANY Speakers for the Conference. If so, grab
            the first one and make them the Featured Speaker. """
        if sortedSummary:
            featuredSpeakerKey = sortedSummary[0][0]
        else:
            featuredSpeakerKey = None

        """ If a Featured Speaker was found, build up a Memcache entry that
            contains the Speaker's key and a list of Session names for the
            Sessions they are speaking at. """
        if featuredSpeakerKey:
            featuredMessage['key'] = featuredSpeakerKey
            for session in sessions:
                if session.speakerKey == featuredSpeakerKey:
                    featuredMessage['sessionName'].append(session.sessionName)

            """ The Memcache key consists of the string constant and the
                websafe key for the Conference this relates to. The value
                of the entry is the featuredMessage object that is built up
                in the code block directly above. """
            memcache.set(MEMCACHE_SPEAKER_KEY + c_key.urlsafe(),
                         featuredMessage)

        # If there was no featured Speaker, clear out any Memcache entry.
        else:
            # No featured speakers in the system, so clear the MemCache
            memcache.delete(MEMCACHE_SPEAKER_KEY + c_key.urlsafe())
        return

    @endpoints.method(
        message_types.VoidMessage, StringMessage,
        path='conference/announcement/get', http_method='GET',
        name='getAnnouncement')
    def getAnnouncement (self, request):
            """ Return any current Announcement from Memcache. If there is
                no Announcement present, return an empty string. """
            return StringMessage(data=memcache.get(
                MEMCACHE_ANNOUNCEMENTS_KEY) or "")

    # - - - Registration - - - - - - - - - - - - - - - - - - - -

    @ndb.transactional(xg=True)
    def _conferenceRegistration (self, request, reg=True):
        """ Register or unregister user for selected Conference. Will throw
            an exception if the specified Conference does not exist. Will
            also throw an exception if the user is trying to register for a
            Conferene they have already registered for or if the Conference
            has no remaining seats available. Will also throw an exception if
            trying to unregister from a Conference that the user is not
            presently registered for. """
        retval = None

        # get the Profile from the logged-in user
        prof = self._getProfileFromUser()

        """ check if conf exists with provided websafeConfKey and throw
            an exception if the conference is not in Datastore """
        wsck = request.websafeConferenceKey
        conf = ndb.Key(urlsafe=wsck).get()
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % wsck)

        # start the registration if that's what this request is for
        if reg:
            # check if user already registered otherwise add
            if wsck in prof.conferenceKeysToAttend:
                raise ConflictException(
                    "You have already registered for this conference")

            # check if seats avail and raise exception if none left
            if conf.seatsAvailable <= 0:
                raise ConflictException(
                    "There are no seats available.")

            # register user, take away one seat
            prof.conferenceKeysToAttend.append(wsck)
            conf.seatsAvailable -= 1
            retval = True

        else:  # not a register request, so must be unregister.
            # First confirm user already registered
            if wsck in prof.conferenceKeysToAttend:

                # unregister user, add back one seat
                prof.conferenceKeysToAttend.remove(wsck)
                conf.seatsAvailable += 1
                retval = True
            else:
                retval = False

        # write things back to the datastore & return
        prof.put()
        conf.put()
        return BooleanMessage(data=retval)

    @endpoints.method(message_types.VoidMessage, ConferenceForms,
                      path='conferences/attending',
                      http_method='GET', name='getConferencesToAttend')
    def getConferencesToAttend (self, request):
        """ Return list of Conferences the current user is registered for. """

        """ First, get user's profile and then use that to build a query for
            all descendant conferences (which represent the conferences the
            user has registered for) """
        prof = self._getProfileFromUser()
        conf_keys = [ndb.Key(urlsafe=wsck)
                     for wsck in prof.conferenceKeysToAttend]
        conferences = ndb.get_multi(conf_keys)

        # get organizers of the above conferences
        organisers = [ndb.Key(Profile, conf.organizerUserId)
                      for conf in conferences]
        profiles = ndb.get_multi(organisers)

        # put display names in a dict for easier fetching
        names = {}
        for profile in profiles:
            names[profile.key.id()] = profile.displayName

        # return set of ConferenceForm objects per Conference
        return ConferenceForms(items=[self._copyConferenceToForm(
            conf, names[conf.organizerUserId])
                                      for conf in conferences])

    @endpoints.method(CONF_GET_REQUEST, BooleanMessage,
                      path='conference/{websafeConferenceKey}',
                      http_method='POST', name='registerForConference')
    def registerForConference (self, request):
        """ Register the current user for the Conference specified in the
            websafeConferenceKey parameter assuming there are still seats
            available for that Conference and the user isn't already registered
            for that Conference (both will throw exceptions). """
        return self._conferenceRegistration(request)

    @endpoints.method(CONF_GET_REQUEST, BooleanMessage,
                      path='conference/{websafeConferenceKey}',
                      http_method='DELETE', name='unregisterFromConference')
    def unregisterFromConference (self, request):
        """ Unregisters the current user from the Conference specified in the
            websafeConferenceKey parameter assuming they are presently
            registered for that Conference (throws exception if the user is
            not presently registered for that Conference). """
        return self._conferenceRegistration(request, reg=False)

    @endpoints.method(message_types.VoidMessage, ConferenceForms,
                      path='filterPlayground',
                      http_method='GET', name='filterPlayground')
    def filterPlayground (self, request):
        """ Filter Playground - a section used for testing various filters
            to validate the result set obtained """
        q = Conference.query()
        # field = "city"
        # operator = "="
        # value = "London"
        # f = ndb.query.FilterNode(field, operator, value)
        # q = q.filter(f)
        q = q.filter(Conference.city == "London")
        q = q.filter(Conference.topics == "Medical Innovations")
        q = q.filter(Conference.month == 6)

        return ConferenceForms(
            items=[self._copyConferenceToForm(conf, "") for conf in q]
        )

# register API
api = endpoints.api_server([ConferenceApi])
