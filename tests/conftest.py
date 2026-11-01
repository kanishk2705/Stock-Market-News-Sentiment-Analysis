import os
import sys

# Tests never touch the real database: give database.py syntactically valid dummy credentials.
os.environ["SUPABASE_URL"] = "https://example.supabase.co"
os.environ["SUPABASE_KEY"] = "eyJhbGciOiJIUzI1NiJ9.eyJyb2xlIjoiYW5vbiJ9.dummysignature"
os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)
os.environ.pop("GROQ_API_KEY", None)
os.environ.pop("EMAIL_SENDER", None)
os.environ.pop("EMAIL_PASSWORD", None)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
