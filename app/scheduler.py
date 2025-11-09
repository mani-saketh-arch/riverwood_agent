import os
import asyncio
import requests
from datetime import datetime, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

load_dotenv()

class DailyCallScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.base_url = os.getenv("BASE_URL", "http://localhost:8000")
        
        # Default call times (you can customize these)
        self.call_times = [
            "09:00:00",  # 9 AM
            "10:00:00",  # 10 AM
            "11:00:00",  # 11 AM
            "14:00:00",  # 2 PM
            "15:00:00",  # 3 PM
            "16:00:00",  # 4 PM
            "17:00:00",  # 5 PM
        ]
    
    def trigger_daily_calls(self, target_time: str):
        """Trigger calls for specific time slot"""
        try:
            print(f"🕐 Triggering calls for {target_time}")
            
            response = requests.post(
                f"{self.base_url}/call/initiate-daily-calls",
                params={"target_time": target_time}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Successfully initiated calls: {result.get('total_customers', 0)} customers")
            else:
                print(f"❌ Error initiating calls: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error in trigger_daily_calls: {e}")
    
    def schedule_calls_for_time(self, call_time: str):
        """Schedule calls for specific time"""
        hour, minute, second = call_time.split(":")
        
        # Add job for this specific time
        self.scheduler.add_job(
            self.trigger_daily_calls,
            trigger=CronTrigger(hour=int(hour), minute=int(minute)),
            args=[call_time],
            id=f"call_job_{call_time}",
            name=f"Daily calls at {call_time}",
            replace_existing=True
        )
        
        print(f"📅 Scheduled daily calls for {call_time}")
    
    def start(self):
        """Start the scheduler (runs every hour)."""
        print("🚀 Starting Hourly Call Scheduler...")

        # Run job every hour at minute 0
        self.scheduler.add_job(
            self.trigger_daily_calls,
            trigger=CronTrigger(minute=0),  # every hour, on the hour
            args=["hourly"],                # pass a simple label
            id="hourly_call_job",
            name="Hourly Customer Calls",
            replace_existing=True
        )

        # Add a lightweight health check every 30 minutes
        self.scheduler.add_job(
            self.health_check,
            trigger=CronTrigger(minute="*/30"),
            id="health_check",
            name="Scheduler Health Check",
            replace_existing=True
        )

        self.scheduler.start()
        print("✅ Scheduler started successfully! Calls will trigger every hour.")

    def health_check(self):
        """Periodic health check"""
        print(f"💓 Health check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 Active jobs: {len(self.scheduler.get_jobs())}")
    
    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        print("🛑 Scheduler stopped")

# For standalone usage
if __name__ == "__main__":
    scheduler = DailyCallScheduler()
    scheduler.start()
    
    try:
        # Keep the script running
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        scheduler.stop()