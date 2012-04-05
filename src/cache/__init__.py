# local dependencies
from .version import __version__

# external dependencies
from decorator import decorator

# stdlib
from inspect import getargspec

class Cache:
    """
    Creates a cache decorator factory.

        cache = Cache(a_cache_client)

    Positional Arguments:
    backend    This is a cache backend that must have "set" and "get"
               methods defined on it.  This would typically be an
               instance of, for example, `pylibmc.Client`.

    Keyword Arguments:
    enabled    If `False`, the backend cache will not be used at all,
               and your functions will be run as-is.  This is useful
               for development, when the backend cache may not be
               present at all.
               Default: True

    bust       If `True`, the values in the backend cache will be
               ignored, and new data will be calculated and written
               over the old values.
               Default: False

    """

    def __init__(self, backend, **default_options):
        self.backend = backend
        self.default_options = default_options

    def __call__(self, key, **kw):
        """
        Returns the decorator itself
            @cache("mykey", ...)
            def expensive_method
                # ...

            # or in the absence of decorators

            expensive_method = cache("mykey", ...)(expensive_method)

        Positional Arguments:

        key    (string) The key to set

        Keyword Arguments:

        The decorator takes the same keyword arguments as the Cache
        constructor.  Options passed to this method supercede options
        passed to the constructor.

        """


        opts = self.default_options.copy()
        opts.update(kw)

        def _cache(fn):
            return CacheWrapper(self.backend, key, fn, **opts)

        return _cache

class CacheWrapper:
    """
    The result of using the cache decorator is an instance of
    CacheWrapper.

    Methods:

    get       (aliased as __call__) Get the value from the cache,
              recomputing and caching if necessary.

    cached    Get the cached value.  In case the value is not cached,
              you may pass a `default` keyword argument which will be
              used instead.  If no default is present, a `KeyError` will
              be thrown.

    refresh   Re-calculate and re-cache the value, regardless of the
              contents of the backend cache.
    """

    def __init__(self, backend, key, calculate,
                 bust=False, enabled=True, **kw):
        self.backend = backend
        self.key = key
        self.calculate = calculate

        self.bust = bust
        self.enabled = enabled

        self.options = kw

        if len(getargspec(calculate).args) > 0:
            raise TypeError("cannot cache a function with arguments")

    def cached(self, default='__absent__'):
        cached = None
        if self.enabled and not self.bust:
            cached = self.backend.get(self.key)

        if cached is None:
            if default == '__absent__':
                raise KeyError

            return default

        return self._unprepare_value(cached)

    CACHE_NONE = '___CACHE_NONE___'
    def _prepare_value(self, value):
        if value is None:
            return self.CACHE_NONE

        return value

    def _unprepare_value(self, prepared):
        if prepared == self.CACHE_NONE:
            return None

        return prepared

    def refresh(self):
        fresh = self.calculate()
        if self.enabled:
            value = self._prepare_value(fresh)
            self.backend.set(self.key, value, **self.options)

        return fresh

    def get(self):
        try:
            return self.cached()
        except KeyError:
            return self.refresh()

    def __call__(self):
        return self.get()