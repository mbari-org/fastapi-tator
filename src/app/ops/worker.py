# worker.py
import redis
from rq import Worker, Queue, Connection

from app.logger import info
from app.ops.models import SDCATModel


async def sdcat_detect(model: SDCATModel):
    """
    Process all images in a given directory
    :param model: model with criteria for the job
    """
    # Send a Slack message
    print(f"=====================>Processing images in {model.images}")
    pass

listen = ['default']

if __name__ == '__main__':
    redis_conn = redis.Redis(host='localhost', port=6379, db=0)
    task_queue = Queue(connection=redis_conn)
    with Connection(redis_conn):
        worker = Worker(map(Queue, listen))
        worker.work()
