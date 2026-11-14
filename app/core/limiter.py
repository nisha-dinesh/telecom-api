# app/core/limiter.py
# Job of this file: ONE shared rate limiter. Routes add "@limiter.limit('5/minute')".

from slowapi import Limiter
from slowapi.util import get_remote_address

# key_func = how to tell callers apart (here: by IP address).
# default_limits = applies to every route that has no limit of its own.
# Counters live in memory: fine for one server process.
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])