# fastapi-tator, Apache-2.0 license
# Filename: app/redis_process.py
# Description: Run Redis process tasks

import redis
from rq import Queue

import time
from datetime import datetime

import app.ops.worker as worker_tasks
from app.ops.models import SDCATModel

# Set up Redis connection
redis_conn = redis.Redis(host='localhost', port=6379, db=0)

# Check if the Redis connection is working
redis_conn.ping()

sdcat_task_processor_q = Queue(name='default', connection=redis_conn)

def process_sdcat(sdcat_process_task: SDCATModel):
    now = datetime.now()
    timestamp = int(time.mktime(now.timetuple()))
    sdcat_process_task.id = f"{sdcat_process_task.images}_{timestamp}"
    job_ai = sdcat_task_processor_q.enqueue(worker_tasks.sdcat_detect, sdcat_process_task, result_ttl=-1)
    return {"job_id": job_ai.get_id()}
    # return {"AI Feedback Process Job Status": job_ai.get_status()}