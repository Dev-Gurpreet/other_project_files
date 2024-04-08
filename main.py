from fastapi import FastAPI,status,File, Form, UploadFile,Header,Depends 
from typing import Dict, Optional
from fastapi.responses import ORJSONResponse
import uuid,os,json
from ocr.provision_functions import provision_form_in_db
from image_operation.alignment import align_images_azure
from starlette.config import Config
from azure_storage_account.file_operations import azure_storage_account
import requests
import json
from pydantic import BaseModel
from app.celery_worker import image_alignment, t_status, add_new_form, detect_form_version_and_page
import time
from location_operation.find_location import find_cities_from_text

app = FastAPI(title="WinsurTech Document Reader",
        version="0.1.0",
        description="Document Reader REST API makes it possible to extract data from editable, flattened and scanned ACCORD forms as well as images. Apart from ACCORD forms, any other PDF forms are also supported. The data is converted into simple to consume JSON output.",
        docs_url = None,
        edoc_url = None)


class pdf_arguments(BaseModel):
    filename: str
    pdf_data_str:str
    server:str
    
    
@app.post("/v1/get_pdf_data")
async def get_form_data(pdf_file: UploadFile = File(...), server: str = Form(...)):
    try:
        server=str(server).lower().strip()
        if server =="":
            return {"Status":False,"error_msg":"server parameter is missing"}
    except:
        return {"Status":False,"error_msg":"server parameter is missing"}
    
    unique_filename = str(uuid.uuid4())+'.pdf'
    directory = os.getcwd() + os.sep + 'pdf_files'  

    input_path = directory + os.sep + unique_filename 
    try:
        os.makedirs(directory, exist_ok=True)
    except OSError as error:
        print("Directory '%s' can not be created" % directory)
    input_path = directory + os.sep + unique_filename

    contents = await pdf_file.read()
    f = open(f"{input_path}", 'wb')
    f.write(contents)
    f.close()

    task_info =  add_new_form.delay(input_path,server)
    time.sleep(2)
    task_result = t_status(task_info.task_id)
    while task_result.status == "PENDING":
        time.sleep(1)
        task_result = t_status(task_info.task_id)
    
    if task_result.status == "SUCCESS":
        data_dict = task_result.result
        if data_dict is not None:
            return data_dict
        else:
            return {"Status": False, "error_msg": "Unexpected result from the task"}
    else:
        return {"Status": False, "error_msg": "Task execution failed"}


@app.post("/v1/align-image")
def provision_form(image_path:Optional[str] = Form(""), template_path:Optional[str] = Form(""), server:Optional[str] = Form(""), accuracy:Optional[str] = Form("")):
    try:
        if image_path != "" and template_path !="" and server != "":
            dir_path = os.getcwd()
            config = Config(dir_path + os.sep + '.env')
            if server.lower().strip() == "test":
                azure_storage_connection_string = config('AZURE_STORAGE_CONNECTION_STRING_TEST')
                container_name = config('AZURE_API_FILE_CONTAINER_TEST')

            elif server.lower().strip() == "live":
                azure_storage_connection_string = config('AZURE_STORAGE_CONNECTION_STRING_LIVE')
                container_name = config('AZURE_API_FILE_CONTAINER_LIVE')
            
            elif server.lower().strip() == "live2":
                azure_storage_connection_string = config('AZURE_STORAGE_CONNECTION_STRING_LIVE2')
                container_name = config('AZURE_API_FILE_CONTAINER_LIVE2')
            
            else:
                azure_storage_connection_string = ""
                container_name = ""

            if azure_storage_connection_string != "" or  container_name != "":
                task_align = image_alignment.delay(azure_storage_connection_string,container_name,image_path,template_path, accuracy)
                time.sleep(2)
                task_result = t_status(task_align.task_id)
                while task_result.status == "PENDING":
                    time.sleep(1)
                    task_result = t_status(task_align.task_id)

                alignment_result = task_result.result
                if alignment_result != None:
                    return alignment_result
                
        return False

    except Exception as e:
        return False
    

@app.post("/v1/detect-acord-form")
def detect_acord_form_and_page_no(image_path:Optional[str] = Form(""), server:Optional[str] = Form("")):
    try:
        if image_path != "" and server != "":
            dir_path = os.getcwd()
            config = Config(dir_path + os.sep + '.env')
            if server.lower().strip() == "test":
                azure_storage_connection_string = config('AZURE_STORAGE_CONNECTION_STRING_TEST')
                container_name = config('AZURE_API_FILE_CONTAINER_TEST')

            elif server.lower().strip() == "live":
                azure_storage_connection_string = config('AZURE_STORAGE_CONNECTION_STRING_LIVE')
                container_name = config('AZURE_API_FILE_CONTAINER_LIVE')
            
            elif server.lower().strip() == "live2":
                azure_storage_connection_string = config('AZURE_STORAGE_CONNECTION_STRING_LIVE2')
                container_name = config('AZURE_API_FILE_CONTAINER_LIVE2')
            
            else:
                azure_storage_connection_string = ""
                container_name = ""

            if azure_storage_connection_string != "" or  container_name != "":
                task_version = detect_form_version_and_page.delay(azure_storage_connection_string,container_name,image_path)
                time.sleep(2)
                task_result = t_status(task_version.task_id)
                while task_result.status == "PENDING":
                    time.sleep(1)
                    task_result = t_status(task_version.task_id)

                version_result = task_result.result
                if version_result != None:
                    return version_result
                
        return ("","",False)

    except Exception as e:
        return ("","","server error")


@app.post("/v1/detect-cities-from-text")
def detect_cities_from_text(text:Optional[str] = Form("")):
    try:
        cities_list = find_cities_from_text(text=text)
        return cities_list
    except:
        return list()