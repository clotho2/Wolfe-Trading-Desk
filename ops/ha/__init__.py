# path: ops/ha/__init__.py
from .leader import RedisLeaderElector, LeaderStatus, set_leader, get_leader
