VideoLinkBot
==============

Reddit bot that posts a comment with all of the links in a submission.
See the bot in action at: http://www.reddit.com/user/videolinkbot

A POLITE REQUEST
------------------
Although I have licesned this code with a very permissive license, please
don't create a bot on reddit.com that serves the same function or nearly 
the same function as /u/VideoLinkBot. When I get tired of operating this bot
I will add a text file to that effect to this repository and will also post an
announcement retiring the bot ro http://www.reddit.com/r/VideoLinkBot. Until then,
one link-aggregating bot should be more than enough. 


Getting Started
-------------
To use this tool, start out by creating a file called "loginCredentials.txt" that 
contains your bot's reddit username on the first line and password on the second.
What can I say, I'm lazy. I'll add support for passing the user/pass via the commandline
in the future, but right now this is the easiet way to use the bot.

simplebot.py
-------------
This is the main workhorse. This script contains the praw.Reddit instance used by the bot
and also contains the post_aggregate_links() function, which is the main function of the bot.
To mine videos out of all the comments in a reddit submission and post a comment listing them 
in a table, use simplebot.py like this:

        import simplebot.py as s
        s.login()
        s.post_aggregate_links('abc123')

where "abc123" is the reddit submission id.

simplemonitor.py
-----------------
This script is what according to most people makes this tool a proper "bot." Simplemonitor
keeps tabs on /r/all/comments looking for newly posted comments containing links to videos.
When simplemonitor finds such a comment, it directs simplebot to post_aggregate_links() for 
the submission that comment was posted in response to. As long as loginCredentials.txt exists,
you should be able to just run simplemonitor.py
