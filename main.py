#!/usr/bin/env python

"""
main.py -- Udacity conference server-side Python App Engine
    HTTP controller handlers for memcache & task queue access

$Id$

created by wesc on 2014 may 24

"""

__author__ = 'wesc+api@google.com (Wesley Chun)'

import webapp2
from google.appengine.api import app_identity
from google.appengine.api import mail
from conference import ConferenceApi

class SetAnnouncementHandler(webapp2.RequestHandler):
    def get(self):
        """Set Announcement in Memcache."""
        ConferenceApi._cacheAnnouncement()
        self.response.set_status(204)


class SendConfirmationEmailHandler(webapp2.RequestHandler):
    def post(self):
        """Send email confirming Conference creation."""
        mail.send_mail(
            'noreply@%s.appspotmail.com' % (
                app_identity.get_application_id()),     # from
            self.request.get('email'),                  # to
            'You created a new Conference!',            # subj
            'Hi, you have created a following '         # body
            'conference:\r\n\r\n%s' % self.request.get(
                'conferenceInfo')
        )

class SetFeaturedSpeakerHandler(webapp2.RequestHandler):
    def post(self):
        """ Sets the Featured Speaker list. Featured Speaker is defined as any
            Speakers that are speaking in 2 or more Sessions of a given
            Conference. The list of Featured Speakers is stored in
             MemCache for fast retrieval """
        c_key = ndb.Key(urlsafe=self.request.get('c_key'))
        confSessions = Session.query(ancestor=c_key)

        """ get all speakers """
        speakers = Speaker.query()
        speakers = speakers.order(Speaker.name)

        """ create empty list of featured speakers """
        feat_spk_keys = []

        """ check for every speaker """
        for speaker in speakers:
            count = 0
            for session in confSessions:
                for conference_speaker_key in session.speakers:
                    if speaker.key == conference_speaker_key:
                        count += 1

            """ if in more than one session, feature this speaker """
            if count > 1:
                """ attach the speaker key to the list of featured speakers """
                feat_spk_keys.append(conference_speaker_key)

        """ set memcache key to the urlsafe key of the conference. """
        MEMCACHE_CONFERENCE_KEY = "Featured:%s" % c_key.urlsafe()

        """ If there are featured speakers at the conference """
        if feat_spk_keys:

            """ Build the list of featured speakers """
            count = 0
            featured = "Feature speakers"
            for spk_key in feat_spk_keys:
                count += 1
                featured += " Featured %s: %s SESSIONS: " % (
                    count, spk_key.get().name)
                featuredSessions = confSessions.filter(
                    Session.speakers == spk_key)
                featured += ", ".join(sess.name for sess in featuredSessions)

            """ set the list into MemCache """
            memcache.set(MEMCACHE_CONFERENCE_KEY, featured)

        else:
            """ No featured speakers in the system, so clear the MemCache """
            memcache.delete(MEMCACHE_CONFERENCE_KEY)

app = webapp2.WSGIApplication([
    ('/crons/set_announcement', SetAnnouncementHandler),
    ('/tasks/send_confirmation_email', SendConfirmationEmailHandler),
    ('/tasks/set_featured_speaker', SetFeaturedSpeakerHandler),
], debug=True)