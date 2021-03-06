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

import re

from django import http
from django.conf import settings
from django.core.cache import cache
from django.template.loader import render_to_string
from django.template import RequestContext
import simplejson as json

import motion.models
from motion.forms import CommentForm
import typepad
from typepadapp import models, signals
from typepadapp.auth import get_user
import typepadapp.forms
from typepadapp.decorators import ajax_required


### Moderation
if 'moderation' in settings.INSTALLED_APPS:
    from moderation import models as moderation
else:
    moderation = None


@ajax_required
def more_comments(request):
    """
    Fetch more comments for the asset and return the HTML
    for the additional comments.
    """

    asset_id = request.GET.get('asset_id')
    offset = int(request.GET.get('offset')) or 1
    if not asset_id or not offset:
        raise http.Http404

    # Fetch more comments!
    typepad.client.batch_request()
    request.typepad_user = get_user(request)
    asset = models.Asset.get_by_url_id(asset_id)
    comments = asset.comments.filter(start_index=offset,
        max_results=settings.COMMENTS_PER_PAGE)
    typepad.client.complete_batch()

    ### Moderation
    if moderation:
        id_list = [comment.url_id for comment in comments]
        if id_list:
            approved = moderation.Approved.objects.filter(asset_id__in=id_list)
            approved_ids = [a.asset_id for a in approved]

            suppressed = moderation.Queue.objects.filter(asset_id__in=id_list,
                status=moderation.Queue.SUPPRESSED)
            suppressed_ids = [a.asset_id for a in suppressed]

            flags = moderation.Flag.objects.filter(tp_asset_id__in=id_list,
                user_id=request.typepad_user.url_id)
            flag_ids = [f.tp_asset_id for f in flags]

            for comment in comments:
                if comment.url_id in suppressed_ids:
                    comment.suppress = True
                if comment.url_id in approved_ids:
                    comment.moderation_approved = True
                if comment.url_id in flag_ids:
                    comment.moderation_flagged = True

    # Render HTML for comments
    comment_string = ''
    for comment in comments:
        comment_string += render_to_string('motion/assets/comment.html', {
            'comment': comment,
            'view': 'permalink',
        }, context_instance=RequestContext(request))

    # Return HTML
    return http.HttpResponse(comment_string)


@ajax_required
def favorite(request):
    """
    Add this item to the user's favorites. Return OK.
    """

    action = request.POST.get('action', 'favorite')

    asset_id = request.POST.get('asset_id')
    if not asset_id:
        raise http.Http404

    typepad.client.batch_request()
    request.typepad_user = get_user(request)
    asset = models.Asset.get_by_url_id(asset_id)
    typepad.client.complete_batch()

    if action == 'favorite':
        fav = models.Favorite()
        fav.in_reply_to = asset.asset_ref
        request.typepad_user.favorites.post(fav)
        signals.favorite_created.send(sender=favorite, instance=fav, parent=asset,
            group=request.group)
    else:
        typepad.client.batch_request()
        fav = models.Favorite.get_by_user_asset(request.typepad_user.url_id, asset_id)
        typepad.client.complete_batch()
        fav.delete()
        signals.favorite_deleted.send(sender=favorite, instance=fav,
            parent=asset, group=request.group)

    return http.HttpResponse('OK')


@ajax_required
def asset_meta(request):
    """An AJAX method for returning metadata about a list of assets, in the
    context of the authenticated user.

    This method requires POST and accepts one or more asset_id parameters
    which should be a valid TypePad Asset XID, prefixed with either
    'asset-' or 'comment-' (the prefix informs the type of metadata to
    supply. Comments cannot be favorited, so there is no need to issue
    favorite requests for them).

    The response will be a JSON data structure, mapping the supplied IDs as a
    key to a dictionary containing "favorite" and "can_delete" members that
    are assigned a true value. If an asset is neither a favorite or can be
    deleted by the requesting user, the ID will not be present in the
    response. An example response would look like this:

        {
            "asset-asset_xid1": { "favorite": true },
            "comment-asset_xid2": { "can_delete": true }
        }
    """
    if not hasattr(request, 'typepad_user'):
        typepad.client.batch_request()
        request.typepad_user = get_user(request)
        typepad.client.complete_batch()

    ids = request.POST.getlist('asset_id')
    if not ids or not request.typepad_user.is_authenticated():
        return http.HttpResponse('{}', mimetype='application/json')

    user_id = request.typepad_user.url_id
    admin_user = request.typepad_user.is_superuser

    favs = []
    opts = []
    meta = {}
    typepad.client.batch_request()
    for id in ids:
        xid = re.sub(r'^(asset|comment)-', '', id)
        # deleted comments and assets can leave a 'asset-' or 'comment-' in the request
        if not len(xid): continue

        # request favorite status for assets
        if id.startswith('asset-'):
            favs.append((id, typepad.Favorite.head_by_user_asset(user_id, xid)))

        # for non-admins and only if this install permits asset deletion,
        # request if the user can delete this asset.
        if not admin_user and settings.ALLOW_USERS_TO_DELETE_POSTS:
            opts.append((id, typepad.Asset.get_by_url_id(xid).options()))
        if admin_user:
            meta[id] = {'can_delete': True}
    typepad.client.complete_batch()

    for f in favs:
        if f[1].found():
            if f[0] not in meta:
                meta[f[0]] = {}
            meta[f[0]]['favorite'] = True
    for o in opts:
        if o[1].status == 200:
            if o[1].can_delete():
                if o[0] not in meta:
                    meta[o[0]] = {}
                meta[o[0]]['can_delete'] = True
    return http.HttpResponse(json.dumps(meta), mimetype='application/json')


@ajax_required
def asset_ping(request):
    kind = request.POST['type']
    if kind == 'comment':
        return comment_ping(request)

    stream_key = 'group_stream:%s' % request.group.xid
    xid = request.POST['xid']
    events = cache.get(stream_key)
    resp = {"count": 0, "last": xid}
    if events and xid:
        count = 0
        last = None
        for i in range(len(events)):
            if events[i] in (xid, '-' + xid):
                match = i
                break
            if not events[i].startswith('-'):
                count += 1
                last = last or events[i]
        if count and last:
            resp = {"count": count, "last": last}
    return http.HttpResponse(json.dumps(resp), mimetype='application/json')


@ajax_required
def comment_ping(request):
    parent = request.POST['parent']
    stream_key = 'asset_stream:%s' % parent
    last = request.POST['xid']
    events = cache.get(stream_key)
    resp = {"data": '', "last": last, "count": 0}

    if events:
        comments = []
        for asset_id in events:
            if last and (asset_id in (last, '-' + last)):
                break
            if not asset_id.startswith('-'):
                comments.append(asset_id)
            if len(comments) == typepad.client.subrequest_limit - 1: break

        if comments:
            resp['last'] = comments[0]
            assets = []

            typepad.client.batch_request()
            count = models.Asset.get_by_url_id(parent).comments.filter(max_results=0)
            for id in comments:
                assets.append(models.Comment.get_by_url_id(id))
            typepad.client.complete_batch()

            results = ''
            assets.reverse()
            for asset in assets:
                results += render_to_string('motion/assets/comment.html', {
                    'comment': asset,
                }, context_instance=RequestContext(request))
            resp['data'] = results
            resp['parent'] = parent
            resp['count'] = count.total_results

    return http.HttpResponse(json.dumps(resp), mimetype='application/json')


@ajax_required
def crosspost_options(request):
    """
    Add this option to the user's preferred crossposting options.
    Return OK.
    """

    typepad.client.batch_request()
    request.typepad_user = get_user(request)
    typepad.client.complete_batch()

    # Current crossposting options
    co = motion.models.CrosspostOptions.get(request.typepad_user.url_id)
    if co is None:
        co = motion.models.CrosspostOptions(user_id=request.typepad_user.url_id)
    if co.crosspost:
        options = json.loads(co.crosspost)
    else:
        options = []

    # Get checkbox value and if it is checked or unchecked
    value = request.POST.get('option_value')
    if not value:
        raise http.Http404
    checked = request.POST.get('checked') == 'true'

    # Update crossposting options
    if checked and not value in options:
        options.append(value)
    elif value in options:
        options.remove(value)

    co.crosspost = json.dumps(options)
    co.save()

    return http.HttpResponse('OK')


@ajax_required
def edit_profile(request):

    typepad.client.batch_request()
    user = get_user(request)
    typepad.client.complete_batch()

    profile = user.get_profile()
    profileform = typepadapp.forms.LocalProfileForm(request.POST, instance=profile)

    if profileform.is_valid():
        profileform.save()
        return http.HttpResponse(json.dumps({'status': 'success', 'data': 'OK'}))
    else:
        errorfields = [k for k, v in profileform.errors.items()]
        return http.HttpResponse(json.dumps({'status': 'error', 'data': ','.join(errorfields)}))


@ajax_required
def upload_url(request):
    """
    Return an upload URL that the client can use to POST a media asset.
    """
    remote_url = request.application.browser_upload_endpoint
    url = request.oauth_client.get_file_upload_url(remote_url)
    url = 'for(;;);%s' % url # no third party sites allowed.
    return http.HttpResponse(url)


@ajax_required
def asset_post(request):
    """Ajax interface for creating a post or comment."""

    post_type = request.POST.get('post_type', None)
    if post_type is None:
        raise Exception("post_type is a required parameter")

    if post_type == 'comment':
        frm = CommentForm(request.POST)
        if frm.is_valid():
            postid = request.POST.get('parent', None)
            if postid is None:
                raise Exception("parent is a required parameter")

            typepad.client.batch_request()
            user = get_user(request)
            asset = models.Asset.get_by_url_id(postid)
            typepad.client.complete_batch()

            if not user.is_authenticated():
                raise Exception("not authorized")

            request.typepad_user = user
            comment = frm.save()
            comment.in_reply_to = asset.asset_ref

            ### Moderation
            if moderation:
                from moderation import views as mod_view
                if mod_view.moderate_post(request, comment):
                    html = render_to_string('motion/assets/comment.html', {
                        'comment': comment,
                        'view': 'permalink',
                    }, context_instance=RequestContext(request))
                    return http.HttpResponse(json.dumps({
                        'status': 'moderated',
                        'data': 'Your comment is held for moderation.'}),
                        mimetype='application/json')

            try:
                asset.comments.post(comment)
            except Exception, e:
                return http.HttpResponse(json.dumps({
                    'status': 'error',
                    'data': str(e),
                }), mimetype='application/json')

            signals.asset_created.send(sender=asset_post, instance=comment,
                parent=asset, group=request.group)

            # render response
            html = render_to_string('motion/assets/comment.html', {
                'comment': comment,
                'view': 'permalink',
            }, context_instance=RequestContext(request))

            return http.HttpResponse(json.dumps({
                'status': 'posted', 'data': html, 'xid':comment.xid}),
                mimetype='application/json')
        else:
            errorfields = [k for k, v in frm.errors.items()]
            return http.HttpResponse(json.dumps({'status': 'error',
                'data': ','.join(errorfields)}), mimetype='application/json')
    else:
        # TBD: support for other post types
        pass
