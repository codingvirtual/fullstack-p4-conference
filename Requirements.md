This project is connected to the Developing Scalable Apps with Python courses, but depending on your background knowledge you may not need the entirety of the course to complete this project. Here's what you should do:

1.	You do not have to do any work on the frontend part of the application to finish this project. All your added functionality will be testable via APIs Explorer. More in-depth explanation.

2.	Clone the conference application repository.

3.	Add Sessions to a Conference
		1.	Define the following endpoint methods
			1.	getConferenceSessions(websafeConferenceKey) -Given a conference, return all sessions
			2.	getConferenceSessionsByType(websafeConferenceKey, typeOfSession) Given a conference, return all sessions of a specified type (eg lecture, keynote, workshop)
			3.	getSessionsBySpeaker(speaker) -Given a speaker, return all sessions given by this particular speaker, across all conferences
			4.	createSession(SessionForm, websafeConferenceKey) -open to the organizer of the conference
		2.	Define Session class and SessionForm
			1.	Session name
			2.	highlights
			3.	speaker
			4.	duration
			5.	typeOfSession
			6.	date
			7.	start time (in 24 hour notation so it can be ordered).
4.	Add Sessions to User Wishlist
		1.	Define the following Endpoints methods
			1.	addSessionToWishlist(SessionKey) -adds the session to the user's list of sessions they are interested in attending
			2.	getSessionsInWishlist() -query for all the sessions in a conference that the user is interested in

5.	Work on indexes and queries

Create indexes
Come up with 2 additional queries
Solve the following query related problem: Let’s say that you don't like workshops and you don't like sessions after 7 pm. How would you handle a query for all non-workshop sessions before 7 pm? What is the problem for implementing this query? What ways to solve it did you think of?

6.	Add a Task
		1.	When adding a new session to a conference, determine whether or not the session's speaker should be the new featured speaker. This should be handled using App Engine's Task Queue.
		2.	Define the following endpoints method: getFeaturedSpeaker()