# StudyAI: AI Study Companion

StudyAI is an AI-powered study companion designed to help students understand difficult topics, revise efficiently, and prepare for exams in one place.

## Why This Project Was Made

Students often spend a lot of time searching for explanations, converting notes into revision material, planning study time, and checking their understanding. StudyAI brings these tasks into one simple interface so students can:

- understand problems through step-by-step guidance;
- scan handwritten or printed questions;
- turn notes into flashcards and quizzes;
- create a study plan based on an exam date;
- summarize long study material;
- collect formulas and important rules;
- understand difficult topics in simple language;
- review previously solved problems.

## Features

| Tool | How it helps students |
|---|---|
| Solve | Provides guided solutions for math, science, history, and general questions |
| Scan Image | Reads a question from an uploaded image and extracts its text |
| Flashcards | Converts notes into quick revision cards |
| Quiz | Creates topic-based multiple-choice practice questions with explanations |
| Study Planner | Creates a plan based on the exam date and daily study hours |
| Summarizer | Extracts the most important points from long notes |
| Formula Sheet | Collects formulas, equations, definitions, and important rules |
| Explain ELI5 | Explains complex topics using simple language and everyday examples |
| History | Stores and displays recently solved problems |

## How to Run the Project with Anaconda Prompt

### First-time setup

```bat
cd C:\gauth-clone
conda create -n studyai python=3.14 -y
conda activate studyai
pip install -r requirements.txt
```

Create a Gemini API key at <https://aistudio.google.com/apikey>.

Create or edit the `.env` file in the project root:

```env
GEMINI_API_KEY=your_new_key_here
GEMINI_MODEL=gemini-3.6-flash
```

Keep `.env` local—never commit it or share the Gemini API key. For production,
also set a unique `DJANGO_SECRET_KEY`, set `DJANGO_DEBUG=False`, and configure
`DJANGO_ALLOWED_HOSTS` for your deployment. Development generates a temporary
Django secret automatically if `DJANGO_SECRET_KEY` is not set.

### Start the Django application

Keep this Anaconda Prompt open:

```bat
cd C:\gauth-clone
conda activate studyai
cd backend
python manage.py migrate
python manage.py runserver
```

Open the Django application at <http://127.0.0.1:8000/>.

The home page redirects to login. Create an account at `/signup/`, then use the authenticated dashboard. The API health check is available at <http://127.0.0.1:8000/api/history/>.

### Optional legacy Streamlit interface

The main interface is now served by Django. The previous Streamlit interface is still available for compatibility if you want to run it separately:

Open a second Anaconda Prompt:

```bat
cd C:\gauth-clone
conda activate studyai
streamlit run frontend\app.py
```

Open the legacy interface at <http://localhost:8501>.

For the new Django interface, only the Django server is required. The Streamlit interface requires both processes to remain running.

## Important Security Notes

- Never share the Gemini API key or commit it to GitHub.
- If the key is exposed, revoke it in Google AI Studio and create a new one.
- The `.env` file is ignored by Git and should remain local.
- The Django application runs on its own; only the optional legacy Streamlit interface needs a separate process.

## Common Problems

**`EnvironmentNameNotFound: studyai`**

Create the environment first:

```bat
conda create -n studyai python=3.14 -y
conda activate studyai
```

**Django shows a 404 at `/`**

The current project includes a Django homepage. Restart the server and open `http://127.0.0.1:8000/`. The API health check is at `/api/history/`.

**The legacy Streamlit frontend says “Backend error”**

Make sure the Django terminal is still running with `python manage.py runserver`.

## Technology

- Django templates and session-based authentication
- Django REST API backend
- Optional Streamlit legacy interface
- Google Gemini for AI responses and image OCR
- SQLite for local history

`requirements.txt` contains the packages needed to install and run the project.
