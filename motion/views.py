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


"""Views for Motion sites.

Motion's views provide the Motion community microblogging experience. Motion
uses the `typepadapp` class-based view system; see `typepadapp.views` for more
about how these class-based views work.

"""


from urlparse import urljoin, urlparse
import simplejson as json
import re

from django.conf import settings
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.generic.simple import redirect_to
from django.http import Http404, HttpResponseRedirect, HttpResponseForbidden, HttpResponseGone
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import SiteProfileNotAvailable
from django.contrib.auth import get_user
from django.utils.html import escape
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe

from motion import forms
import motion.models
import typepad
import typepadapp.forms
from typepadapp import models, signals
from typepadapp.views.base import TypePadView


### Moderation
if 'moderation' in settings.INSTALLED_APPS:
    from moderation import models as moderation
else:
    moderation = None


def home(request, page=1, **kwargs):
    """Display the home page view, based on local configuration.

    The home page may be the list of recent member activity, a featured user's
    profile page, or the recent activity in the group of people you are
    following. Which home page is shown depends on the related settings:

    * If the `FEATURED_MEMBER` setting is set, the home page is the
      `FeaturedMemberView`.
    * Otherwise, if `HOME_MEMBER_EVENTS` is ``True`` and the viewer is logged
      in, the home page is the viewer's `FollowingEventsView`.
    * Otherwise, the home page is the `GroupEventsView`.

    By default there's no `FEATURED_MEMBER` and `HOME_MEMBER_EVENTS` is
    ``False``, so the home page view is the group events view. To always use a
    certain view instead of these rules, change your urlconf to use a
    different view for the home page.

    """
    if settings.FEATURED_MEMBER:
        # Home page is a featured user.
        return FeaturedMemberView(request, settings.FEATURED_MEMBER,
            page=page, view='home', **kwargs)
    if settings.HOME_MEMBER_EVENTS:
        typepad.client.batch_request()
        user = get_user(request)
        typepad.client.complete_batch()
        if user.is_authenticated():
            # Home page is the user's inbox.
            return FollowingEventsView(request, page=page, view='home', **kwargs)
    # Home page is group events.
    return GroupEventsView(request, page=page, view='home', **kwargs)


class AssetEventView(TypePadView):

    """An abstract view for displaying a list of asset events.

    This is an abstract view for showing a list of events, such as on the
    `GroupEventsView` or `MemberView`. It automatically filters the
    `object_list` attributes of subclassing views to only include events that
    refer to assets posted to the group.

    """

    def filter_object_list(self, request):
        self.object_list.entries = [event for event in self.object_list.entries
            if isinstance(event.object, models.Asset) and event.object.is_local]

        ### Moderation
        if moderation:
            id_list = [event.object.url_id for event in self.object_list.entries]
            if id_list:
                suppressed = moderation.Queue.objects.filter(asset_id__in=id_list,
                    status=moderation.Queue.SUPPRESSED)
                if suppressed:
                    suppressed_ids = [a.asset_id for a in suppressed]
                    self.object_list.entries = [event for event in self.object_list.entries
                        if event.object.url_id not in suppressed_ids]

                approved = moderation.Approved.objects.filter(asset_id__in=id_list)
                approved_ids = [a.asset_id for a in approved]

                if request.user.is_authenticated():
                    flags = moderation.Flag.objects.filter(tp_asset_id__in=id_list,
                        user_id=request.user.url_id)
                    flag_ids = [f.tp_asset_id for f in flags]
                else:
                    flag_ids = []

                for event in self.object_list.entries:
                    event.object.moderation_flagged = event.object.url_id in flag_ids
                    event.object.moderation_approved = event.object.url_id in approved_ids


class AssetPostView(TypePadView):

    """An abstract view that can make new posts to the group.

    Views that subclass AssetPostView can post new content to the group.

    .. rubric:: Template variables:

    * ``form``: A :class:`PostForm` instance to use for the compose form.
    * ``elsewhere``: A list of `ElsewhereAccount` instances belonging to the
      signed-in viewer. Some of these accounts may be used for cross-posting.
    * ``upload_xhr_endpoint``: A URL for posting media assets to.
    * ``upload_complete_endpoint``: The URL of the `upload_complete` view.
      Send it to the ``upload_xhr_endpoint`` for it to return to your site
      after the viewer posts a media asset.

    """

    form = forms.PostForm

    def setup(self, request, *args, **kwargs):
        super(AssetPostView, self).setup(request, *args, **kwargs)

        if request.user.is_authenticated() and 'elsewhere' in self.context:
            elsewhere = self.context['elsewhere']
            choices = []
            for acct in elsewhere:
                if acct.crosspostable:
                    choices.append((acct.id,
                        mark_safe("""<img src="%(media_url)sthemes/motion/images/icons/throbber.gif" alt="loading..." style="display:none;" />"""
                        """<img src="%(icon)s" height="16" width="16" alt="" /> """
                        """%(username)s """ % {
                            'media_url': settings.MEDIA_URL,
                            'icon': escape(acct.provider_icon_url),
                            'username': escape(acct.username or acct.provider_name)
                        })
                    ))
            if len(choices):
                self.form_instance.fields['crosspost'].choices = choices
                try:
                    # Saved crossposting options
                    co = motion.models.CrosspostOptions.objects.get(user_id=request.user.url_id)
                    self.form_instance.fields['crosspost'].initial = json.loads(co.crosspost)
                except motion.models.CrosspostOptions.DoesNotExist:
                    pass

    def select_from_typepad(self, request, *args, **kwargs):
        if request.user.is_authenticated():
            upload_xhr_endpoint = reverse('upload_url')
            elsewhere = request.user.elsewhere_accounts

            ### Moderation
            if moderation:
                upload_xhr_endpoint = reverse('moderated_upload_url')

            upload_complete_endpoint = urljoin(settings.FRONTEND_URL, reverse('upload_complete'))
        self.context.update(locals())

    def post(self, request, *args, **kwargs):
        if self.form_instance.is_valid():
            post = self.form_instance.save()
        else:
            request.flash.add('errors', _('Please correct the errors below.'))
            return

        ### Moderation
        if moderation:
            # lets hand off to the moderation app
            from moderation import views as mod_view
            if mod_view.moderate_post(request, post):
                return HttpResponseRedirect(request.path)

        try:
            post.save(group=request.group)
        except models.assets.Video.ConduitError, ex:
            request.flash.add('errors', ex.message)
            # TODO: if request.FILES['file'], do we need to remove the uploaded file?
        else:
            request.flash.add('notices', _('Post created successfully!'))
            signals.asset_created.send(sender=self.post, instance=post,
                group=request.group)
            if request.is_ajax():
                return self.render_to_response('motion/assets/asset.html', { 'entry': post })
            else: # Return to current page.
                return HttpResponseRedirect(request.path)


class GroupEventsView(AssetEventView, AssetPostView):

    """The list of everyone's events in the group.

    This view displays the group's recent events from all members of the
    group. Only events related to assets are shown; non-asset events such as
    joining the group are ignored. The list is split into pages of at most
    `settings.EVENTS_PER_PAGE` events each.

    .. rubric:: Template:

    ``motion/events.html``

    .. rubric:: Template variables:

    * ``object_list``: The list of `Event` instances for this view.
    * ``memberships``: A list of `Relationship` instances for the last
      `settings.MEMBERS_PER_WIDGET` members to join the group.
    * ``following``: A list of `Relationship` instances for the last
      `settings.FOLLOWERS_PER_WIDGET` group members the signed-in viewer
      followed.
    * ``followers``: A list of `Relationship` instances for the last
      `settings.FOLLOWERS_PER_WIDGET` group members who followed the signed-in
      viewer.

    See the variables available from `AssetPostView` too.

    """

    paginate_by = settings.EVENTS_PER_PAGE
    template_name = "motion/events.html"

    def select_from_typepad(self, request, page=1, view='events', *args, **kwargs):
        self.paginate_template = reverse('group_events') + '/page/%d'
        self.object_list = request.group.events.filter(start_index=self.offset, max_results=self.limit)
        memberships = request.group.memberships.filter(max_results=settings.MEMBERS_PER_WIDGET)
        if request.user.is_authenticated():
            following = request.user.following(group=request.group, max_results=settings.FOLLOWERS_PER_WIDGET)
            followers = request.user.followers(group=request.group, max_results=settings.FOLLOWERS_PER_WIDGET)
        self.context.update(locals())
        super(GroupEventsView, self).select_from_typepad(request, *args, **kwargs)


class FollowingEventsView(TypePadView):

    """The recent events by everyone in a group whom the signed-in user is
    following.

    This view displays events in the group by all group members. That is, this
    view is like the TypePad dashboard, but localized to the group. This view
    is also called a member's inbox. The viewer must be signed in. Each page
    of the view displays up to `settings.EVENTS_PER_PAGE` events.

    .. rubric:: Template:

    ``motion/following.html``

    .. rubric:: Template variables:

    * ``object_list``: The list of `Event` instances to display.

    """

    template_name = "motion/following.html"
    paginate_by = settings.EVENTS_PER_PAGE
    login_required = True

    def select_from_typepad(self, request, view='following', *args, **kwargs):
        self.paginate_template = reverse('following_events') + '/page/%d'
        self.object_list = request.user.group_notifications(request.group,
            start_index=self.offset, max_results=self.paginate_by)


class AssetView(TypePadView):

    """The permalink page for an asset.

    This view displays one asset by itself, often with comments. More comments
    can be loaded with Motion's ajax views. Through this view's page, a
    signed-in viewer may delete the asset (if permitted), post a comment, or
    mark the entry as a favorite.

    .. rubric:: Template:

    ``motion/permalink.html``

    .. rubric:: Template variables:

    * ``entry``: The `Asset` instance being viewed.
    * ``comments``: A list of `Asset` instances for the last
      `settings.COMMENTS_PER_PAGE` comments on this page's asset.
    * ``favorites``: A list of `Favorite` instances for the most recent times
      group members have marked this page's asset as a favorite.

    """

    form = forms.CommentForm
    template_name = "motion/permalink.html"

    def setup(self, request, *args, **kwargs):
        super(AssetView, self).setup(request, *args, **kwargs)

    def select_from_typepad(self, request, postid, *args, **kwargs):
        entry = models.Asset.get_by_url_id(postid)

        if request.method == 'GET':
            # no need to do these for POST...
            comments = entry.comments.filter(start_index=1, max_results=settings.COMMENTS_PER_PAGE)
            favorites = entry.favorites

        self.context.update(locals())

    def get(self, request, *args, **kwargs):
        # Verify this user is a member of the group.
        entry = self.context['entry']

        if not entry.is_local:
            # if this entry isn't local, 404
            raise Http404

        # Make a faux event object since our templates expect an event
        # object and attributes to be present
        event = typepad.Event()
        event.object = entry
        event.actor = entry.author
        event.published = entry.published
        self.context['event'] = event

        ### Moderation
        if moderation:
            entry.moderation_approved = False

            approved_asset = moderation.Approved.objects.filter(asset_id=entry.url_id)
            if len(approved_asset):
                entry.moderation_approved = True
            else:
                moderated_asset = moderation.Queue.objects.filter(asset_id=entry.url_id)
                if len(moderated_asset) and \
                    moderated_asset[0].status == moderation.Queue.SUPPRESSED:
                    return HttpResponseGone(_('The requested post has been removed from this site.'))

            if not entry.moderation_approved and request.user.is_authenticated():
                entry.moderation_flagged = moderation.Flag.objects.filter(tp_asset_id=entry.url_id,
                    user_id=request.user.url_id)

            comments = self.context['comments']

            id_list = [comment.url_id for comment in comments]
            if id_list:
                approved = moderation.Approved.objects.filter(asset_id__in=id_list)
                approved_ids = [a.asset_id for a in approved]

                suppressed = moderation.Queue.objects.filter(asset_id__in=id_list,
                    status=moderation.Queue.SUPPRESSED)
                suppressed_ids = [a.asset_id for a in suppressed]

                if request.user.is_authenticated():
                    flags = moderation.Flag.objects.filter(tp_asset_id__in=id_list,
                        user_id=request.user.url_id)
                    flag_ids = [f.tp_asset_id for f in flags]
                else:
                    flag_ids = []

                for comment in comments:
                    if comment.url_id in suppressed_ids:
                        comment.suppress = True
                    if comment.url_id in approved_ids:
                        comment.moderation_approved = True
                    if comment.url_id in flag_ids:
                        comment.moderation_flagged = True

        return super(AssetView, self).get(request, *args, **kwargs)

    def post(self, request, postid, *args, **kwargs):
        # Delete entry
        if 'delete' in request.POST:
            # Fetch the asset to delete
            asset_id = request.POST.get('asset-id')
            if asset_id is None:
                raise Http404

            entry = self.context['entry']
            if entry.url_id == asset_id:
                asset = entry
            else:
                # this request must be to delete a comment shown on this page
                typepad.client.batch_request()
                asset = models.Asset.get_by_url_id(asset_id)
                typepad.client.complete_batch()

            # Only let plain users delete stuff if so configured.
            if settings.ALLOW_USERS_TO_DELETE_POSTS or request.user.is_superuser:
                try:
                    asset.delete()
                    signals.asset_deleted.send(sender=self.post, instance=asset, group=request.group)
                except asset.Forbidden:
                    pass
                else:
                    if isinstance(asset, models.Comment):
                        # Return to permalink page
                        request.flash.add('notices', _('Comment deleted.'))
                        return HttpResponseRedirect(request.path)
                    # Redirect to home
                    request.flash.add('notices', _('Post deleted.'))
                    return HttpResponseRedirect(reverse('home'))

            # Not allowed to delete
            request.flash.add('errors', _('You are not authorized to delete this asset.'))
            return HttpResponseRedirect(request.path)

        elif 'comment' in request.POST:
            if self.form_instance.is_valid():
                typepad.client.batch_request()
                self.select_typepad_user(request)
                asset = models.Asset.get_by_url_id(postid)
                typepad.client.complete_batch()
                comment = self.form_instance.save()
                comment.in_reply_to = asset.asset_ref

                ### Moderation
                if moderation:
                    from moderation import views as mod_view
                    if mod_view.moderate_post(request, comment):
                        return HttpResponseRedirect(request.path)

                asset.comments.post(comment)
                request.flash.add('notices', _('Comment created successfully!'))
                signals.asset_created.send(sender=self.post, instance=comment,
                    parent=asset, group=request.group)
                # Return to permalink page
                return HttpResponseRedirect(request.path)


class MembersView(TypePadView):

    """The group's members list.

    This view displays a paginated list of all members in the group. From this
    page, a signed-in viewer may follow and unfollow these members. Up to
    `settings.MEMBERS_PER_PAGE` members are shown on each page.

    .. rubric:: Template:

    ``motion/members.html``

    .. rubric:: Template variables:

    * ``object_list``: The list of `User` instances for members of the group
      to display on this page.

    """

    paginate_by = settings.MEMBERS_PER_PAGE
    template_name = "motion/members.html"

    def select_from_typepad(self, request, *args, **kwargs):
        self.paginate_template = reverse('members') + '/page/%d'
        self.object_list = request.group.memberships.filter(start_index=self.offset,
            max_results=self.limit)
        self.context.update(locals())


class MemberView(AssetEventView):

    """A group member's profile page.

    This view shows a group member's per-group profile page. This page shows
    the member's profile information as well as the member's most recent
    events in the group.

    Profiles for TypePad members are only visible in the group if the member
    is either a current member of the group or has posted content in the group
    that has not been deleted. If a TypePad member leaves the group without
    posting content, the profile page will not exist, as though that TypePad
    member had never joined the group. Use the ``is_member`` template variable
    to test if the member is currently in the group.

    Profiles for blocked members are similarly not visible, except if the
    signed-in viewer is a group administrator. Use the ``is_blocked`` template
    variable to test if the member is blocked from the group.

    .. rubric:: Template:

    ``motion/member.html``

    .. rubric:: Template variables:

    * ``member``: The `User` instance for the group member whose profile page
      this is.
    * ``elsewhere``: A list of `ElsewhereAccount` instances for the member
      whose profile page is being displayed.
    * ``object_list``: The profile member's `settings.EVENTS_PER_PAGE` most
      recent events in the group.
    * ``is_self``: Whether the member whose page is being viewed is also the
      signed-in viewer. That is, whether the signed-in viewer is viewing their
      own profile page.
    * ``is_member``: Whether the member being viewed is still a member of the
      group.
    * ``is_blocked``: Whether the member being viewed is blocked from
      membership in the group.

    """

    paginate_by = settings.EVENTS_PER_PAGE
    template_name = "motion/member.html"
    methods = ('GET', 'POST')

    def select_from_typepad(self, request, userid, *args, **kwargs):
        self.paginate_template = reverse('member', args=[userid]) + '/page/%d'

        member = models.UserProfile.get_by_url_id(userid)
        u = member.user
        user_memberships = u.group_memberships(request.group)

        if request.method == 'GET':
            # no need to do these for POST requests
            elsewhere = u.elsewhere_accounts
            self.object_list = u.group_events(request.group,
                start_index=self.offset, max_results=self.limit)

        # clear this reference, so we don't do an additional subrequest
        # for the User object too
        u = None

        self.context.update(locals())
        super(MemberView, self).select_from_typepad(request, userid, *args, **kwargs)

    def get(self, request, userid, *args, **kwargs):
        # Verify this user is a member of the group.
        user_memberships = self.context['user_memberships']
        member = self.context['member']

        try:
            user_membership = user_memberships[0]
        except IndexError:
            is_member = False
            is_blocked = False
        else:
            is_member = user_membership.is_member()
            is_blocked = user_membership.is_blocked()

        if not request.user.is_superuser: # admins can see all members
            if not len(self.object_list) and not is_member:
                # if the user has no events and they aren't a member of the group,
                # then this is a 404, effectively
                raise Http404

        self.context['is_self'] = request.user.id == member.id
        self.context['is_member'] = is_member
        self.context['is_blocked'] = is_blocked

        elsewhere = self.context['elsewhere']
        if elsewhere:
            for acct in elsewhere:
                if acct.provider_name == 'twitter':
                    self.context.update({
                        'twitter_username': acct.username
                    })
                    break

        try:
            profile = member.user.get_profile()
        except SiteProfileNotAvailable:
            pass
        else:
            profileform = typepadapp.forms.LocalProfileForm(instance=profile)
            if self.context['is_self']:
                self.context['profileform'] = profileform
            else:
                self.context['profiledata'] = profileform


        ### Moderation
        if moderation:
            if hasattr(settings, 'MODERATE_BY_USER') and settings.MODERATE_BY_USER:
                blacklist = moderation.Blacklist.objects.filter(user_id=member.url_id)
                if blacklist:
                    self.context['moderation_moderated'] = not blacklist[0].block
                    self.context['moderation_blocked'] = blacklist[0].block
                else:
                    self.context['moderation_unmoderated'] = True


        return super(MemberView, self).get(request, userid, *args, **kwargs)

    def post(self, request, userid, *args, **kwargs):
        # post from the ban user form?
        if request.POST.get('form-action') == 'ban-user':
            user_memberships = self.context['user_memberships']

            try:
                user_membership = user_memberships[0]
            except IndexError:
                is_admin = False
                is_member = False
                is_blocked = False
            else:
                is_admin = user_membership.is_admin()
                is_member = user_membership.is_member()
                is_blocked = user_membership.is_blocked()

            if not request.user.is_superuser or is_admin:
                # must be an admin to ban and cannot ban/unban another admin
                raise Http404

            if is_member:
                # ban user
                user_membership.block()
                signals.member_banned.send(sender=self.post,
                    instance=self.context['member'], group=request.group,
                    membership=user_membership)
            elif is_blocked:
                # unban user
                user_membership.unblock()
                signals.member_unbanned.send(sender=self.post,
                    instance=self.context['member'], group=request.group,
                    membership=user_membership)

        ### Moderation
        elif moderation and request.POST.get('form-action') == 'moderate-user':
            member = self.context['member']

            try:
                blacklist = moderation.Blacklist.objects.get(user_id=member.url_id)
            except:
                blacklist = moderation.Blacklist()
                blacklist.user_id = member.url_id

            if request.POST['moderation_status'] == 'block':
                blacklist.block = True
                blacklist.save()
                request.flash.add('notices', _('This user can no longer post.'))
            elif request.POST['moderation_status'] == 'moderate':
                blacklist.block = False
                blacklist.save()
                request.flash.add('notices', _('This user\'s posts will be moderated.'))
            elif blacklist and blacklist.pk:
                blacklist.delete()
                request.flash.add('notices', _('This user is no longer moderated.'))

        else:
            return super(MemberView, self).post(request, userid, *args, **kwargs)

        # Return to current page.
        return HttpResponseRedirect(request.path)


class FeaturedMemberView(MemberView, AssetPostView):

    """The profile page for a featured member of the group.

    This view is like the `MemberView`, but can include a form for posting new
    content into the group, so that this view can be used as the home page.
    This view is used as the home page when a featured member is configured in
    the site settings; see the `home` view for more information.

    .. rubric:: Template:

    ``motion/featured_member.html``

    .. rubric:: Template variables:

    See the variables provided by `MemberView` and `AssetPostView`.

    """

    template_name = "motion/featured_member.html"

    def select_from_typepad(self, request, userid, *args, **kwargs):
        super(FeaturedMemberView, self).select_from_typepad(request, userid, *args, **kwargs)
        memberships = request.group.memberships.filter(member=True, max_results=settings.MEMBERS_PER_WIDGET)
        # this view can be accessed in different ways; lets preserve the
        # request path used, and strip off any pagination portion to construct
        # the pagination template
        path = request.path
        path = re.sub('(/page/\d+)?/?$', '', path)
        self.paginate_template = path + '/page/%d'
        self.context.update(locals())
        super(FeaturedMemberView, self).select_from_typepad(request, userid, *args, **kwargs)


class RelationshipsView(TypePadView):

    """A list of group members either following or being followed by a
    particular member of the group.

    This view displays members of the group who are following a given group
    member, or members of the group whom the given group member is following.
    The list is displayed the same way as the full group member directory
    (even using the same template).

    .. rubric:: Template:

    ``motion/members.html``

    .. rubric:: Template variables:

    * ``member``: The `User` instance for the member whose relationships are
      being viewed.
    * ``object_list``: A list of `Relationship` instances for up to
      `settings.MEMBER_PER_PAGE` "followings." If viewing a member's
      "followers" page, that member is the `target` of the `Relationship` and
      the followers are the `source` attributes; on a member's "following"
      page, these are reversed.

    """

    paginate_by = settings.MEMBERS_PER_PAGE
    template_name = "motion/members.html"

    def select_from_typepad(self, request, userid, rel, *args, **kwargs):
        if rel not in ('following', 'followers'):
            # The URL regex *should* prevent this
            raise Http404

        # Fetch logged-in group member
        member = models.User.get_by_url_id(userid)
        self.paginate_template = reverse(rel, args=[userid]) + '/page/%d'

        self.object_list = getattr(member, rel)(start_index=self.offset,
            max_results=self.limit, group=request.group)
        self.context.update(locals())


def upload_complete(request):
    """
    Callback after uploading directly to TypePad which verifies the response
    as 'okay' or displays an error message page to the user.
    """
    status = request.GET['status']
    if status == '201' or status == '200':
        # Signal that a new object has been created
        parts = urlparse(request.GET['asset_url'])
        instance = models.Asset.get(parts[2], batch=False)
        request.flash.add('notices', _('Thanks for the %(type)s!') \
            % { 'type': instance.type_label.lower() })
        signals.asset_created.send(sender=upload_complete, instance=instance,
            group=request.group)
        # Redirect to clear the GET data
        if settings.FEATURED_MEMBER:
            typepad.client.batch_request()
            user = get_user(request)
            typepad.client.complete_batch()
            if not user.is_authenticated() or not user.is_featured_member:
                return HttpResponseRedirect(reverse('group_events'))
        return HttpResponseRedirect(reverse('home'))
    return render_to_response('motion/error.html', {
        'message': request.GET['error'],
    }, context_instance=RequestContext(request))
