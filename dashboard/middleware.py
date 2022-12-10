# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class UpdateSession(object):
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request, language):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        response = self.get_response(request)

        # Code to be executed for each request/response after the view is called.
        try:
            if language == 1:
                lang = 'en'
            else:
                lang = 'span'
            request.session['language'] = lang
        except:
            pass
        return response