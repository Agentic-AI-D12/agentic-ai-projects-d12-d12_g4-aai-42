import html
import re
import time
from main import run_system
import streamlit as st

from auth import login, signup
from main import run_system


st.set_page_config(page_title="Healthcare AI Assistant", layout="wide")


if "page" not in st.session_state:
    st.session_state.page = "login"

if "user" not in st.session_state:
    st.session_state.user = None

if "result" not in st.session_state:
    st.session_state.result = None

if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "login"

if "sidebar_topic" not in st.session_state:
    st.session_state.sidebar_topic = "treatment"


import os
css_path = os.path.join(os.path.dirname(__file__), "style.css")
with open(css_path, "r") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def render_hero(title: str, subtitle: str, badge: str) -> None:
    st.markdown(
        f"""
        <div class="hero-panel">
            <div class="badge">{badge}</div>
            <h1 class="page-title">{title}</h1>
            <p class="subtitle">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def set_sidebar_visibility(show: bool) -> None:
    display = "block" if show else "none"
    st.markdown(
        f"""
        <style>
        section[data-testid="stSidebar"] {{
            display: {display};
        }}
        div[data-testid="collapsedControl"] {{
            display: {display};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-shell">
                <div class="sidebar-title">Healthcare AI</div>
                <div class="sidebar-copy">
                    Faster treatment summaries, local hospital guidance, and estimated cost ranges.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.session_state.user:
            st.markdown(
                f"""
                <div class="sidebar-chip">Signed in as {html.escape(st.session_state.user)}</div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("<div class='sidebar-menu-label'>Results</div>", unsafe_allow_html=True)

            has_result = bool(st.session_state.get("result"))

            if st.button("📋 Treatment Summary", key="sidebar_topic_treatment", use_container_width=True):
                st.session_state.sidebar_topic = "treatment"
                if has_result:
                    st.session_state.page = "result"
                    st.session_state.show_cost = False
                    st.session_state.show_hospitals = False
                    st.session_state.show_schedule = False
                else:
                    st.session_state.page = "form"
                st.rerun()

            if st.button("🏥 Hospital Suggestions", key="sidebar_topic_hospital", use_container_width=True):
                st.session_state.sidebar_topic = "hospital"
                if has_result:
                    st.session_state.page = "result"
                    st.session_state.show_hospitals = True
                    st.session_state.show_cost = False
                    st.session_state.show_schedule = False
                else:
                    st.session_state.page = "form"
                st.rerun()

            if st.button("💰 Cost Plan", key="sidebar_topic_cost", use_container_width=True):
                st.session_state.sidebar_topic = "cost"
                if has_result:
                    st.session_state.page = "result"
                    st.session_state.show_cost = True
                    st.session_state.show_hospitals = False
                    st.session_state.show_schedule = False
                else:
                    st.session_state.page = "form"
                st.rerun()

            if st.button("🗓️ Execution Schedule", key="sidebar_topic_schedule", use_container_width=True):
                st.session_state.sidebar_topic = "schedule"
                if has_result:
                    st.session_state.page = "result"
                    st.session_state.show_schedule = True
                    st.session_state.show_cost = False
                    st.session_state.show_hospitals = False
                else:
                    st.session_state.page = "form"
                st.rerun()

            st.markdown("<div class='sidebar-menu-label'>Navigate</div>", unsafe_allow_html=True)
            if st.button("Patient Form", key="sidebar_form_btn", use_container_width=True):
                st.session_state.page = "form"
                st.rerun()

            if has_result and st.button("View Generated Result", key="sidebar_results_btn", use_container_width=True):
                st.session_state.page = "result"
                st.rerun()

            if st.button("Logout", key="sidebar_logout_btn", use_container_width=True):
                st.session_state.page = "login"
                st.session_state.user = None
                st.session_state.auth_mode = "login"
                st.rerun()


def format_block(text: str) -> str:
    if not text:
        return ""
    # Convert bold markers to HTML
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    
    # Simple list parsing
    lines = text.split("\n")
    html_lines = []
    in_list = False
    
    for line in lines:
        line = line.strip()
        if not line:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append("<br>")
            continue
            
        if line.startswith("- ") or line.startswith("* ") or (len(line) > 2 and line[0].isdigit() and line[1] == "."):
            if not in_list:
                html_lines.append("<ul style='margin-left: 20px; margin-top: 10px; margin-bottom: 10px;'>")
                in_list = True
            # Remove bullet marker
            content = line[2:].strip() if not line[0].isdigit() else line[line.find(".")+1:].strip()
            html_lines.append(f"<li style='margin-bottom: 6px;'>{content}</li>")
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<div style='margin-bottom: 8px;'>{line}</div>")
            
    if in_list:
        html_lines.append("</ul>")
        
    return "".join(html_lines)


def render_result_block(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="result-card">
            <div class="result-label">{html.escape(title)}</div>
            <div class="result-body">{format_block(body)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_topic_content() -> tuple[str, str]:
    topic = st.session_state.sidebar_topic
    topics = {
        "treatment": (
            "Treatment Summary",
            "This section explains the condition in simple words and gives a short treatment direction so the user can understand the next care steps quickly.",
        ),
        "hospital": (
            "Hospital Suggestions",
            "This section focuses on nearby hospital options based on the location you enter, so the user can quickly shortlist where to go for consultation or treatment.",
        ),
        "cost": (
            "Cost Plan",
            "This section gives an estimated low, medium, and high treatment range in INR to help the user understand expected budget planning before visiting a hospital.",
        ),
        "schedule": (
            "Execution Schedule",
            "This section provides a detailed treatment timeline and validates hospital resources like bed and doctor availability.",
        ),
    }
    return topics.get(topic, topics["treatment"])


def render_topic_panel() -> None:
    title, copy = get_topic_content()
    st.markdown(
        f"""
        <div class="topic-panel">
            <div class="result-label">Interactive Guide</div>
            <div class="topic-title">{html.escape(title)}</div>
            <div class="topic-copy">{html.escape(copy)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def parse_cost_cards(cost_text: str) -> list[tuple[str, str]]:
    cards = []
    for line in (cost_text or "").splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue

        if ":" in cleaned:
            label, value = cleaned.split(":", 1)
        else:
            parts = re.split(r"\s{2,}", cleaned, maxsplit=1)
            if len(parts) == 2:
                label, value = parts
            else:
                label, value = "Estimate", cleaned

        cards.append((label.strip(), value.strip()))

    return cards[:3]


def render_cost_cards(cost_text: str) -> None:
    cards = parse_cost_cards(cost_text)

    if not cards:
        render_result_block("Estimated Cost", cost_text)
        return

    columns = st.columns(len(cards))
    for column, (label, value) in zip(columns, cards):
        with column:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">{html.escape(label)}</div>
                    <div class="metric-value">{html.escape(value)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

# ---------- LOGIN PAGE ----------
def _deprecated_login_page():
    st.markdown("<h1 class='center'>🔐 Healthcare AI</h1>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])

    with col2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)

        choice = st.radio("Select", ["Login", "Signup"], horizontal=True)

        if choice == "Login":
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")

            if st.button("Login"):
                if login(username, password):
                    st.success("Login successful 🎉")
                    st.session_state.user = username
                    st.session_state.page = "form"
                    st.rerun()
                else:
                    st.error("Invalid credentials")

        else:
            username = st.text_input("Username", key="signup_username")
            password = st.text_input("Password", type="password", key="signup_password")

            if st.button("Create Account"):
                if signup(username, password):
                    st.success("Account created! Please login.")
                else:
                    st.error("User already exists")

        st.markdown("</div>", unsafe_allow_html=True)


# ---------- FORM PAGE ----------
def _deprecated_form_page():
    st.markdown(f"<h2>👋 Welcome, {st.session_state.user}</h2>", unsafe_allow_html=True)

    if st.button("Logout"):
        st.session_state.page = "login"
        st.session_state.user = None
        st.rerun()

    col1, col2, col3 = st.columns([1,2,1])

    with col2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)

        st.subheader("Enter Details")
        disease = st.text_input("Disease", key="disease_input")
        location = st.text_input("Location", key="location_input")

        if st.button("Get Treatment Plan"):
            if not disease.strip() or not location.strip():
                st.error("Please fill all fields")
                return

            with st.spinner("Analyzing..."):
                time.sleep(2)
                result = run_system({
                    "disease": disease,
                    "location": location
                })

            st.session_state.result = result
            st.session_state.page = "result"
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


# ---------- RESULT PAGE ----------
def _deprecated_result_page():
    st.markdown("<h2>📊 Results</h2>", unsafe_allow_html=True)

    if st.button("🔙 Back"):
        st.session_state.page = "form"
        st.rerun()

    result = st.session_state.result

    col1, col2, col3 = st.columns([1,2,1])

    with col2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)

        st.markdown("### 🩺 Treatment Plan")
        st.write(result["treatment"])

        st.markdown("### 🏥 Hospitals")
        st.write(result["hospitals"])

        st.markdown("### 💰 Cost")
        st.code(result["cost"])

        st.markdown("</div>", unsafe_allow_html=True)

# ---------- POLISHED UI ----------
def login_page():
    set_sidebar_visibility(False)

    left_col, right_col = st.columns([1.2, 0.9], gap="large")

    with left_col:
        st.markdown(
            """
            <div class="feature-panel">
                <div class="badge">Smart care planning</div>
                <div class="feature-title">Healthcare AI Assistant</div>
                <div class="feature-copy">
                    Professional healthcare guidance with treatment direction, hospital suggestions, and budget estimates in one smooth workflow.
                </div>
                <div class="mini-stat">Fast login, cleaner dashboard, and simpler treatment planning experience.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right_col:
        st.markdown(
            f"""
            <div class="auth-panel">
                <div class="badge">{'Welcome back' if st.session_state.auth_mode == 'login' else 'Create your account'}</div>
                <h2 class="card-title">{'Login to continue' if st.session_state.auth_mode == 'login' else 'Sign up to get started'}</h2>
                <p class="muted-text">{'Access your healthcare dashboard and continue planning treatment.' if st.session_state.auth_mode == 'login' else 'Create a secure account to use the assistant dashboard.'}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.session_state.auth_mode == "login":
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")

            if st.button("Login", key="login_btn", use_container_width=True):
                if login(username, password):
                    st.session_state.user = username
                    st.session_state.page = "form"
                    st.success("Login successful.")
                    st.rerun()
                else:
                    st.error("Invalid credentials.")

            st.caption("New here?")
            if st.button("Create an account", key="show_signup_btn", use_container_width=True):
                st.session_state.auth_mode = "signup"
                st.rerun()
        else:
            username = st.text_input("Username", key="signup_username")
            password = st.text_input("Password", type="password", key="signup_password")

            if st.button("Create Account", key="create_account_btn", use_container_width=True):
                if signup(username, password):
                    st.session_state.auth_mode = "login"
                    st.success("Account created. Please login.")
                    st.rerun()
                else:
                    st.error("User already exists.")

            st.caption("Already have an account?")
            if st.button("Back to login", key="show_login_btn", use_container_width=True):
                st.session_state.auth_mode = "login"
                st.rerun()


def form_page():
    set_sidebar_visibility(True)
    render_sidebar()

    st.markdown(
        f"""
        <div class="assistant-panel">
            <div class="assistant-row">
                <div class="assistant-identity">
                    <div class="assistant-icon">🏥</div>
                    <div>
                        <div class="assistant-label">Assistant agent</div>
                        <div class="assistant-name">Healthcare Assistant Agent</div>
                        <div class="assistant-copy">Welcome, {html.escape(st.session_state.user or 'User')}. Add disease and location details to generate your treatment summary.</div>
                    </div>
                </div>
                <div class="badge">Dashboard</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left_col, right_col = st.columns([1.15, 0.85], gap="large")

    with left_col:
        st.subheader("Patient Details")
        st.caption("Enter patient details, condition, and location to generate a personalized treatment summary.")

        patient_name = st.text_input("Patient Name", key="name_input", placeholder="e.g. John Doe")
        age_col, gender_col = st.columns(2)
        with age_col:
            age = st.text_input("Age", key="age_input", placeholder="e.g. 45")
        with gender_col:
            gender = st.selectbox("Gender", ["Male", "Female", "Other"], key="gender_input")
        disease = st.text_input("Disease", key="disease_input", placeholder="e.g. Kidney Stone")
        location = st.text_input("Location", key="location_input", placeholder="e.g. Delhi")

        st.markdown("<div style='margin-top: 6px;'></div>", unsafe_allow_html=True)
        willing_to_travel = st.radio(
            "Are you willing to travel to another city for treatment?",
            ["Yes", "No"],
            index=1,
            horizontal=True,
            key="travel_input"
        )
        if willing_to_travel == "Yes":
            st.info("✈️ We will find **India's top 3 hospitals** for your condition.", icon=None)
        else:
            st.info(f"📍 We will find the best hospitals in **{location or 'your city'}**.", icon=None)

        if st.button("Get Treatment Plan", key="treatment_btn", use_container_width=True):
            if not disease.strip() or not location.strip() or not patient_name.strip() or not age.strip():
                st.error("Please fill all fields.")
                return

            with st.spinner("Analyzing your request..."):
                result = run_system({
                    "patient_name": patient_name,
                    "age": age,
                    "gender": gender,
                    "disease": disease,
                    "location": location,
                    "willing_to_travel": willing_to_travel
                })

            st.session_state.result = result
            st.session_state.show_cost = False
            st.session_state.show_hospitals = False
            st.session_state.show_schedule = False
            st.session_state.page = "result"
            st.session_state.sidebar_topic = "treatment"
            st.rerun()

    with right_col:
        render_topic_panel()
        st.markdown(
            """
            <div class="result-card">
                <div class="result-label">Suggested Input Style</div>
                <div class="result-body">Name: John Doe<br>Age: 45<br>Disease: Kidney Stone<br>Location: Delhi</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def result_page():
    set_sidebar_visibility(True)
    render_sidebar()

    render_hero(
        "Your Care Results",
        "Review the generated treatment overview, hospital options, and estimated cost range.",
        "Analysis complete",
    )

    if st.button("Back to Form", key="back_btn"):
        st.session_state.page = "form"
        st.rerun()

    result = st.session_state.result
    
    left_col, right_col = st.columns([2.5, 1])
    
    with left_col:
        # Active Section Logic
        show_cost = st.session_state.get("show_cost", False)
        show_hospitals = st.session_state.get("show_hospitals", False)
        show_schedule = st.session_state.get("show_schedule", False)

        # 1. NAVIGATION BAR
        st.markdown("<div class='section-heading' style='margin-top: 0;'>Navigation</div>", unsafe_allow_html=True)
        nav_col1, nav_col2, nav_col3, nav_col4 = st.columns(4)
        
        with nav_col1:
            if st.button("📋 Summary", key="nav_treatment_btn", use_container_width=True):
                st.session_state.show_cost = False
                st.session_state.show_hospitals = False
                st.session_state.show_schedule = False
                st.session_state.sidebar_topic = "treatment"
                st.rerun()
        
        with nav_col2:
            if st.button("💰 Cost", key="nav_cost_btn", use_container_width=True):
                st.session_state.show_cost = True
                st.session_state.show_hospitals = False
                st.session_state.show_schedule = False
                st.session_state.sidebar_topic = "cost"
                st.rerun()
                
        with nav_col3:
            if st.button("🏥 Hospitals", key="nav_hospitals_btn", use_container_width=True):
                st.session_state.show_hospitals = True
                st.session_state.show_cost = False
                st.session_state.show_schedule = False
                st.session_state.sidebar_topic = "hospital"
                st.rerun()
                
        with nav_col4:
            if st.button("🗓️ Schedule", key="nav_schedule_btn", use_container_width=True):
                st.session_state.show_schedule = True
                st.session_state.show_cost = False
                st.session_state.show_hospitals = False
                st.session_state.sidebar_topic = "schedule"
                st.rerun()

        st.markdown("<hr style='margin: 20px 0; border: 0; border-top: 1px solid rgba(22,50,79,0.1);'>", unsafe_allow_html=True)

        # 2. DYNAMIC CONTENT AREA
        if show_cost:
            st.markdown("<div class='section-heading' style='font-size: 1.4rem;'>💰 Cost Plan</div>", unsafe_allow_html=True)
            cost_text = result.get("cost", "")
            cards_lines = []
            breakdown_lines = []
            for line in cost_text.splitlines():
                cleaned = line.strip()
                if not cleaned: continue
                
                if cleaned.lower().startswith("average") and ":" in cleaned:
                    cards_lines.append(cleaned)
                else:
                    breakdown_lines.append(line)
            
            if cards_lines:
                st.markdown("<div class='section-heading'>Market Average Estimates</div>", unsafe_allow_html=True)
                render_cost_cards("\n".join(cards_lines))
                st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)
            
            if breakdown_lines:
                st.markdown("<div class='section-heading'>🏥 Hospital Wise Cost Breakdown</div>", unsafe_allow_html=True)
                render_result_block("Individual Estimates", "\n".join(breakdown_lines).strip())

        elif show_hospitals:
            st.markdown("<div class='section-heading'>🏥 Hospital List</div>", unsafe_allow_html=True)
            render_result_block("Hospitals", result.get("hospitals", ""))

        elif show_schedule:
            st.markdown("<div class='section-heading'>🗓️ Execution Schedule</div>", unsafe_allow_html=True)
            schedule_text = result.get("schedule", "")
            schedule_text = re.sub(r"<[^>]+>", "", schedule_text).strip()

            resource_part = []
            schedule_part = []
            in_schedule = False
            for line in schedule_text.splitlines():
                if "execution schedule" in line.lower():
                    in_schedule = True
                if in_schedule:
                    schedule_part.append(line)
                else:
                    resource_part.append(line)

            resource_text = "\n".join(resource_part).strip()
            schedule_text_clean = "\n".join(schedule_part).strip()

            if resource_text:
                render_result_block("Resource Availability", resource_text)
                st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

            if schedule_text_clean:
                clean_schedule = schedule_text_clean
                for p in ["Phase 1", "Phase 2", "Phase 3"]:
                    clean_schedule = clean_schedule.replace(p, f"**{p}**")
                render_result_block("Treatment Timeline", clean_schedule)
        
        else:
            # Default: Treatment Summary
            st.markdown("<div class='section-heading'>🩺 Treatment Plan</div>", unsafe_allow_html=True)
            render_result_block("Treatment Summary", result.get("treatment", ""))

    with right_col:
        render_topic_panel()
        st.markdown(
            """
            <div class="result-card">
                <div class="result-label">Navigation Tip</div>
                <div class="result-body">Use the buttons at the top to switch between sections of your medical plan instantly.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---------- ROUTING ----------
if st.session_state.page == "login":
    login_page()

elif st.session_state.page == "form":
    form_page()

elif st.session_state.page == "result":
    result_page()
