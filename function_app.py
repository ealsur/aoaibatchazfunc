
import azure.functions as func
import time
import logging
import os
from openai import AzureOpenAI
from urllib.parse import urlparse

OPENAI_ENDPOINT = os.environ.get("OPENAI_ENDPOINT")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
BATCH_OUTPUT_CONTAINER = os.environ.get("BATCH_OUTPUT_CONTAINER")
BATCH_RETRY_DELAY = int(os.environ.get("BATCH_RETRY_DELAY", "30"))
client = AzureOpenAI(api_key=OPENAI_API_KEY, azure_endpoint=OPENAI_ENDPOINT, api_version="2025-04-01-preview")

app = func.FunctionApp()

@app.function_name(name="BlobMonitor")
@app.blob_trigger(arg_name="myblob", path="batch-input", connection="BlobStorageConnection") 
@app.queue_output(arg_name="outputQueueItem", queue_name="monitorjobs", connection="BlobStorageConnection")
def BlobTrigger(myblob: func.InputStream, outputQueueItem: func.Out[str]):
    blob_url = myblob.uri
    parsed = urlparse(blob_url)
    output_folder_url = f"{parsed.scheme}://{parsed.netloc}/{BATCH_OUTPUT_CONTAINER}"
    logging.info(f"Detected new file: {blob_url}. Using output folder: {output_folder_url}")
    try:
        batch_response = client.batches.create(
            input_file_id=None,
            endpoint="/chat/completions",
            completion_window="24h",
            extra_body={
                "input_blob": blob_url,
                "output_folder": {
                    "url": output_folder_url,
                }
            }
        )
        logging.info(f"Batch API succeeded with id: {batch_response.id}")
        outputQueueItem.set(str(batch_response.id))
    except Exception as e:
        # Can be used to handle throttling on a deadletter queue
        logging.error(f"Batch API error. {e}.")


@app.function_name(name="QueueMonitor")
@app.queue_trigger(arg_name="azqueue", queue_name="monitorjobs", connection="BlobStorageConnection")
@app.queue_output(arg_name="outputQueueItem", queue_name="monitorjobs", connection="BlobStorageConnection")
def QueueTrigger(azqueue: func.QueueMessage, outputQueueItem: func.Out[str]):
    batch_job_id = azqueue.get_body().decode('utf-8')
    batch_response = client.batches.retrieve(batch_job_id)
    logging.info(f"Batch job {batch_job_id} status: {batch_response.status}")
    if batch_response.status not in ("completed", "failed", "canceled"):
        logging.info(f"Batch job {batch_job_id} is still processing. Sleeping for {BATCH_RETRY_DELAY} seconds before re-enqueueing.")
        time.sleep(BATCH_RETRY_DELAY)
        outputQueueItem.set(str(batch_response.id))
    else:
        logging.info(f"Batch job {batch_job_id} reached a final state. Output: {batch_response.output_blob}. Error: {batch_response.error_blob}")
