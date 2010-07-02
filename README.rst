moin-despam
===========

``moin-despam.py`` is a script for mass-marking pages as spam in MoinMoin. It

1. Downloads RecentChanges.
2. Asks you which of the pages to mark as spam (via ``$EDITOR``, default vi).
3. Logs in with your user account.
4. Replaces the text of each page by ``#acl All:\nspam``,
   which makes the page disappear from *RecentChanges*, except for superusers.

NOTE: you need to have a superuser account for this to work!

You need a configuration file (default is ``~/.moin-despam.ini``), like this::

    url = http://some-website.com/moinwiki
    user = YourUserName
    password = your-password

Requirements
------------

You need to have the following additional Python libraries installed:

- `mechanize <http://wwwsearch.sourceforge.net/mechanize/>`__
- `configobj <http://www.voidspace.org.uk/python/configobj.html>`__

