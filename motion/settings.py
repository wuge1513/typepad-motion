# Copyright (c) 2009-2010 Six Apart Ltd.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of Six Apart Ltd. nor the names of its contributors may
#   be used to endorse or promote products derived from this software without
#   specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


"""Settings for Motion sites.

Motion sites use and provide many settings for you to customize the Motion
site experience. Include the default values for these settings in your Django
project's settings by importing them at the top of your ``settings.py``
module::

    from motion.settings import *

You can then override the defaults later in your ``settings.py`` (or in an
imported ``local_settings.py``) as you would Django's default settings.

"""


# Motion application settings.
# You can override these in your custom app settings.py.
import os
import logging
from django.utils.translation import ugettext_lazy as _
from typepadapp.settings import *


DEBUG = False
TEMPLATE_DEBUG = DEBUG

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = 'dev.db'
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''

APPEND_SLASH = False

TIME_ZONE = 'ETC/UTC'

# Enable this if you need to customize application phrases or
# need real localization
USE_I18N = False

MEDIA_URL = '/static/'
ADMIN_MEDIA_PREFIX = '/media/'

AUTHENTICATION_BACKENDS = (
    'typepadapp.backends.TypePadBackend',
)

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'typepadapp.csrf_middleware.CsrfMiddleware', # django.contrib.csrf.middleware
    'typepadapp.middleware.ConfigurationMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'djangoflash.middleware.FlashMiddleware',
    'typepadapp.debug_middleware.DebugToolbarMiddleware',
    'typepadapp.middleware.ApplicationMiddleware',
    'typepadapp.middleware.UserAgentMiddleware',
    'typepadapp.middleware.AuthorizationExceptionMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
    'django.core.context_processors.media',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.request',
    'djangoflash.context_processors.flash',
    'typepadapp.context_processors.settings',
)

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'motion',
    'typepadapp',
)

##############################
# MOTION INSTALL SETTINGS    #
##############################
SITE_ID = 1
SECRET_KEY = ''

BACKEND_URL = 'https://api.typepad.com'
"""The URL of the TypePad API service to use.

This setting should normally always be the default value of
``https://api.typepad.com``, but it may be useful to send API requests
somewhere else for development or debugging.

"""

FRONTEND_URL = 'http://127.0.0.1:8000'
"""The URL at which the Motion site is available to internet viewers.

This URL is used to build the URL a group member returns to after uploading a
media post, so you should set it to where your Motion site is hosted.

By default, this setting is ``http://127.0.0.1:8000``.

"""

FEATURED_MEMBER = None
"""The TypePad XID of an account to use as a featured member of the group.

Setting a `FEATURED_MEMBER` changes the home page of the site into that
member's activity. See :doc:`featured` for more information on using featured
members.

By default, this setting is ``None`` (no featured member).

"""

HOME_MEMBER_EVENTS = False
"""Whether to show signed-in members their "Following" pages as the Motion
site's home page.

This setting has no effect if the `FEATURED_MEMBER` setting is also set.

By default, this setting is ``False`` (the group events page is the home page).

"""

LOGIN_URL = '/login'

OAUTH_CONSUMER_KEY = 'key'
"""The key portion of your TypePad API consumer token.

Set this to the "Consumer Key" portion of the API key.

"""

OAUTH_CONSUMER_SECRET = 'secret'
"""The secret portion of your TypePad API consumer token.

Set this to the "Consumer Secret" portion of the API key.

"""

OAUTH_GENERAL_PURPOSE_KEY = 'gp_key'
"""The key portion of your TypePad API anonymous access token.

Set this to the "Anonymous Access Key" portion of the API key.

"""

OAUTH_GENERAL_PURPOSE_SECRET = 'gp_secret'
"""The secret portion of your TypePad API anonymous access secret.

Set this to the "Anonymous Access Secret" portion of the API key.

"""

SESSION_COOKIE_NAME = 'motion'

AUTH_PROFILE_MODULE = ''
CACHE_BACKEND = 'locmem:///'

POST_TYPES =  [
    { "id": "post", "label": _("Text") },
    { "id": "link", "label": _("Link") },
    { "id": "photo", "label": _("Photo") },
    { "id": "video", "label": _("Video") },
    { "id": "audio", "label": _("Audio") },
]
"""The post type IDs and labels displayed in the member posting interface.

This setting is a list of dictionaries, each dictionary containing an ``id``,
the code identifier for a type of post; and a ``label``, the localized name
for that type of post. To remove a post type from the posting interface,
redefine this setting without that type.

By default, this setting defines ``post``, ``link``, ``photo``, ``video``, and
``audio`` post types.

"""

DEFAULT_USERPIC_PATH = 'images/default-avatars/spaceface-50x50.jpg'
"""The path to the to use if a problem occurs finding a member's userpic.

All TypePad accounts have their own default userpics, so this userpic won't
appear unless a problem occurs. You should not need to change it from its
default value of ``images/default-avatars/spaceface-50x50.jpg``.

"""

USE_TITLES = False
"""Whether to provide titles in the posting interface.

If set to ``True``, the Motion posting interface will include a "more options"
section that includes a field for post titles.

By default, `USE_TITLES` is ``False`` and titles are not used.

"""

# Switches to enable/disable posting/commenting/rating/following
ALLOW_POSTING = True
"""Whether to allow posting new posts in the Motion interface.

If set to ``False``, the Motion posting interface will not be shown to anyone.
Use this setting to temporarily disable addition of new posts. To turn off
posting for regular members but let administrators still post, use
`ALLOW_COMMUNITY_POSTS` instead.

By default, this setting is ``True`` (posting is enabled).

"""

ALLOW_COMMENTING = True
"""Whether to provide the Motion commenting interface.

If set to ``False``, the Motion commenting interface will not be shown. Use
this setting to temporarily disable the leaving of new comments.

By default, this setting is ``True`` (commenting is enabled).

"""

ALLOW_RATING = True
"""Whether to provide Motion's interface for favoriting posts.

If set to ``False``, the interface for marking posts as favorites will not be
provided. Use this setting to temporarily prevent saving posts as favorites.

By default, this setting is ``True`` (favoriting is enabled).

"""

ALLOW_USERS_TO_DELETE_POSTS = True
"""Whether Motion should allow group members to delete their own posts and
comments.

The ability to delete some assets may be affected by further permissions
provided by TypePad (for example, group members may only be allowed to delete
comments during a grace period after leaving them). This setting does not
affect administrators' ability to delete any post in the group, only regular
members' ability to delete their own assets. Regular members can never delete
other members' content in the group.

By default, this setting is ``True`` and group members can delete their assets.

"""

ALLOW_COMMUNITY_POSTS = True
"""Whether regular group members should be able to post to the group.

If this setting is set to ``False``, only administrators of the group can make
new posts. To disable for all members including administrators, use
`ALLOW_POSTING` instead.

By default, this setting is ``True`` and all group members can post.

"""

ITEMS_PER_FEED = 18
"""How many items to put in the site's XML feeds.

This setting affects how many events are in the group events feed, how many
posts are in a member's feed, and how many comments are in a post's comments
feed.

By default, 18 items are shown in feeds.

"""

# Group members, following, followers
MEMBERS_PER_PAGE = 18
"""How many members to show on pages of members lists.

This setting governs how many members are shown per page in the group members
list and the lists of members following or being followed by another member of
the group. Depending on the theme your Motion site uses, the members lists may
be shown in three columns; for these themes, use a multiple of three for this
setting to avoid incomplete rows.

By default, 18 members are shown per page.

"""

FOLLOWERS_PER_WIDGET = 5
"""How many group members to show in each following/followers bar on the home
page.

When viewing the group events page, signed-in members see short bars of group
members following and being followed by them next to the compose form. This
settings governs how many members' userpics are shown in each bar.

By default, the bars show five userpics.

"""

PARAGRAPH_WORDCOUNT = 100
"""How many words of each post to show on the group events page.

By default, 100 words are shown.

"""

LINK_TITLE_LENGTH = 60
"""How many characters to include in the title of a link post.

If a link post has a longer title, it is truncated to this many characters.
Note titles are only shown at all if the `USE_TITLES` setting is ``True``.

By default, the first 60 characters of link posts' titles are used.

"""

FULL_FEED_CONTENT = False
"""Whether the full content of posts is included in feeds.

If set to ``True``, the full content of posts is included in each feed item,
as when viewing the assets on their permalink pages. If ``False``, are
truncated as on the group events page (that is, to the first
`PARAGRAPH_WORDCOUNT` words).

By default, this setting is ``False`` and feed items are truncated.

"""

PHOTO_MAX_WIDTH = 460
"""The maximum width in pixels at which to display photos.

This setting should specify the width of the column in your theme where photo
posts are displayed, in pixels. Photos wider than this size may be posted to
the group, but they will be constrained to display at this width.

By default, `PHOTO_MAX_WIDTH` is 460.

"""

VIDEO_MAX_WIDTH = 400
"""The maximum width in pixels at which to display video embeds.

This setting should specify a safe size at which to embed video in the page,
equal to or less than the width in pixels of the column in your theme where
video posts are displayed.

By default, `VIDEO_MAX_WIDTH` is 400.

"""

THEME = 'motion'
"""The name of the theme to use for this Motion site.

This setting controls which ``theme`` path of the stylesheet to include in the
Motion site pages. For example, if you added a ``kittens`` theme and set
`THEME` to ``kittens``, the Motion templates would include the
``themes/kittens/style.css`` stylesheet.

By default, the ``motion`` theme is used.

"""
