from celery import Celery
from celery.utils.log import get_task_logger# Initialize celery
from kombu import Queue
from kombu.entity import Exchange
from azure_storage_account.file_operations import azure_storage_account
from image_operation.alignment import align_images_azure, align_images_cv2
from image_operation.acord_form_image import find_acord_form_version
from ocr.provision_functions import provision_form_in_db

CELERY_QUEUE_DEFAULT                        = 'tasks_queue_image_alignment'
CELERY_QUEUE_IMAGE_ALIGNMENT                = 'tasks_queue_image_alignment'
CELERY_QUEUE_ADD_NEW_FORM                   = 'tasks_queue_add_new_form'
CELERY_QUEUE_DETECT_FORM_VERSION_AND_PAGE   = 'tasks_queue_detect_form_version_and_page'

celery_app = Celery('tasks', broker='pyamqp://guest:guest@127.0.0.1:5672//')

tasks_exchange = Exchange('tasks_exchange', type='direct')
celery_app.conf["task_queues"] = (
    Queue('tasks_queue_image_alignment', tasks_exchange, routing_key= CELERY_QUEUE_IMAGE_ALIGNMENT),
    Queue('tasks_queue_add_new_form', tasks_exchange, routing_key= CELERY_QUEUE_ADD_NEW_FORM),
    Queue('tasks_queue_detect_form_version_and_page', tasks_exchange, routing_key= CELERY_QUEUE_DETECT_FORM_VERSION_AND_PAGE),
)

celery_app.conf["task_routes"] = {
    'tasks.image_alignment':{'queue': 'tasks_queue_image_alignment', 'routing_key': 'tasks_queue_image_alignment','exchange': tasks_exchange}, 
    'tasks.add_new_form':{'queue': 'tasks_queue_add_new_form', 'routing_key': 'tasks_queue_add_new_form', 'exchange': tasks_exchange},
    'tasks.detect_form_version_and_page':{'queue': 'tasks_queue_detect_form_version_and_page', 'routing_key': 'tasks_queue_detect_form_version_and_page', 'exchange': tasks_exchange},
    }

celery_app.conf['result_backend'] = 'rpc://'
celery_app.conf["task_default_exchange_type"] = 'direct'
celery_app.conf["task_default_queue"] = CELERY_QUEUE_DEFAULT
celery_app.conf["worker_send_task_events"] = True
celery_app.conf["worker_prefetch_multiplier"] = 1
celery_app.conf["task_acks_late"] = True

celery_log = get_task_logger(__name__)


def t_status(id):
    c = celery_app.AsyncResult(id)
    return c


@celery_app.task(queue="tasks_queue_image_alignment", exchange="tasks_queue_image_alignment")
def image_alignment(azure_storage_connection_string,container_name,image_path,template_path,accuracy):
    try:
        storage_obj = azure_storage_account(azure_storage_connection_string,container_name)
        if accuracy == "high":
            alignment_result = align_images_azure(image=image_path,template=template_path,stroage_obj=storage_obj)
        else:
            alignment_result = align_images_cv2(image=image_path,template=template_path,stroage_obj=storage_obj)
            # alignment_result = align_images_azure(image=image_path,template=template_path,stroage_obj=storage_obj)
            
        return alignment_result
    
    except Exception as e:
        celery_log.info(e)
        return False


@celery_app.task(queue="tasks_queue_add_new_form", exchange="tasks_queue_add_new_form")
def add_new_form(input_path,server):
    try:
        provision_status, acordFormVersion, error_msg = provision_form_in_db(input_path,server)
        data_dict={"provision_status":provision_status,"acordFormVersion":acordFormVersion,"error_msg":error_msg}
        return data_dict
    
    except Exception as e:
        celery_log.info(e)
        return {"Status":False,"error_msg":"Internal Server Error"}
    

@celery_app.task(queue="tasks_queue_detect_form_version_and_page", exchange="tasks_queue_detect_form_version_and_page")
def detect_form_version_and_page(azure_storage_connection_string,container_name,image_path):
    storage_obj = azure_storage_account(azure_storage_connection_string,container_name)
    acord_form_version_and_page = find_acord_form_version(image=image_path,stroage_obj=storage_obj)
    return acord_form_version_and_page
