# Copyright (c) 2009 Six Apart Ltd.
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

from django.conf import settings
from django.core.cache import cache

from typepadapp.models.users import User
from typepadapp.models.assets import Comment
from typepadapp import signals

if hasattr(settings, 'KEY_VALUE_STORE_BACKEND'):
    from motion.models.kv import CrosspostOptions
else:
    from motion.models.db import CrosspostOptions


def update_event_stream(sender, instance=None, group=None, **kwargs):
    if group is None:
        return

    if isinstance(instance, Comment):
        # ignore comments
        return

    group_id = group.xid
    lock_key = 'event_stream_lock:%s' % group_id
    stream_key = 'event_stream:%s' % group_id

    event = {
        "asset_id": instance.xid,
        # "event": event_name,
        # "ts": instance.published
    }

    tries = 0
    while tries < 10:
        if cache.add(lock_key, 1, 2):
            # we have a lock
            events = cache.get(stream_key, [])
            # add new event
            events.insert(0, event)
            if len(events) > 100:
                events = events[0:100]
            # update event stream
            cache.set(stream_key, events, settings.LONG_TERM_CACHE_PERIOD)
            # release our lock
            cache.delete(lock_key)
            return
        else:
            # lets retry
            tries += 1

signals.asset_created.connect(update_event_stream)