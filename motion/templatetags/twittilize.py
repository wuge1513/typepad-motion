import re

from django import template
from django.template.defaultfilters import urlize, stringfilter
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe


register = template.Library()


def needs_autoescape(fn):
    fn.needs_autoescape = True
    return fn


usernames_re = re.compile(r"""
        (?: (?<= \A @ )    # leading at
          | (?<= \s @ ) )  # or spaced at
        \w+                # and a name
    """, re.VERBOSE | re.MULTILINE | re.DOTALL)


hashtags_re = re.compile(r"""
        (?: (?<= \A )    # beginning of string
          | (?<= \s ) )  # or whitespace
        \#               # the hash
        \w               # the tag, which starts with a word char
        (?: [^\s&]       # contains non-whitespace characters
          | &[^;]+; )*   # and complete character entities
        \w               # and ends with another word char
        (?<! 's )        # but doesn't end with "'s"
        (?<! &\#39;s )   # or an encoded "'s"
    """, re.VERBOSE | re.MULTILINE | re.DOTALL)


@register.filter
@needs_autoescape
@stringfilter
def twittilize(tweet, autoescape=None):
    if autoescape:
        tweet = conditional_escape(tweet)

    # Auto-link URLs (using Django's implementation).
    tweet = urlize(tweet)

    # Auto-link Twitter username references.
    tweet = re.sub(
        usernames_re,
        lambda m: '<a href="http://twitter.com/%s">%s</a>' % (m.group(0), m.group(0)),
        tweet,
    )

    # Auto-link hashtags.
    tweet = re.sub(
        hashtags_re,
        lambda m: '<a href="http://twitter.com/search?q=%s">%s</a>' % (m.group(0), m.group(0)),
        tweet,
    )

    return mark_safe(tweet)
