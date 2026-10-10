# n8n workshop | HPE Private Cloud AI

Files for a document-question-answering workshop using **n8n**, **Qdrant**, **MLIS** and **Open WebUI** on HPE Private Cloud AI (PCAI).

The Helm packages and the workflow/pipeline files in this repository are the supplied workshop artifacts. They are kept **unchanged**. Cluster-specific URLs, models, passwords and collection names must be configured after import.

## Workshop files

| File | Purpose |
| --- | --- |
| [`helm/n8n-0.4.0.tgz`](helm/n8n-0.4.0.tgz) | n8n Helm chart with PostgreSQL. |
| [`helm/open-webui-8.12.2-2-pcai.tgz`](helm/open-webui-8.12.2-2-pcai.tgz) | Open WebUI chart, including the Pipelines dependency. |
| [`helm/qdrant-1.14.0.tgz`](helm/qdrant-1.14.0.tgz) | Qdrant Helmchart. |
| [`n8n/PCAI_RAG_ALL_IN_ONE.json`](n8n/PCAI_RAG_ALL_IN_ONE.json) | n8n workflow: PDF upload and document chat. |
| [`open-webui/pcai_document_rag_no_auth.py`](open-webui/pcai_document_rag_no_auth.py) | Open WebUI Pipeline that calls the n8n Chat Trigger (no Basic Auth). |

## Before starting

- Access to a PCAI namespace where the two charts can be installed; suitable persistent storage for PostgreSQL and Open WebUI.
- Qdrant deployed and reachable from n8n (not included in these files).
- An **embedding model** and a **chat/instruct model** running in MLIS, both exposing the OpenAI-compatible endpoints needed by the workflow. Save their deployment URLs, model IDs and required API tokens.
- Admin access to n8n and Open WebUI. Use a different Helm release and external hostname for each installation.

## Setup at a glance

1. **Deploy the charts.** In PCAI, import the TGZ files as frameworks and install them in the intended namespace(s). Open the n8n chart's `values.yaml` before deployment to review `owner.email`, `owner.password`, `ezua.virtualService.endpoint`, persistence and database settings. **Replace the demo password** and use a unique hostname. The initial email/password are for the n8n web login, not for Qdrant or MLIS.
2. **Check your internal endpoints.** A Kubernetes Service normally follows `http://<service-name>.<namespace>.svc.cluster.local:<service-port>`. Here, `namespace` is the PCAI project/Kubernetes namespace. Use the **actual** Service name and port reported by the cluster. For OpenAI-compatible MLIS endpoints, use `http://<model-service>.<namespace>.svc.cluster.local/v1` **only after confirming the Service, port and routing work**. Obtain the actual model ID from `/v1/models`.
3. **Connect Qdrant.** Find its Service name, namespace and port with `kubectl get svc -n <namespace>`. Set the Qdrant API credential to `http://<qdrant-service>.<namespace>.svc.cluster.local:<service-port>` (port `6333` is common, but check yours). Use the **base URL**, without `/collections` or `/dashboard`; enter an API key only if Qdrant requires one.
4. **Import the JSON into n8n.** Recreate/assign the Qdrant credential, embedding credential and LLM credential in the imported nodes. Select a Qdrant collection with a vector size matching the embedding model. Use the **same embedding model and collection for INSERT and RETRIEVE**.
5. **Upload a text-based PDF.** Run `UPLOAD PDF - n8n Form`, submit a PDF and check `Qdrant - INSERT PDF chunks` and its execution result. Verify points in Qdrant.
6. **Test and publish the chat.** Use `TEST CHAT - Open chat in n8n` for an editor test. Enable its public/embedded chat mode and **Publish** the workflow to register the production webhook. Test with a **POST**, not a browser GET.
7. **Connect Open WebUI.** Import the Python file from **Admin Panel > Settings > Pipelines**. In its Valves, replace `N8N_CHAT_URL` with the **actual production Chat Trigger URL** from *this* n8n instance. Keep TLS verification on if its certificate is trusted; otherwise configure the internal CA. Open a new chat and choose **PCAI Document RAG**.

### Endpoint examples

```text
Qdrant:       http://<qdrant-service>.<namespace>.svc.cluster.local:<service-port>
Embedding:    http://<embedding-service>.<namespace>.svc.cluster.local/v1
Chat model:   http://<llm-service>.<namespace>.svc.cluster.local/v1
n8n webhook:  https://<n8n-host>/webhook/<chat-trigger-id>/chat
Pipelines:    http://<pipelines-service>.<namespace>.svc.cluster.local:9099
```

Replace all angle-bracket placeholders with values from the customer's cluster. For Qdrant, `<qdrant-service>` is its **Kubernetes Service name**, `<namespace>` is the **PCAI project/namespace**, and `<service-port>` is the port exposed by that Service (often `6333`). Test `http://<qdrant-service>.<namespace>.svc.cluster.local:<service-port>/collections` from a pod that can reach Qdrant, but enter only the base URL in the n8n credential. The `svc.cluster.local` pattern does **not** guarantee that every MLIS/Knative deployment exposes direct Service routing; confirm with `kubectl get svc -n <namespace>`.

### Notes from the supplied workflow

- Both Qdrant vector-store nodes actually select the collection **`anywhere`**. Some sticky notes and the final upload-success message say **`pcai_n8n_pdf_demo`**. Those messages are not the active node settings. Use the collection selected in INSERT and RETRIEVE, or change both to a new workshop collection.
- The JSON contains model IDs and credential *references* from the original instance. Recreate/select working credentials and replace the model IDs for the customer's MLIS deployments after importing; the JSON is **not** a portable credential backup.
- The Python Pipeline contains a sample n8n hostname and webhook ID. **Change `N8N_CHAT_URL` in Valves** for every customer. It sends an unauthenticated request and is intended for a controlled demo; secure the webhook before broader exposure.
- The Open WebUI chart's existing `ezua.virtualService.endpoint` example may conflict with another installation. Change it during import to a unique hostname.

For the full customer procedure, see the **separate Overleaf guide** supplied with this workshop. Keep actual API keys, login passwords, and private cluster configuration out of a public repository.

## File integrity

Checksums for the four source artifacts are provided in [`SHA256SUMS.txt`](SHA256SUMS.txt). The Helm TGZ files were copied as supplied, not rebuilt or edited.
