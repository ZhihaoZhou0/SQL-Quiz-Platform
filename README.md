# Restaurant SQL Quiz Platform

A live, authenticated SQL quiz built for **Duke University IDS 706 (Data Engineering)**. Students sign in, write SQL queries against a hosted PostgreSQL database, inspect the returned rows, and save their answers. The quiz contains **five questions worth four points each (20 points total)**. It also provides optional automatic feedback by comparing query results with reference results.

**Live quiz:** https://ids706-restaurant-sql-quiz.streamlit.app/  
**Source code:** https://github.com/ZhihaoZhou0/SQL-Quiz-Platform

## Features

- **Hosted PostgreSQL:** Restaurant data is stored in Supabase and queried live, rather than from a static example table in the interface.
- **Authentication:** Supabase Auth supports account creation and sign-in. Users who are not signed in cannot run SQL or save answers.
- **Interactive SQL quiz:** Each question includes a prompt, a SQL editor, a **Run SQL** button, and an expandable hint showing both the expected SQL and its expected result table.
- **Automatic feedback:** Running SQL displays the result table and checks it against the reference query's result set. The quiz shows per-question feedback and a score out of 20; it does **not** require matching the reference SQL text.
- **Saved answers:** **Save Answer** writes each authenticated user's SQL to PostgreSQL. Saved SQL is restored when the user signs in again.
- **GitHub Actions:** A workflow installs dependencies and tests a live database query using credentials supplied through GitHub Actions Secrets.

## Technology Stack

| Component | Technology | Purpose |
| --- | --- | --- |
| Web application | Python, Streamlit | Quiz interface and score display |
| Hosted database | Supabase PostgreSQL | Restaurant data and saved answers |
| Authentication | Supabase Auth | Sign-up, sign-in, and user identity |
| Database access | `psycopg2` | Execute SQL and persist answers |
| Data display/comparison | pandas | Render and compare query results |
| CI | GitHub Actions + GitHub Secrets | Automated live database connectivity test |
| Deployment | Streamlit Community Cloud | Publicly accessible quiz website |

## Quiz Questions

| # | Question | SQL concepts | Points |
| --- | --- | --- | ---: |
| 1 | Nearby Restaurants | `WHERE`, `ORDER BY` | 4 |
| 2 | Top Rated Restaurants | `ORDER BY`, `LIMIT` | 4 |
| 3 | Restaurant Prices with Tax | Arithmetic, `ROUND`, aliases | 4 |
| 4 | Restaurants by Cuisine | `COUNT`, `GROUP BY`, sorting | 4 |
| 5 | Highly Rated Restaurants | Filtering and sorting | 4 |
| | **Total** | | **20** |

Every question provides a hint with the **expected SQL and expected result**. Queries run against the hosted `restaurants` table.

## How to Use the Quiz

1. Open the [live quiz](https://ids706-restaurant-sql-quiz.streamlit.app/).
2. Create an account under **Sign Up**, or use **Sign In** if you already have an account. If email confirmation is required, follow the link sent to your email before signing in.
3. Expand a question and enter a PostgreSQL `SELECT` query.
4. Click **Run SQL** to execute the query and view the rows returned from Supabase. The application also displays **Correct / Incorrect** feedback based on the expected result.
5. Expand **Hint: Expected SQL and Result** to inspect the reference query and result table.
6. Click **Save Answer** to store your SQL answer for that question. Your saved SQL is available after you sign out and sign in again.
7. Review the **Quiz Summary** for saved-answer count, checked-answer count, correct answers, and your current score out of 20.

**Note:** Saved SQL answers persist in PostgreSQL, but automatic grading results and the score are **session-only**. After signing in again, click **Run SQL** to check your saved answers and rebuild the score. Running a query does not automatically save it; use **Save Answer** separately.

## Database Design

The Supabase project hosts two application tables:

- **`restaurants`** — quiz dataset with restaurant names, addresses, distance in miles, ratings, cuisine, average cost, and personal rank. The initial sample data is supplied in `init.sql`.
- **`quiz_answers`** — stores saved SQL by authenticated user and question. Relevant fields include `user_id`, `question_number`, `answer_sql`, `created_at`, and `updated_at`. Saving an answer again updates the existing answer for that user/question.

Student-entered queries are executed through the restricted PostgreSQL **`quiz_reader`** role, which has read access to the restaurant data but no permission to insert, update, or delete it. The Streamlit server uses a separate privileged database connection to load and save quiz answers. User identifiers are used to retrieve each user's saved answers.

## Project Files

| File | Role |
| --- | --- |
| `app.py` | Streamlit UI, Supabase Auth, questions, answer persistence, and grading |
| `quiz_db.py` | Restricted connection and execution of student SQL |
| `init.sql` | Restaurant database setup/sample data |
| `query.py` | Database-query example from the course lab |
| `test_quiz_connection.py` | Database connectivity test script |
| `requirements.txt` | Python dependencies |
| `.github/workflows/test.yml` | GitHub Actions database test |
| `.gitignore` | Prevents local secrets and virtual environment files from being committed |

## Run Locally

**Prerequisites:** Python 3.12 (recommended), a Supabase project with the required tables and data, and the appropriate database roles/permissions.

1. Clone the repository and open its folder:

   ```bash
   git clone https://github.com/ZhihaoZhou0/SQL-Quiz-Platform.git
   cd SQL-Quiz-Platform
   ```

2. Create a virtual environment and install dependencies:

   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. Set up the Supabase PostgreSQL database. Use the restaurant dataset in `init.sql`, create the `quiz_answers` table with a unique constraint on `(user_id, question_number)`, and configure a read-only `quiz_reader` role for student queries. Configure Supabase Auth for email/password sign-in.

4. Create a local **`.env`** file (do not commit it) with the following variable names and your own Supabase credentials:

   ```dotenv
   SUPABASE_URL=your_supabase_project_url
   SUPABASE_KEY=your_supabase_public_anon_key

   DB_HOST=your_supabase_session_pooler_host
   DB_PORT=5432
   POSTGRES_DB=postgres

   POSTGRES_USER=your_privileged_pooler_username
   POSTGRES_PASSWORD=your_privileged_database_password

   QUIZ_DB_USER=your_read_only_pooler_username
   QUIZ_DB_PASSWORD=your_read_only_database_password
   ```

   Use the **Supabase Session pooler** connection details rather than the Direct connection. The database connections in the application use `sslmode=require`. Copy the exact host, port, and usernames shown by your Supabase project; the values above are placeholders.

5. Start the application:

   ```bash
   streamlit run app.py
   ```

   Open the local URL shown by Streamlit (typically `http://localhost:8501`). For local email confirmation links, configure the corresponding allowed redirect URL in Supabase Auth settings.

## GitHub Actions and Secrets

The workflow in `.github/workflows/test.yml` runs on pushes to the repository and can also be started manually. It checks out the repository, sets up Python 3.12, installs `requirements.txt`, and executes a query against the hosted PostgreSQL `restaurants` table. The test asserts that the top-rated-restaurants query returns three rows.

The workflow receives these values from **GitHub repository secrets**, not hard-coded passwords:

- `POSTGRES_DB`
- `DB_HOST`
- `DB_PORT`
- `QUIZ_DB_USER`
- `QUIZ_DB_PASSWORD`

The CI test uses the restricted reader account. **`.env` is excluded by `.gitignore`** and must never be pushed to GitHub. A successful workflow run is visible in the repository's **Actions** tab.

## Deployment

The app is deployed on **Streamlit Community Cloud** from the GitHub repository. Runtime credentials are configured as private deployment secrets/environment variables, rather than stored in the source code. Supabase Auth is configured to allow the deployed website URL for authentication redirects.

**Deployed app:** https://ids706-restaurant-sql-quiz.streamlit.app/

## Security and Limitations

- Signed-out users cannot access the quiz's query and save actions.
- Student SQL uses a dedicated, read-only database role, separate from the server-side connection used for answer persistence.
- Database connections require SSL; user-answer database operations use parameterized SQL values.
- Secrets belong in local `.env`, GitHub Secrets, or private deployment configuration—not in committed code.
- Automatic grading compares query result sets against reference results; it is intended as practice feedback, not as a general-purpose SQL equivalence checker. The current quiz expects ordered outputs.
- Grading results are not permanently stored; saved SQL answers are.

## Assignment

Created for **IDS 706 — Data Engineering**, Duke University. The project demonstrates a hosted PostgreSQL database, authenticated query/save access, a GitHub Actions workflow using secrets, and a live 20-point SQL quiz.


## Week 8 Optional Extension: RAG-Powered Text-to-SQL

The existing SQL Quiz has an **AI SQL Generator (RAG)** section for signed-in users.

**Live application:** https://ids706-restaurant-sql-quiz.streamlit.app/

### Architecture

1. A signed-in user chooses a quiz question and enters a natural-language request.
2. `rag.py` embeds the request using a deterministic 512-dimensional hashing vectorizer and performs **real ChromaDB vector similarity retrieval** against database schema, business rules, and five SQL examples. The Chroma collection is initialized in memory from those documents; it does not require a separate hosted service or model download.
3. The retrieved documents are included in the prompt sent to **Google Gemini** using the `google-genai` API (`gemini-2.5-flash` by default, configurable through `GEMINI_MODEL`).
4. The app displays generated SQL and the retrieved knowledge documents/distances.
5. For extra credit, the app automatically executes generated SQL through the restricted PostgreSQL `quiz_reader` account, displays the result table, and compares results against the selected quiz question's expected SQL output.

**Pipeline:** Natural-language question → ChromaDB vector retrieval → Gemini API → SQL → read-only PostgreSQL execution → result validation.

### Run locally

Use the same Supabase database, Supabase Auth, and `.env` configuration from Week 7. Add the following to your local `.env` (never commit this file):

```dotenv
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
```

From the project folder, with your virtual environment activated:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Sign in, scroll to **AI SQL Generator (RAG)**, select a quiz question, and click **Generate SQL with Gemini + Run + Validate**. Expand **Retrieved context from ChromaDB** to inspect retrieved documents and distances.

### Streamlit Cloud deployment

In the existing app's **Settings → Secrets**, retain all Week 7 secrets and add:

```toml
GEMINI_API_KEY = "your_gemini_api_key"
GEMINI_MODEL = "gemini-2.5-flash"
```

Push the updated code to GitHub and allow Streamlit Cloud to rebuild. API credentials must remain only in `.env` / Streamlit Secrets, not in committed files. The Chroma collection is rebuilt automatically when the deployed app starts; no separate Chroma server is needed.

### Required screenshots (add after deployment)

- **Basic:** A natural-language question and its AI-generated SQL. Save as `screenshots/rag_generated_sql.png`.
- **Extra credit:** Generated SQL, executed result table, and Correct/Incorrect validation. Save as `screenshots/rag_execution_validation.png`.

After taking the screenshots, commit them to the repository and replace this paragraph with embedded Markdown image references. Screenshots cannot be captured as evidence until the deployed API integration has actually been tested.

### Security notes

Only single-statement `SELECT` SQL is passed to the existing `run_quiz_query` function. It uses a PostgreSQL read-only account, read-only transactions, a 5-second statement timeout, and a 100-row display limit. Generated SQL is never executed with the privileged account used for saving answers. This is a classroom demo, not a production-grade SQL sandbox.
