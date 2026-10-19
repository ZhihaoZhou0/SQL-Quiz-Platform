import os
from decimal import Decimal

import pandas as pd
import psycopg2
import streamlit as st

from dotenv import load_dotenv
from supabase import create_client
from quiz_db import run_quiz_query


# ============================================================
# 1. Configuration
# ============================================================

load_dotenv()

st.set_page_config(
    page_title="SQL Quiz Platform",
    page_icon="📝",
    layout="wide",
)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error(
        "Missing SUPABASE_URL or SUPABASE_KEY. "
        "Please check your environment variables."
    )
    st.stop()


# ============================================================
# 2. Supabase Authentication
# ============================================================

def get_supabase_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


supabase = get_supabase_client()

if "user" not in st.session_state:
    st.session_state.user = None

if "access_token" not in st.session_state:
    st.session_state.access_token = None

if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = None


def save_login_session(response):
    """Store the authenticated user and tokens."""
    if response.session and response.user:
        st.session_state.user = response.user
        st.session_state.access_token = (
            response.session.access_token
        )
        st.session_state.refresh_token = (
            response.session.refresh_token
        )


def sign_out():
    """Clear authentication and quiz session state."""

    # Clear authentication information
    st.session_state.user = None
    st.session_state.access_token = None
    st.session_state.refresh_token = None

    # Clear cached quiz answers and text area values
    for key in list(st.session_state.keys()):
        if key.startswith(("loaded_answers_", "answer_", "grading_results_")):
            del st.session_state[key]


def verify_current_user():
    """
    Validate the stored access token with Supabase Auth.
    Refresh an expired token when possible.
    """
    token = st.session_state.access_token

    if not token:
        st.session_state.user = None
        return False

    try:
        response = supabase.auth.get_user(token)
        if response.user:
            st.session_state.user = response.user
            return True
    except Exception:
        pass

    refresh_token = st.session_state.refresh_token

    if refresh_token:
        try:
            response = supabase.auth.refresh_session(
                refresh_token
            )
            save_login_session(response)
            return st.session_state.user is not None
        except Exception:
            pass

    sign_out()
    return False


# ============================================================
# 3. Database Functions
# ============================================================

def get_database_connection():
    """
    Privileged connection used only by the Streamlit server
    to save and load quiz answers.

    Student SQL is executed separately by quiz_db.py
    using the restricted quiz_reader account.
    """
    return psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        sslmode="require",
        connect_timeout=10,
    )


def save_answer(user_id, question_number, answer_sql):
    """Save or update one answer in PostgreSQL."""
    conn = get_database_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO quiz_answers
                        (user_id, question_number, answer_sql)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id, question_number)
                    DO UPDATE SET
                        answer_sql = EXCLUDED.answer_sql,
                        updated_at = NOW();
                    """,
                    (
                        str(user_id),
                        question_number,
                        answer_sql,
                    ),
                )
    finally:
        conn.close()


def load_answers(user_id):
    """Load saved answers belonging to one user."""
    conn = get_database_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT question_number, answer_sql
                    FROM quiz_answers
                    WHERE user_id = %s;
                    """,
                    (str(user_id),),
                )

                return {
                    question_number: answer_sql
                    for question_number, answer_sql
                    in cur.fetchall()
                }
    finally:
        conn.close()


# ============================================================
# 4. Quiz Questions
# ============================================================

QUESTIONS = [
    {
        "id": 1,
        "title": "Nearby Restaurants",
        "points": 4,
        "description": (
            "Find the names and distances of restaurants "
            "within 2.0 miles. Order the results by distance "
            "from nearest to farthest."
        ),
        "hint_sql": """
SELECT name, distance_miles
FROM restaurants
WHERE distance_miles <= 2.0
ORDER BY distance_miles ASC;
""",
    },
    {
        "id": 2,
        "title": "Top Rated Restaurants",
        "points": 4,
        "description": (
            "Find the names and ratings of the top 3 "
            "highest-rated restaurants."
        ),
        "hint_sql": """
SELECT name, rating
FROM restaurants
ORDER BY rating DESC
LIMIT 3;
""",
    },
    {
        "id": 3,
        "title": "Restaurant Prices with Tax",
        "points": 4,
        "description": (
            "Show each restaurant's name, average cost, "
            "and cost after adding 7.5% tax. "
            "Name the calculated column cost_with_tax, "
            "round it to 2 decimal places, "
            "and order the results by restaurant name."
        ),
        "hint_sql": """
SELECT
    name,
    avg_cost,
    ROUND(avg_cost * 1.075, 2) AS cost_with_tax
FROM restaurants
ORDER BY name;
""",
    },
    {
        "id": 4,
        "title": "Restaurants by Cuisine",
        "points": 4,
        "description": (
            "Count the number of restaurants in each cuisine. "
            "Show cuisine and restaurant_count. "
            "Order by restaurant count descending, "
            "then cuisine ascending."
        ),
        "hint_sql": """
SELECT
    cuisine,
    COUNT(*) AS restaurant_count
FROM restaurants
GROUP BY cuisine
ORDER BY restaurant_count DESC, cuisine ASC;
""",
    },
    {
        "id": 5,
        "title": "Highly Rated Restaurants",
        "points": 4,
        "description": (
            "Find the names and ratings of restaurants "
            "with a rating of at least 4.5. "
            "Order by rating from highest to lowest."
        ),
        "hint_sql": """
SELECT name, rating
FROM restaurants
WHERE rating >= 4.5
ORDER BY rating DESC;
""",
    },
]


# ============================================================
# 4b. Automatic Grading
# ============================================================

def normalize_cell(value):
    """Normalize numeric values returned by psycopg2 for fair comparison."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value)).normalize()
    return value


def grade_sql_answer(user_columns, user_rows, expected_columns, expected_rows):
    """Compare result sets, not SQL text. Ordering matters for these questions."""
    if list(user_columns) != list(expected_columns):
        return False
    if len(user_rows) != len(expected_rows):
        return False
    for user_row, expected_row in zip(user_rows, expected_rows):
        if tuple(map(normalize_cell, user_row)) != tuple(map(normalize_cell, expected_row)):
            return False
    return True


# ============================================================
# 5. Page Header
# ============================================================

st.title("SQL Quiz Platform")
st.subheader("IDS 706 — Restaurant SQL Quiz")

st.write(
    "Practice SQL using a live PostgreSQL database "
    "hosted on Supabase."
)


# ============================================================
# 6. Login / Sign Up
# ============================================================

authenticated = verify_current_user()

if not authenticated:

    st.info(
        "Please sign in to take the 20-point SQL quiz. "
        "You must be signed in to run SQL or save answers."
    )

    login_tab, signup_tab = st.tabs(
        ["Sign In", "Sign Up"]
    )

    with login_tab:

        st.markdown("### Sign In")

        with st.form("login_form"):

            login_email = st.text_input(
                "Email",
                key="login_email",
            )

            login_password = st.text_input(
                "Password",
                type="password",
                key="login_password",
            )

            login_button = st.form_submit_button(
                "Sign In"
            )

        if login_button:

            if not login_email or not login_password:
                st.warning(
                    "Please enter your email and password."
                )
            else:
                try:
                    response = (
                        supabase.auth.sign_in_with_password(
                            {
                                "email": login_email,
                                "password": login_password,
                            }
                        )
                    )

                    save_login_session(response)

                    if st.session_state.user:
                        st.rerun()
                    else:
                        st.error("Sign in failed.")

                except Exception as e:
                    st.error(f"Sign in failed: {e}")

    with signup_tab:

        st.markdown("### Create an Account")

        with st.form("signup_form"):

            signup_email = st.text_input(
                "Email",
                key="signup_email",
            )

            signup_password = st.text_input(
                "Password",
                type="password",
                key="signup_password",
            )

            signup_button = st.form_submit_button(
                "Sign Up"
            )

        if signup_button:

            if not signup_email or not signup_password:
                st.warning(
                    "Please enter your email and password."
                )

            elif len(signup_password) < 6:
                st.warning(
                    "Password must contain at least "
                    "6 characters."
                )

            else:
                try:
                    response = supabase.auth.sign_up(
                        {
                            "email": signup_email,
                            "password": signup_password,
                        }
                    )

                    if response.session:
                        save_login_session(response)
                        st.rerun()
                    else:
                        st.success(
                            "Account created. "
                            "Please check your email "
                            "for the confirmation link, "
                            "then return here to sign in."
                        )

                except Exception as e:
                    st.error(f"Sign up failed: {e}")

    # Critical: signed-out users cannot access quiz actions.
    st.stop()


# ============================================================
# 7. Signed-In User
# ============================================================

user = st.session_state.user
user_id = str(user.id)

st.success(f"Signed in as: {user.email}")

if st.button("Sign Out"):
    sign_out()
    st.rerun()

st.divider()


# ============================================================
# 8. Quiz Interface
# ============================================================

st.header("Restaurant SQL Quiz")

total_points = sum(q["points"] for q in QUESTIONS)

st.write(f"**Total: {total_points} points**")
st.write(f"**Number of questions: {len(QUESTIONS)}**")

st.info(
    "Write a SELECT query for each question. "
    "Click Run SQL to execute your query against "
    "the live restaurant database. "
    "Click Save Answer to store your SQL."
)

# Load saved answers when the authenticated user changes
# or starts a new quiz session.
answers_state_key = f"loaded_answers_{user_id}"

if answers_state_key not in st.session_state:
    try:
        saved_answers = load_answers(user_id)

        st.session_state[answers_state_key] = saved_answers

        # Restore saved SQL into each question's text area.
        for qid, answer_sql in saved_answers.items():
            answer_key = f"answer_{user_id}_{qid}"
            st.session_state[answer_key] = answer_sql

    except Exception as e:
        st.error(f"Unable to load saved answers: {e}")
        st.stop()

saved_answers = st.session_state[answers_state_key]

# Grades are temporary and tied to the exact SQL that was last executed.
grading_state_key = f"grading_results_{user_id}"
if grading_state_key not in st.session_state:
    st.session_state[grading_state_key] = {}
grading_results = st.session_state[grading_state_key]


# ============================================================
# 9. Display Questions
# ============================================================

for question in QUESTIONS:

    qid = question["id"]
    title = question["title"]
    points = question["points"]

    with st.expander(
        f"Question {qid}: {title} ({points} points)",
        expanded=(qid == 1),
    ):

        st.markdown(
            f"**Question {qid} — {points} points**"
        )

        st.write(question["description"])

        st.markdown("#### Your SQL Answer")

        answer_key = f"answer_{user_id}_{qid}"

        if answer_key not in st.session_state:
            st.session_state[answer_key] = (
                saved_answers.get(qid, "")
            )

        sql_answer = st.text_area(
            "Enter your SQL query:",
            key=answer_key,
            height=140,
        )

        run_col, save_col = st.columns(2)

        # ----------------------------------------------------
        # Run SQL
        # ----------------------------------------------------

        with run_col:

            if st.button(
                "▶ Run SQL",
                key=f"run_{qid}",
                use_container_width=True,
            ):

                if not verify_current_user():
                    st.error(
                        "Your session has expired. "
                        "Please sign in again."
                    )
                    st.stop()

                if not sql_answer.strip():
                    st.warning(
                        "Please enter a SQL query first."
                    )

                else:
                    try:
                        columns, rows = run_quiz_query(
                            sql_answer
                        )

                        result_df = pd.DataFrame(
                            rows,
                            columns=columns,
                        )

                        # Execute the reference query and compare actual result sets.
                        expected_columns, expected_rows = run_quiz_query(
                            question["hint_sql"]
                        )
                        is_correct = grade_sql_answer(
                            columns, rows, expected_columns, expected_rows
                        )
                        grading_results[qid] = {
                            "sql": sql_answer,
                            "correct": is_correct,
                        }

                        st.success("Query executed successfully!")
                        st.dataframe(result_df, use_container_width=True)
                        st.caption(
                            f"Returned {len(rows)} rows "
                            "(maximum 100 displayed)."
                        )

                    except Exception as e:
                        # An invalid query cannot retain an earlier score.
                        grading_results.pop(qid, None)
                        st.error(f"SQL execution error: {e}")

        # Show the grade for the currently displayed SQL only.
        # Editing an answer invalidates its previous grade until Run SQL is clicked.
        current_grade = grading_results.get(qid)
        if current_grade and current_grade["sql"] == sql_answer:
            if current_grade["correct"]:
                st.success(f"Correct! {points} / {points} points")
            else:
                st.warning(f"Incorrect result. 0 / {points} points")
        elif current_grade:
            st.info("Answer changed. Click Run SQL to check your new answer.")

        # ----------------------------------------------------
        # Save Answer
        # ----------------------------------------------------

        with save_col:

            if st.button(
                "💾 Save Answer",
                key=f"save_{qid}",
                use_container_width=True,
            ):

                if not verify_current_user():
                    st.error(
                        "Your session has expired. "
                        "Please sign in again."
                    )
                    st.stop()

                if not sql_answer.strip():
                    st.warning(
                        "Please enter an answer first."
                    )

                else:
                    try:
                        save_answer(
                            user_id,
                            qid,
                            sql_answer,
                        )

                        saved_answers[qid] = sql_answer

                        st.success(
                            "Answer saved to Supabase!"
                        )

                    except Exception as e:
                        st.error(
                            f"Failed to save answer: {e}"
                        )

        # ----------------------------------------------------
        # Hint / Expected SQL / Expected Result
        # ----------------------------------------------------

        with st.expander(
            "💡 Hint: Expected SQL and Result"
        ):

            st.markdown("**Expected SQL:**")

            st.code(
                question["hint_sql"].strip(),
                language="sql",
            )

            st.markdown("**Expected Result:**")

            try:
                expected_columns, expected_rows = (
                    run_quiz_query(
                        question["hint_sql"]
                    )
                )

                expected_df = pd.DataFrame(
                    expected_rows,
                    columns=expected_columns,
                )

                st.dataframe(
                    expected_df,
                    use_container_width=True,
                )

            except Exception as e:
                st.warning(
                    f"Expected result unavailable: {e}"
                )

    st.write("")


# ============================================================
# 10. Quiz Summary
# ============================================================

st.divider()

st.subheader("Quiz Summary")

saved_count = sum(
    1
    for question in QUESTIONS
    if saved_answers.get(question["id"], "").strip()
)

st.write(
    f"**Saved answers:** {saved_count} / {len(QUESTIONS)}"
)

st.write(
    f"**Total possible points:** {total_points}"
)

earned_points = 0
correct_count = 0
checked_count = 0
for question in QUESTIONS:
    qid = question["id"]
    grade = grading_results.get(qid)
    current_sql = st.session_state.get(f"answer_{user_id}_{qid}", "")
    if grade and grade["sql"] == current_sql:
        checked_count += 1
        if grade["correct"]:
            earned_points += question["points"]
            correct_count += 1

st.metric("Your Score", f"{earned_points} / {total_points}")
st.progress(earned_points / total_points if total_points else 0)
st.write(f"**Correct answers:** {correct_count} / {len(QUESTIONS)}")
st.caption(
    f"Checked answers: {checked_count} / {len(QUESTIONS)}. "
    "Scores reflect only answers checked with Run SQL in this session. "
    "Editing SQL invalidates its previous grade; click Run SQL again. "
    "Saved SQL answers persist in Supabase, but scores are not saved."
)
