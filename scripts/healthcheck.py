import sys
from sqlalchemy import text
from app.db import engine
try:
    with engine.connect() as c: c.execute(text("select 1"))
    print("healthy")
except Exception as e:
    print(f"unhealthy: {e}"); sys.exit(1)
