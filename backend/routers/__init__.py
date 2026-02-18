"""
Backend Routers Package

This package contains modularized API routers for the DVBC ERP system.
Each router handles a specific domain of functionality.
"""

from . import deps
from . import models
from . import auth
from . import leads
from . import projects
from . import meetings
from . import stats
from . import security
from . import users
from . import kickoff
from . import ctc
from . import employees
from . import attendance
from . import expenses
from . import hr
from . import masters
from . import sow_masters
from . import enhanced_sow

__all__ = [
    "deps",
    "models", 
    "auth",
    "leads",
    "projects",
    "meetings",
    "stats",
    "security",
    "users",
    "kickoff",
    "ctc",
    "employees",
    "attendance",
    "expenses",
    "hr",
    "masters",
    "sow_masters",
    "enhanced_sow",
]
