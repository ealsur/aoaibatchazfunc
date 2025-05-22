
# Azure Functions: Blob Batch Monitor

This project contains two Azure Functions for monitoring blobs and processing batch jobs using the OpenAI (Azure OpenAI) Batch API.

## Required permissions

The Azure OpenAI account requires Service-Managed Identity enabled and RBAC access permissions to the Azure Storage account. See the [official documentation](https://learn.microsoft.com/azure/ai-services/openai/how-to/batch-blob-storage?tabs=python#azure-blob-storage-configuration) for detailed steps.

## Required Configuration (Application Settings)
Add the following settings to your Azure Functions App (in the Azure Portal or in `local.settings.json` for local development):

| Setting Name             | Description                                                                 |
|------------------------- |-----------------------------------------------------------------------------|
| `OPENAI_ENDPOINT`        | The endpoint for your (Azure) OpenAI resource.                              |
| `OPENAI_API_KEY`         | The API key for your (Azure) OpenAI resource.                               |
| `BATCH_OUTPUT_CONTAINER` | The name of the blob container where batch outputs are stored.              |
| `BATCH_RETRY_DELAY`      | (Optional) Delay in seconds before retrying unfinished batch jobs. Defaults to `30`. |
| `BlobStorageConnection`  | Connection string for the Azure Storage account with the blob and queue.    |

Example for `local.settings.json`:
```json
{
  "IsEncrypted": false,
  "Values": {
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AzureWebJobsStorage": "<your-storage-connection-string>",
    "BlobStorageConnection": "<your-storage-connection-string>",
    "OPENAI_ENDPOINT": "<your-openai-endpoint>",
    "OPENAI_API_KEY": "<your-openai-key>",
    "BATCH_OUTPUT_CONTAINER": "batch-output",
    "BATCH_RETRY_DELAY": "30"
  }
}
```

## Function Descriptions

### 1. BlobMonitor (Blob Trigger)
- **Trigger:** Runs when a new blob is added to the `batch-input` container.
- **Action:**
  - Calls the OpenAI Batch API to start a batch job for the new blob.
  - Enqueues the batch job ID to the `monitorjobs` queue for monitoring.

### 2. QueueMonitor (Queue Trigger)
- **Trigger:** Runs when a message (batch job ID) is added to the `monitorjobs` queue.
- **Action:**
  - Checks the status of the batch job using the OpenAI Batch API.
  - If the job is not complete, waits for `BATCH_RETRY_DELAY` seconds and re-enqueues the job ID for another check.
  - If the job is complete (or failed/canceled), logs the output and error blob locations.

---

**Note:**
- The queue and blob container names are hardcoded as `monitorjobs` and `batch-input` respectively. Update the code if you need to change them.