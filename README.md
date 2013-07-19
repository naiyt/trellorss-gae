Trello RSS Google App Engine Implementation
===========================================

A Google App Engine implementation of my [trello-rss](https://github.com/naiyt/trello-rss) Python module. Allows you to create and manage feeds for Trello boards. Has support for both public and private boards.

Demos:

* [Running on the Trello Dev Board](http://trellorss.appspot.com/feed/5066549580791808)
* [Running on the Trello Public API board](http://trellorss.appspot.com/feed/5275456790069248)

Dependencies
------------

These should all be included, so in theory you should be able to just clone this repository and then throw it up on GAE if you want to run a version of it yourself. The only thing you need to do is to create a file called `vars.py` in `trellorss -> lib` and enter your [Trello API key](https://trello.com/1/appKey/generate). From there, you should be good to go!

* [Py-Trello](https://github.com/sarumont/py-trello)
* [Trello-RSS](https://github.com/naiyt/trello-rss)
* [PyRSS2Gen](https://pypi.python.org/pypi/PyRSS2Gen/1.1)

TODO
====

This isn't fully fleshed out yet, so feel free to suggest any changes, or make them yourselves and then send a pull request. Here's what I'm thinking should be the next steps:

* Support for more actions
* Get the short ids for cards/boards
* Modify feed page
* Confirm page before deleting a feed
* Better handling for potentially identical feeds
* Prettify the XML (doesn't matter for the feed really, but would make it more human readable - the problem is how PyRSS2Gen outputs the resultant XML)