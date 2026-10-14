from django.core.cache import cache

def invalidate_cache(cache_key):
    """
    Invalidate a specific cache key.
    """
    cache.delete(cache_key)
    print(f"Cache invalidated for key: {cache_key}")