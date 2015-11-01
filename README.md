# Full Stack Nanodegree Project 4 - Conference App

## Table of Contents
1.  Project Overview
2.  Requirements
3.  Satisfaction of Requirements Discussion
4.  Running the Code
5.  Credits

## 1 - Project Overview
This project is the 4th in a series of projects associated with the Udacity
Full Stack Nanodegree program. In this particular project, students are
provided with a fully-functioning client/server application for organizing
conferences and events. The client side includes a web client as well as
an Android client. On the server side, all code is developed in Python and
leverages Google App Engine as the server host. In addition to basing on
App Engine, data persistence is provided through the Google Cloud Datastore
API and user authentication is handled via OAuth2 (Google Login in this
case).

The student's objective is to extend the original provided server-side code
to enhance the overall functionality of the project. In the originally
provided code, a User could create and manage a Conference and could also
register and unregister for a Conference. The extended capability the student
is to add to the server is support for:

- Allow Conferences to have Sessions
- Sessions can be added or deleted
- Sessions have Speakers
- Users can have a Wishlist of Sessions
- Leverage App Engine Task Queues and Memcache to provide Featured Speaker
    notices.

Students are only required to implement the back-end server-side Python code
to enable this functionality, which will be tested using the Google API
Explorer.

## 2 - Requirements

There are two levels of requirements described in this section. In the first
part, the requirements for actually using the code are outlined. In the second
part, the requirements for the Project itself are outlined so that the reader
can appreciate the code base and the rationale behind it.

##### -- Requirements to Run The Code

In order to load and run this code, several requirements must be met:
 - You must have a Google account
 - You must create a new project in the Google Developer's Console
 - You must copy and paste the API keys you will create into the code so that
    it will run on App Engine.
 - You need the development tools as well as the Google Cloud Python SDK
    in order to test and upload the code to GAE.

Details on *how* to meet these requirements can be found in the Google App Engine
documentation. Please review the following resources for assistance:
   - https://cloud.google.com/appengine/downloads#Google_App_Engine_SDK_for_Python
   - https://cloud.google.com/appengine/docs/python/
   - https://developers.google.com/api-client-library/python/guide/aaa_apikeys

See Section 4 on Running the Code for instructions on what to do with the
Project ID and API keys you will generate.

##### -- Project-Specific Requirements
###### From Project Rubric (ConferenceAppSpecs.pdf) and Requirements.md --

1.  App Architecture

    1.1 App is architected as a Web Service API

    1.2 App supports a variety of possible front-end clients

2.  Task 1: Design Choices (Implementation).

    2.1 Student adds classes for Session
and SessionForm.

    2.2 The README file includes an explanation about how Sessions and
    Speakers are implemented.

    2.3 Student response shows understanding of the process of data modeling
    and justifies their implementation decisions for the chosen data types.

3.  Task 2: Session Wishlist - Users are able to mark sessions they are
interested in and retrieve their own current wishlist.

4.  Task 3: Additional Queries

    4.1 The README file describes two additional query types that are consistent
    with the goals of the project.

    4.2 Both of the proposed queries are implemented.

    4.3 Query Problem: In the README, student describes the reason for the
    problem with the provided query.

    4.4 Query Problem: In the README, student proposes one or more solutions
    to the problematic query.

5.  Task 4: Featured Speaker

    5.1 Student implements getFeaturedSpeaker()

    5.2 Student uses App Engine's Task Queue when implementing the featured
    speaker logic:

    - When a new session is added to a conference, check the speaker. If
    there is more than one session by this speaker at this conference,
    also add a new Memcache entry that features the speaker and session
    names. You can choose the Memcache key."

6.  Code Quality

    6.1 Code is ready for personal review and neatly formatted.

    6.2 Code follows an intuitive, easy-to-follow logical structure.

7.  Code Readability - Comments are present and effectively explain longer code
procedures.

8.  Documentation

    8.1 README file is included.

    8.2 The README file provides details of all the steps required to successfully
    run the application.

## 3 - Satisfaction of Requirements discussion

1.  Requirement 1 defines that the application is to be architected as a
Web Service API and that as such, it supports a variety of possible front-end
clients.

    A review of app.yaml reveals that an API is "published" under the URL
    string beginning with `/_ah/spi/*`. Further, app.yaml directs all such
    requests to conference.api. The Conference API is fully specified in
    the file `conference.py`. The API itself is defined on approximately
    line 62 with the @endpoints.api decoration. Each specific method of
    the API is defined in the remainder of the file and is decorated with
    @endpoints.method that defines parameters of the URL and request.

    The code is architected using the Google Cloud Endpoints API which, by
    definition, is a client-agnostic architecture built using RESTful API's.
    Further, example clients are provided both as a web front-end within
    this repository (see `/static` directory) and also as an Android client
    via the Google Play Store.

2.  Requirement 2 defines requirements to create the notion of a Session
    for a specific Conference. To accommodate this requirement, two classes
    will be required along with several methods to support Session actions
    such as creating and removing sessions.

    The Session class itself is defined in `models.py` and includes the
    following fields:

    - sessionName
    - highlights
    - speaker
    - duration
    - typeOfSession
    - date
    - startTime (in 24 hour notation so it can be ordered).
    - speakerKey

    The `date` field is defined as an extension of ndb.DateProperty to
    properly support date-oriented data. All remaining fields are defined
    as extensions to ndb.StringProperty and will contain strings. Note
    that the startTime field is expected to contain a date in HH:MM format
    using 24 hour notation.

    The speakerKey field is also an extension of ndb.StringProperty and
    specifically exists in order to link the session to a Speaker (described
    further below). This field will contain a "websafe" key to the associated
    Speaker.

    In addition to creating classes to support Session (and REST-based
    Session operations), a Speaker class was implemented to store data
    associated with a Speaker. The fields for a Speaker are:

    - displayName
    - profileKey
    - biography

    All of the above fields are extensions to ndb.StringProperty. If the
    Speaker also happens to be a user of the system, the profileKey links
    to their user Profile in the system.

    Finally, the original Conference class was modified:

    - sessionKeys(repeated=True)
        - Defines a "list" of sessionKeys that relate the given Conference
        to zero or more Sessions that, together, make up the "agenda" of
        the Conference. As before, these are "websafe" keys.

    To support operations involving Sessions such as creating and deleting
    them, several methods were required and are briefly described below.

    - getConferenceSessions(websafeConferenceKey)
        - Given a conference, return all sessions

    - getConferenceSessionsByType(websafeConferenceKey, typeOfSession)
    	- Given a conference, return all sessions of a specified type
    				(eg lecture, keynote, workshop)
    - getSessionsBySpeaker(speaker)
    	- Given a speaker, return all sessions given by this particular
    				speaker, across all conferences
    - createSession(SessionForm, websafeConferenceKey)
        - Creates a session and relates it to the parent Conference it is
        part of.
    	- Available only to the organizer of the conference.

3.  Requirement 3 defines the notion of a Session Wishlist for a user. The
    idea is that a user can put various Sessions on their wishlist to help
    them remember the sessions they are interested in.

    To support this functionality, the Profile (represents a user in the
    system) class required modification:

    - add field `sessionKeysWishList` as a list (repeated=True) of Session
    keys the user has added to their wishlist.

    Further, two Endpoints methods were required to support operations:
    - addSessionToWishlist(SessionKey)
		- adds the session to the user's list of sessions they are
				interested in attending
	- getSessionsInWishlist()
		- query for all the sessions in a conference that the user is
				interested in

4.  Requirement 4 specified that two new queries (of the student's choice)
    be created and that a specific query "problem" be solved by the student.

    4.1 To satisfy the first part of the requirement, the following two queries
    and their associated Endpoint methods were created:

    - getAllSpeakers()
        - Returns a list of all the Speakers for all Conferences and Sessions

    - sessionsByTimeAndType(startTime,typeOfSession)
        - Returns all Sessions that begin before the time specified
            by startTime (represented in 24 hour format as HH:MM) and
            constrained to MATCH the type of Session as specified by the
            typeOfSession parameter.

    4.2 The 2nd part of the requirement posed a specific query-related problem
    to solve along with a description of how the solution was derived. The
    problem itself is as follows:

   - Let’s say that you don't like workshops and you don't like sessions
      after 7 pm. How would you handle a query for all non-workshop
      sessions before 7 pm?
      - What is the problem for implementing this query?
      - What ways to solve it did you think of?

      The main problem in implementing this query is that Datastore will not
      allow you to do a query with two different inequality operators in the
      query. For this problem, the query would require that typeOfSession
      does NOT equal 'workshop' and startTime is less than 19:00:00. Datastore
      will not allow that sort of query.

      To solve this, you could either query for all sessions that do NOT match
      the session type and then iterate over the results in Python and test
      the session startTime against the request startTime OR the exact
      opposite.

      I chose to implement it the "first" way described above as I believe
      that filtering by session type may produce FEWER results than starting
      out with all the sessions before a given time and then iterating from
      there.

      In the code, you'll see extensive commenting explaining the process,
      but at a high level the query results are iterated over and a new
      list is built to contain only those sessions from the query that start
      before the indicated time. That new list is what gets returned to the
      user.

5.  Requirement #5 specifies that a Featured Speaker capability is to be added
    to the system. Specifically, some sort of logic is to be created to
    identify the criteria for a Speaker to be the Featured Speaker and
    then appropriate code must be written to implement that logic using App
    Engine's Task Queue capability.

    - SetFeaturedSpeakerHandler()
      - Method to determine if there are any featured speakers in the system
        and if so, set up a MemCache key to hold the list of those speakrers.
      - Defined in `main.py`.
    - getFeaturedSpeaker()
      - Method to retrieve the list of Featured Speakers that is stored in
        MemCache so it can be displayed. Defined in `conference.py`.
      - Called any time a change of Speakers or Sessions is made.

6.  Requirement #6 defines Code Quality as code that is ready for personal
    (human) review and is neatly formatted. It further specifies that the code
    is intuitive and has an easy-to-follow, logical structure.

    As you will see in the code, the methods related to a particular class of
    object (Session, Speaker, Conference, etc.) are grouped together and
    typically follow a consistent format in terms of the order in which the
    methods are defined. All PEP guidelines for line length are adhered to.

7.  Requirement #7 requires the code to be readable and that comments are
    present that effectively explain longer blocks of code. In most cases,
    not only are longer blocks of code commented but so are shorter ones.
    Comments, when used, are to help articulate the logic or approach as well
    as to remind the reader of what certain variables are used for, etc.

8.  Requirement #8 requires that a README file is present and that it contains
    instructions for running the code. The first part of this requirement is
    deemed self-evident (you wouldn't be reading this otherwise). Instructions
    for running the code are in the very next section.

## 4 - Running the Code

1.  First, follow the steps outlined in Section 2, Requirements, and create a
    project on the Google Developer's Console.

2.  Within the console, create the appropriate Credentials for your project.
    You will need all of the following:
    - Browser Key
    - Android Key
    - iOS Key

3.  Download this repo to your local machine.

4.  Using the editing tool of your choice, open `settings.py` and replace the
    keys you see there with the keys you generated in Step 2 above.

5.  Also open `app.yaml` and replace the application with the Application ID
    you created in Step 1 above.

6.  Using the Google tools, run the code locally using Google's Development
    Server (included in the SDK you would have obtained while getting the
    required components described in Section 2, Requirements, of this document).

7.  Once you have the code running on the local dev server, you can use the
    Google SDK tools to deploy the code up to GAE if you choose.

8.  NOTE: you can delete any files that end with `.md` or `.pdf` as well as the
    `.gitignore` file. You must keep the `templates` directory as well as the
    entire contents of the `static` directory.


## 5 - Credits
Original starter project created by Google and Udacity as part of the Full
Stack Nanodegree program, Project 4. Original app named Conference Central.

Modifications by Greg Palen included completing assigned project components as
well as some limited refactoring of the original code.