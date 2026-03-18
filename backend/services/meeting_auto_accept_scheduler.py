"""
Meeting Auto-Accept Scheduler
==============================

Automated scheduled job that runs hourly to auto-accept meetings
where the client hasn't responded within 24 hours.

Features:
- Hourly execution (configurable interval)
- Finds meetings with expired response tokens
- Auto-accepts them and updates status
- Notifies manager and scheduler

Usage:
    from services.meeting_auto_accept_scheduler import MeetingAutoAcceptScheduler
    
    # Start the scheduler
    scheduler = MeetingAutoAcceptScheduler(db)
    await scheduler.start()
    
    # Manual trigger
    results = await scheduler.run_now()
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class MeetingAutoAcceptScheduler:
    """
    Scheduled service to auto-accept meetings with expired response tokens.
    Runs hourly to check for meetings awaiting client response > 24 hours.
    """
    
    # Default: Run every hour
    DEFAULT_INTERVAL_HOURS = 1
    
    def __init__(self, db, interval_hours: int = None):
        """
        Initialize the scheduler.
        
        Args:
            db: MongoDB database connection
            interval_hours: Interval between checks (default: 1 hour)
        """
        self.db = db
        self.interval_hours = interval_hours if interval_hours is not None else self.DEFAULT_INTERVAL_HOURS
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_run: Optional[datetime] = None
        self._last_results: Optional[List[Dict]] = None
        self._total_processed: int = 0
    
    async def start(self):
        """Start the scheduler."""
        if self._running:
            logger.warning("Meeting auto-accept scheduler already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info(f"Meeting auto-accept scheduler started. Running every {self.interval_hours} hour(s)")
    
    async def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Meeting auto-accept scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        while self._running:
            try:
                # Calculate seconds until next run
                interval_seconds = self.interval_hours * 3600
                
                # Wait for the interval
                logger.info(f"Next auto-accept check in {self.interval_hours} hour(s)")
                await asyncio.sleep(interval_seconds)
                
                if not self._running:
                    break
                
                # Run the auto-accept process
                await self.run_now()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in meeting auto-accept scheduler: {e}")
                # Wait a bit before retrying on error
                await asyncio.sleep(300)  # 5 minutes
    
    async def run_now(self) -> List[Dict[str, Any]]:
        """
        Manually trigger the auto-accept process.
        
        Returns:
            List of auto-accepted meetings
        """
        logger.info("Running meeting auto-accept check...")
        
        now = datetime.now(timezone.utc)
        results = []
        
        try:
            # Find meetings that are:
            # - Status = SCHEDULED
            # - Token sent but not used
            # - Token expired (> 24h since sent)
            
            expired_meetings = await self.db.meetings.find({
                "status": "SCHEDULED",
                "client_token_used": False,
                "client_response_token": {"$ne": None},
                "invite_sent_at": {"$ne": None}
            }).to_list(100)
            
            for meeting in expired_meetings:
                # Check if token has expired (24h from invite sent)
                invite_sent = meeting.get('invite_sent_at')
                if isinstance(invite_sent, str):
                    invite_sent = datetime.fromisoformat(invite_sent.replace('Z', '+00:00'))
                
                # Check explicit expiry or calculate from invite time
                expires_at = meeting.get('client_token_expires_at')
                if expires_at:
                    if isinstance(expires_at, str):
                        expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                else:
                    # Default: 24h from invite sent
                    expires_at = invite_sent + timedelta(hours=24) if invite_sent else None
                
                if not expires_at or now <= expires_at:
                    continue  # Token not yet expired
                
                # Auto-accept the meeting
                state_entry = {
                    "from_state": "SCHEDULED",
                    "to_state": "AUTO_ACCEPTED",
                    "changed_by": "SYSTEM",
                    "changed_by_name": "Auto-Accept Scheduler",
                    "changed_at": now.isoformat(),
                    "reason": "No client response within 24 hours - automatically accepted"
                }
                
                update_result = await self.db.meetings.update_one(
                    {"id": meeting['id'], "status": "SCHEDULED"},  # Double-check status
                    {
                        "$set": {
                            "status": "AUTO_ACCEPTED",
                            "client_response": "AUTO_ACCEPTED",
                            "client_response_at": now.isoformat(),
                            "client_token_used": True
                        },
                        "$push": {"state_history": state_entry}
                    }
                )
                
                if update_result.modified_count > 0:
                    result = {
                        "meeting_id": meeting['id'],
                        "title": meeting.get('title', 'Untitled'),
                        "client_name": meeting.get('client_name', 'Unknown'),
                        "project_name": meeting.get('project_name', 'Unknown'),
                        "meeting_date": meeting.get('meeting_date'),
                        "invite_sent_at": meeting.get('invite_sent_at'),
                        "auto_accepted_at": now.isoformat(),
                        "status": "auto_accepted"
                    }
                    results.append(result)
                    
                    logger.info(f"Auto-accepted meeting {meeting['id']}: {meeting.get('title')}")
                    
                    # Send notification to scheduler (meeting creator)
                    await self._notify_auto_accept(meeting)
            
            self._last_run = now
            self._last_results = results
            self._total_processed += len(results)
            
            logger.info(f"Auto-accept check complete. Processed {len(results)} meeting(s)")
            
        except Exception as e:
            logger.error(f"Error in auto-accept process: {e}")
            raise
        
        return results
    
    async def _notify_auto_accept(self, meeting: Dict[str, Any]):
        """Send notification about auto-accepted meeting."""
        try:
            from services.meeting_notification_service import send_manager_notification
            
            # Notify the scheduler (meeting creator)
            scheduler_id = meeting.get('scheduled_by') or meeting.get('created_by')
            if scheduler_id:
                scheduler = await self.db.users.find_one({"id": scheduler_id}, {"_id": 0})
                if scheduler and scheduler.get('email'):
                    await send_manager_notification(
                        meeting=meeting,
                        manager_email=scheduler['email'],
                        manager_name=scheduler.get('full_name', 'Consultant'),
                        scheduled_by_name='you',
                        notification_type='AUTO_ACCEPTED'
                    )
                    logger.info(f"Auto-accept notification sent to {scheduler['email']}")
        except Exception as e:
            logger.error(f"Failed to send auto-accept notification: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            "running": self._running,
            "interval_hours": self.interval_hours,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "last_results_count": len(self._last_results) if self._last_results else 0,
            "total_processed": self._total_processed,
            "next_run_in_hours": self.interval_hours if self._running else None
        }


# Global scheduler instance
_meeting_auto_accept_scheduler: Optional[MeetingAutoAcceptScheduler] = None


def get_meeting_auto_accept_scheduler() -> Optional[MeetingAutoAcceptScheduler]:
    """Get the global scheduler instance."""
    return _meeting_auto_accept_scheduler


async def start_meeting_auto_accept_scheduler(db) -> MeetingAutoAcceptScheduler:
    """
    Start the global meeting auto-accept scheduler.
    
    Args:
        db: MongoDB database connection
        
    Returns:
        MeetingAutoAcceptScheduler instance
    """
    global _meeting_auto_accept_scheduler
    
    if _meeting_auto_accept_scheduler is not None:
        logger.warning("Meeting auto-accept scheduler already exists")
        return _meeting_auto_accept_scheduler
    
    _meeting_auto_accept_scheduler = MeetingAutoAcceptScheduler(db)
    await _meeting_auto_accept_scheduler.start()
    
    return _meeting_auto_accept_scheduler


async def stop_meeting_auto_accept_scheduler():
    """Stop the global meeting auto-accept scheduler."""
    global _meeting_auto_accept_scheduler
    
    if _meeting_auto_accept_scheduler:
        await _meeting_auto_accept_scheduler.stop()
        _meeting_auto_accept_scheduler = None
