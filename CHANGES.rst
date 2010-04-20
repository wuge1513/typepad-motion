typepad-motion Changelog
========================

1.1.3 (2010-04-20)
------------------

* Let the `PostForm` include a file, to be uploaded directly instead of through the viewer's browser.


1.1.2 (2010-03-30)
------------------

* Updated templates to be compatible with latest TypePad API changes.


1.1.1 (2009-12-16)
------------------

* Fixed a compose form IE bug in Motion javascript affecting users with crossposting options.
* Updated the group event feed with PubSubHubbub support.
* Removed some template files that were relocated to 'typepadapp' with the Motion 1.1 release.


1.1 (2009-11-24)
----------------

* typepad-motion now requires Django 1.1.1 or later.
* Added documentation for mod_wsgi usage.
* Added documentation for views.
* Added documentation for settings.
* Integrated typepadapp-moderation into views for supporting moderation features from that app.
* Added support for crossposting posts to TypePad-supported crossposting services (currently, Facebook, Twitter, FriendFeed). This introduces a new local model for saving crossposting preferences. A ``syncdb`` command should be run to create the table required for this.
* A new default theme which is more neutral.
* Fixed bug where a deleted asset would cause errors in feeds for group and member feeds.
* Feeds now use an excerpt of the post content for generating a title when necessary.
* Changed video posts attribution say "shared a video from" instead of "posted from" to better indicate the video was not necessarily authored by the member posting it.
* Fix for thumbnail selection of photo posts.


1.0.2 (2009-10-12)
------------------

* Updated Django dependency for their security release.


1.0.1 (2009-10-02)
------------------

* Version bump for PyPi packaging issues.


1.0 (2009-09-30)
----------------

* Initial release.
