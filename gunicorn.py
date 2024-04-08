import multiprocessing
import os
from dotenv import load_dotenv
load_dotenv()
import time

time.sleep(10)
name = "Gunicorn config for FastAPI"

current_dir = os.getcwd()
accesslog = current_dir + os.sep + "gunicorn-access.log"
errorlog = current_dir + os.sep + "gunicorn-error.log"

bind = "0.0.0.0:8000"

worker_class = "uvicorn.workers.UvicornWorker"
workers = multiprocessing.cpu_count () * 2 + 1
worker_connections = 1024
backlog = 2048
max_requests = 5120
timeout = 1200
keepalive = 20

debug = os.environ.get("debug", "false") == "true"
reload = debug
preload_app = False
daemon = False

