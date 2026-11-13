import time
from app.db import SessionLocal
from app.config import SLA_MONITOR_INTERVAL_SECONDS
from app.workflow import run_sla_monitor
from app.seed import seed
from types import SimpleNamespace

def main():
    seed()
    system_actor = SimpleNamespace(id="scheduler", role="SYSTEM_ADMIN")
    while True:
        db=SessionLocal()
        try:
            run_sla_monitor(db, system_actor)
        finally:
            db.close()
        time.sleep(SLA_MONITOR_INTERVAL_SECONDS)

if __name__=="__main__":
    main()
