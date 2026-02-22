"""
Router Package Initialization
All routers are imported and exported from here.
"""

# Core dependencies
from . import deps
from . import models
from . import auth

# Core routers
from . import users
from . import leads
from . import projects
from . import meetings

# HR Module
from . import employees
from . import attendance
from . import hr
from . import ctc
from . import letters
from . import expenses

# Sales Module
from . import sales
from . import enhanced_sow
from . import sow_masters
from . import masters
from . import kickoff

# Finance Module
from . import payments
from . import project_payments
from . import payroll

# Analytics & Reports
from . import analytics
from . import stats
from . import project_pnl
from . import reports

# Administration
from . import role_management
from . import permission_config
from . import department_access
from . import security
from . import roles
from . import settings

# Communication
from . import chat
from . import ai_assistant
from . import email_actions
from . import documentation
from . import audio_samples

# New Phase 2 Routers
from . import travel
from . import sow_legacy
from . import agreements
from . import tasks
from . import notifications
from . import approvals
from . import quotations
from . import timesheets
from . import consultants

__all__ = [
    # Core
    'deps', 'models', 'auth', 'users', 'leads', 'projects', 'meetings',
    # HR
    'employees', 'attendance', 'hr', 'ctc', 'letters', 'expenses',
    # Sales
    'sales', 'enhanced_sow', 'sow_masters', 'masters', 'kickoff',
    # Finance
    'payments', 'project_payments', 'payroll',
    # Analytics
    'analytics', 'stats', 'project_pnl', 'reports',
    # Admin
    'role_management', 'permission_config', 'department_access', 'security', 'roles', 'settings',
    # Communication
    'chat', 'ai_assistant', 'email_actions', 'documentation', 'audio_samples',
    # Phase 2
    'travel', 'sow_legacy', 'agreements', 'tasks', 'notifications',
    'approvals', 'quotations', 'timesheets', 'consultants'
]
