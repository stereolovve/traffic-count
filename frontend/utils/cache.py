from datetime import datetime, timedelta
import json
import os
from pathlib import Path

class APICache:
    def __init__(self, cache_dir=".cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_duration = timedelta(hours=1)  # Cache válido por 1 hora

    def _get_cache_path(self, key):
        return self.cache_dir / f"{key}.json"

    def get(self, key):
        cache_path = self._get_cache_path(key)
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
                cache_time = datetime.fromisoformat(data['timestamp'])
                if datetime.now() - cache_time > self.cache_duration:
                    return None
                return data['value']
        except:
            return None

    def set(self, key, value):
        cache_path = self._get_cache_path(key)
        try:
            with open(cache_path, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'value': value
                }, f)
        except:
            pass

# Instância global do cache
cache = APICache() 