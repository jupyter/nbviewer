"""Object for tracking rate-limited requests"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import hashlib

from tornado.log import app_log
from tornado.web import HTTPError


class RateLimiter(object):
    """Rate limit checking object"""

    def __init__(self, limit, interval, cache):
        self.limit = limit
        self.interval = interval
        self.cache = cache

    def key_for_handler(self, handler):
        """Identify a visitor.
        
        Currently combine ip + user-agent.
        We don't need to be perfect.
        """
        agent = handler.request.headers.get("User-Agent", "")
        return "rate-limit:{}:{}".format(
            handler.request.remote_ip,
            hashlib.md5(agent.encode("utf8", "replace")).hexdigest(),
        )

    async def check(self, handler):
        """Check the rate limit for a handler.
        
        Identifies the source by ip and user-agent.
        
        If the rate limit is exceeded, raise HTTPError(429)
        """
        if not self.limit:
            return
        key = self.key_for_handler(handler)
        added = await self.cache.add(key, 1, self.interval)
        if not added:
            # it's been seen before, use incr
            try:
                count = await self.cache.incr(key)
            except Exception as e:
                app_log.warning("Failed to increment rate limit for %s", key)
                return

            app_log.debug(
                "Rate limit remaining for %r: %s/%s",
                key,
                self.limit - count,
                self.limit,
            )

            if count and count >= self.limit:
                minutes = self.interval // 60
                raise HTTPError(
                    429,
                    "Rate limit exceeded for {ip} ({limit} req / {minutes} min)."
                    " Try again later.".format(
                        ip=handler.request.remote_ip, limit=self.limit, minutes=minutes
                    ),
                )
