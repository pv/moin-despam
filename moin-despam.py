#!/usr/bin/env python
"""
moin-despam.py [OPTIONS]

Script for mass-marking pages as spam in MoinMoin. It

    1) Downloads RecentChanges.
    2) Asks you which of the pages to mark as spam (via $EDITOR, default vi).
    3) Logs in with your user account.
    4) Replaces the text of each page by '#acl All:\\nspam',
       which makes the page disappear from RecentChanges, except for superusers

NOTE: you need to have a superuser account for this to work!

You need a configuration file (default is ~/.moin-despam.ini), like this::

    url = http://some-website.com/moinwiki
    user = YourUserName
    password = your-password

"""

#
# This script is in the public domain. Use as you see fit.
#

#
# The code below is super-ugly and badly structured.
# The excuse is that it was written in haste.
#

import os
import urllib
import subprocess
import time
import re
import mechanize
import optparse
import configobj

# get config
p = optparse.OptionParser(usage=__doc__.strip())
p.add_option("-c", "--config", action="store", dest="config",
             default=os.path.expanduser("~/.moin-despam.ini"),
             help="configuration file")
p.add_option("-r", "--regex", action="store", dest="regex",
             default=None, help="delete according to a regular expression")
p.add_option("-f", "--force", action="store_true", dest="force",
             default=False, help="don't ask for confirmation")
options, args = p.parse_args()
if len(args) != 0:
    p.error("Too many arguments")
try:
    if not os.path.isfile(options.config):
        raise RuntimeError("file does not exist")
    cfg = configobj.ConfigObj(options.config)
    url = str(cfg['url']).strip().rstrip('/')
    user = str(cfg['user']).strip()
    password = str(cfg['password']).strip()
except Exception, e:
    p.error("Could not load config file '%s': %s" % (options.config, str(e)))

# get cracking
urllib.getproxies = lambda: {} # fuck, how can disabling proxies be this difficult
br = mechanize.Browser()

print "Reading RecentChanges..."
r = br.open("%s/RecentChanges" % url)
assert br.viewing_html()

pages = []
seen_pages = {}
last_page = None
for link in br.links():
    m = re.match(r'^/(.*)\?action=info$', link.url)
    if m:
        page = m.group(1).strip()
        if page == 'RecentChanges':
            continue
        if page not in seen_pages:
            seen_pages[page] = True
            pages.append(page)
        last_page = page

# select pages to delete
selected_pages = list(pages)
if not selected_pages:
    print ""
    print "No pages to delete."
    raise SystemExit(0)
elif options.regex:
    selected_pages = [p for p in selected_pages
                      if re.match('^%s$' % options.regex, p)]
    print ""
    print "Selected pages:"
    print "---------------"
    for page in selected_pages:
        print page
    if not options.force:
        ok = raw_input("OK [y/n]: ")
        if ok != 'y':
            raise SystemExit(1)
else:
    while True:
        f = open('/tmp/pagelist', 'w')
        f.write("# A list of pages to mark as spam is below. Remove those that\n"
                "# you don't want to mark as spam from the list.\n"
                "# You can also add new pages to mark in the list.\n\n")
        for page in selected_pages:
            f.write("%s\n" % page)
        f.close()
        subprocess.call([os.environ.get('EDITOR', 'vi'), '/tmp/pagelist'])
        f = open('/tmp/pagelist', 'r')
        selected_pages = []
        seen_pages = {}
        for line in f:
            line = line.strip()
            if line.startswith('#'):
                continue
            line = line.replace(' ', '')
            if line and line not in seen_pages:
                seen_pages[line] = True
                selected_pages.append(line)
        f.close()

        print ""
        print "Selected pages:"
        print "---------------"
        for page in selected_pages:
            print page
        ok = raw_input("OK [y/n]: ")
        if ok == 'y':
            break
        elif ok == 'n':
            print "Nothing done."
            raise SystemExit(0)

# follow second link with element text matching regular expression
print "Logging in as %s..." % user
r = br.open("%s/?action=login" % url)
assert br.viewing_html()
br.select_form(nr=2)
br["name"] = user
br["password"] = password
r = br.submit()

# start deleting
for page in selected_pages:
    print "Requesting %s" % page
    skip = False
    count = 0
    timeskip = 10
    while True:
        try:
            r = br.open("%s/%s?action=edit" % (url, page))
            break
        except mechanize.HTTPError, err:
            count += 1
            if err.code in (401, 403):
                print "    Got error %d (unauthorized/forbidden); stopping!"
                raise
            elif count < 4:
                if err.code == 503:
                    timeskip = 80
                    count = max(2, count)
                    print "    Triggered MoinMoin surge protect, a long wait is required."
                print "    Got error %d; retrying in %d sec" % (
                    err.code, timeskip)
                time.sleep(timeskip)
                timeskip *= 2
                continue
            else:
                print "    Too many tries, giving up..."
                skip = True
                break

    if not skip:
        print "    Deleting %s" % page
        br.select_form(nr=1)
        br["savetext"] = "#acl All:\nspam"
        try:
            r = br.submit()
        except mechanize.HTTPError, err:
            if err.code in (500, 502):
                print "    Got error %d; assuming OK" % err.code
            else:
                raise
        assert br.viewing_html()
        time.sleep(1)
