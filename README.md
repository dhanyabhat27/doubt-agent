# Student Doubt Classification Agent (code version 4.2)

A student types a doubt. The agent finds the subject (scikit-learn), routes it (LangGraph),
asks Gemini to explain it (with Google Search when allowed), and lists links to read more.
Exam and admin questions go to faculty. Class notes are an offline fallback.

## Run it on your laptop (Windows)
```
cd C:\faiproj\doubt_agent
pip install -r requirements.txt
python test_agent.py
python -m streamlit run app.py
```
Use `python -m streamlit` because the plain `streamlit` command may not be on your PATH.

## The API key (one-time setup, no terminal needed afterwards)
1. Get a key at aistudio.google.com ("Get API key").
2. In the project folder, make a folder called `.streamlit` (it may already exist).
3. Inside it, create a file called `secrets.toml` with exactly one line:
   ```
   GEMINI_API_KEY = "paste-your-key-here"
   ```
4. Run the app again. The key is now remembered every time. No terminal command is needed.

NEVER paste the key into agent.py, a chat, or GitHub. `.gitignore` already keeps
`secrets.toml` out of GitHub. If a key was ever shared by accident, delete it in
Google AI Studio and make a new one.

Without a key the app still works: it shows the class notes (offline fallback) and the links.

## Optional settings (add as extra lines in secrets.toml, or in the Secrets box online)
- `GEMINI_MODEL = "model-name"` : force one Gemini model name
- `USE_SEARCH = "0"` : skip Google Search, which makes answers faster
The app shows which model answered and how many seconds it took, so you can see what is slow.

## Put it online (Streamlit Community Cloud, free)
1. Make a free account at github.com. Click New repository, name it (for example doubt-agent), Public.
2. Click "uploading an existing file". Drag in: agent.py, app.py, train_data.csv,
   requirements.txt, test_agent.py, README.md, .gitignore, the notes folder and
   the .streamlit folder containing ONLY config.toml. Do NOT upload secrets.toml, venv or __pycache__.
   Click Commit changes.
3. Go to share.streamlit.io, sign in with GitHub, click Create app (or New app).
4. Pick your repository, branch main, main file path app.py.
5. Open Advanced settings. Choose Python 3.12. In Secrets paste:
   ```
   GEMINI_API_KEY = "paste-your-key-here"
   ```
6. Click Deploy. In a few minutes you get a public link. Put it in your report.

## Changing the online app later
Edit the file on your laptop, then upload it to the same GitHub repository again
(Add file > Upload files, same name, Commit changes). The online app updates by itself in
a minute or two. If it does not, open the app, click Manage app, then Reboot.
Free apps sleep when unused: open the link a few minutes before showing it in class.

## Files
- agent.py: classifier, notes fallback, Gemini call, link builder, LangGraph router
- app.py: the screen
- train_data.csv: about 90 example questions with subject labels
- notes/: class notes (offline fallback)
- test_agent.py: 12 tests, prints a pass/fail table
- requirements.txt: libraries to install
- .streamlit/config.toml: theme colours
