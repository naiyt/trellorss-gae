Trello RSS Google App Engine Implementation
===========================================

A Google App Engine implementation of my [trello-rss](https://github.com/naiyt/trello-rss) Python module. Allows you to create and manage feeds for Trello boards. Has support for both public and private boards.

[You can create feeds with this application here.](http://trellorss.appspot.com)

Dependencies
------------

* [Py-Trello](https://github.com/sarumont/py-trello)
* [Trello-RSS](https://github.com/naiyt/trello-rss)
* [PyRSS2Gen](https://pypi.python.org/pypi/PyRSS2Gen/1.1)

You also need a [Trello API key](https://trello.com/1/appKey/generate). Create a file called `secret.py` in your `lib` directory and enter this line:

    KEY = 'your Trello API key'

TODO
====

Feel free to suggest any changes, or make them yourselves and then send a pull request. Here are some things that need to be done:

* Support for more actions
* Support for organizations
* Modify feed page
* More efficient feed generation (for performance)