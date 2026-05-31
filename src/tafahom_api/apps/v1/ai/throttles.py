from rest_framework.throttling import SimpleRateThrottle


class ChatMessageRateThrottle(SimpleRateThrottle):
    scope = "chat_message"

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            return self.cache_format % {
                "scope": self.scope,
                "ident": request.user.pk,
            }
        return None
