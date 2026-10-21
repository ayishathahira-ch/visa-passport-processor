# Host the public demo for free on Hugging Face Spaces

A Docker Space runs this repo's `Dockerfile` and gives you a public URL such as
`https://huggingface.co/spaces/<your-username>/visa-passport-processor`. Put that link in your GitHub README and profile.

1. Create an account at huggingface.co, then **New Space**: name `visa-passport-processor`, SDK **Docker** (Blank template), visibility **Public**.
2. In the new Space, open **Settings → Variables and secrets** and add a **Variable**: `DEMO_MODE` = `1`.
   (Do not add `API_KEY` or `GEMINI_API_KEY` for the public demo.)
3. Put this block at the very top of the `README.md` **in the Space repo only** (GitHub's README does not need it):

   ```yaml
   ---
   title: Visa Passport Processor
   emoji: 🛂
   sdk: docker
   app_port: 5000
   pinned: false
   ---
   ```
4. Push the project files to the Space:

   ```bash
   git clone https://huggingface.co/spaces/<your-username>/visa-passport-processor hf-space
   cp -r visa_processor samples requirements.txt Dockerfile README.md hf-space/
   cd hf-space   # add the YAML block above to the top of README.md, then:
   git add . && git commit -m "Deploy demo" && git push
   ```
5. Wait for the build (a few minutes). Open the Space URL and click **Try valid sample**.

Notes
- In `DEMO_MODE` the n8n endpoint `/process-passport` is switched off; only the demo page and `/demo/process` are exposed, with a per-visitor rate limit.
- Free Spaces sleep when idle, so the first visit after a while may take a minute.
- Uploaded files are processed in memory/temp and deleted immediately, and the page asks visitors to use fictional passports only.
