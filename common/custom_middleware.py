import logging
from datetime import datetime


class APILoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "POST":
            logger = logging.getLogger('api_log')
            logger.info([request.path, request.method, datetime.now()])
        response = self.get_response(request)
        return response
    