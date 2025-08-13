from supabase import create_client, Client
from .config import settings

_sb: Client | None = None

def get_supabase() -> Client:
    global _sb
    if _sb is None:
        _sb = create_client(settings.supabase_url, settings.supabase_service_key)
    return _sb
