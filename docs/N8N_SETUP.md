# n8n setup, step by step (for beginners)

n8n is the "glue": it watches Gmail, sends the passport to this API, and writes the answer to Google Sheets.
The workflow is ready-made in [`n8n/workflow.json`](../n8n/workflow.json); you only connect your own accounts.

## 0. What you need running

| Piece | Command | Check |
|---|---|---|
| This API | `API_KEY=mysecret python -m visa_processor.api` | open http://127.0.0.1:5000/health |
| n8n | `npx n8n` (needs Node.js 20+) | open http://localhost:5678 |

Keep both terminals open. Pick any long random string for `API_KEY` and remember it.

## 1. Google connection (one time)

1. In Google Cloud Console create a project, enable the **Gmail API** and **Google Sheets API**, and create an **OAuth client ID** (type *Desktop app*). Download it as `credentials.json` into the project folder.
2. Run `python scripts/setup_google.py --create-sheet`. A browser window asks you to allow access. When it finishes, copy the `spreadsheet_id` it prints (also saved in `sheet_config.json`).

## 2. Import the workflow

1. In n8n click **Workflows → Add workflow → ⋯ menu → Import from file** and choose `n8n/workflow.json`.
2. You will see 6 nodes: **Gmail Trigger → If subject contains visa → Get Email with Attachments → Prepare payload → Extract passport data → Append row in sheet**.

## 3. Fill in the three things that are yours

| Node | What to change |
|---|---|
| **Gmail Trigger** and **Get Email with Attachments** | Open the node → *Credential* → create a **Gmail OAuth2** credential (n8n shows the exact steps and the redirect URL to paste into Google Cloud) |
| **Extract passport data** | Under *Headers*, replace `PASTE_YOUR_API_KEY_HERE` with your `API_KEY` |
| **Append row in sheet** | Create a **Google Sheets OAuth2** credential, and replace `PASTE_YOUR_SHEET_ID_HERE` with your `spreadsheet_id` |

> If n8n runs in Docker and the API runs on your machine, change the URL in **Extract passport data** from `127.0.0.1` to `host.docker.internal`.

## 4. Test it

1. Email the connected Gmail account with the subject `Work visa application` and attach `samples/sample_passport.png`.
2. In n8n open the **Gmail Trigger** node and click **Fetch Test Event**, then **Execute workflow**.
3. Every node should turn green and a new row appears in your Google Sheet.
4. When it works, switch the workflow to **Active** (top right).

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ECONNREFUSED` in *Extract passport data* | The API is not running, or Docker needs `host.docker.internal` (see above) |
| `401 Unauthorized` | The header value does not match the `API_KEY` the API was started with |
| `No passport attachment found` | Attach a PDF/JPG/PNG; inline signature images are ignored |
| Nothing triggers | The trigger reads **unread** mail only; mark the test mail unread |
| `422 OCR found no text` | The scan is too blurry or the file is empty |
| `Is Valid` = false | Not an error: a required field is missing or the passport is expired (see `warnings`) |

> The workflow file was written to match n8n's current node formats, but n8n changes over time. If an import complains about a node version, recreate that node by hand with the same settings. The API itself is fully covered by tests.
