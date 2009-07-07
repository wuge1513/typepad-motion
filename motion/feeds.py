from datetime import datetime

from django.conf import settings
from django.core.urlresolvers import reverse

from typepadapp import models
from typepadapp.views.base import TypePadEventFeed


class PublicEventsFeed(TypePadEventFeed):
    description_template = 'motion/assets/feed.html'

    def title(self):
        return "Recent Entries in %s" % self.request.group.display_name

    def link(self):
        return reverse("group_events")

    def subtitle(self):
        return self.request.group.tagline

    def select_from_typepad(self, *args, **kwargs):
        self.items = self.request.group.events.filter(max_results=settings.ITEMS_PER_FEED)


class MemberFeed(TypePadEventFeed):
    description_template = 'motion/assets/feed.html'

    def select_from_typepad(self, bits, *args, **kwargs):
        # check that bits has only one member (just the userid)
        if len(bits) != 1:
            raise ObjectDoesNotExist
        userid = bits[0]
        user = models.User.get_by_url_id(userid)
        self.items = user.group_events(self.request.group,
            max_results=settings.ITEMS_PER_FEED)
        self.object = user

    def title(self, obj):
        return "Recent Entries from %s" % obj.display_name

    def link(self, obj):
        if not obj:
            raise FeedDoesNotExist
        return obj.get_absolute_url()

    def subtitle(self, obj):
        return "Recent Entries from %s in %s." % (obj.display_name,
            self.request.group.display_name)


class CommentsFeed(TypePadEventFeed):
    description_template = 'motion/assets/feed.html'

    def select_from_typepad(self, bits, *args, **kwargs):
        # check that bits has only one member (just the asset id)
        if len(bits) != 1:
            raise ObjectDoesNotExist
        assetid = bits[0]
        asset = models.Asset.get_by_url_id(assetid)
        comments = asset.comments.filter(start_index=1,
            max_results=settings.ITEMS_PER_FEED)
        # TBD: construct a list of faux events to wrap each comment...
        self.items = comments
        self.object = asset

    def title(self, obj):
        return "Recent Comments on %s" % obj

    def link(self, obj):
        if not obj:
            raise FeedDoesNotExist
        return obj.get_absolute_url()

    def subtitle(self, obj):
        return "Recent Comments on %s in %s." % (obj, self.request.group.display_name)
