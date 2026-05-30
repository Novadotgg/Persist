# Import tasks to ensure they register as actors on the default Dramatiq broker
from app.workers.tasks import classify_event_priority, generate_event_summary
