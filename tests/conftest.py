import os
import tempfile

# Settings are read when `app` is first imported, so point them at a throwaway database first.
_tmp = tempfile.mkdtemp(prefix="notifaybers-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["SCHEDULER_LOCK_PATH"] = f"{_tmp}/scheduler.lock"
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ADMIN_USERNAME", "tester")
os.environ.setdefault("VAPID_PRIVATE_KEY_PATH", f"{_tmp}/none.pem")
