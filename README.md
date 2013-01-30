YoutubeLinkBot
==============

Reddit bot that posts a comment with all of the links in a submission

Right now, simplebot.py is basically the whole thing. The other files are for
future unimplemented features (data persistence, updating existing comments).

Basic usage:

    1. Create a file called logincredentials.txt in the same folder as 
       you place the script.
    2. On the first line put a username and the second line that users
       password.
    3. in an interactive console, type the following:
        
        import simplebot as s
        s.login()
        s.post_aggregate_links('123abc') # where '123abc' is a submission id
        
