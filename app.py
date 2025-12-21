import streamlit as st
import time
from utils import (
    OpenRouterLLM,
    PromptTemplates,
    ChatHistoryManager,
    ResumeProcessor,
    parse_llm_response
)


st.set_page_config(
    page_title="AI Interview Platform",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Modern Color Palette - Teal/Emerald Theme */
    :root {
        --primary: #0d9488;
        --secondary: #14b8a6;
        --success: #10b981;
        --warning: #f59e0b;
        --danger: #ef4444;
        --dark: #0f172a;
        --light: #f1f5f9;
    }
    
    /* Main Container */
    .main {
        background: linear-gradient(135deg, #0d9488 0%, #14b8a6 100%);
        padding: 1.5rem;
    }
    
    /* Card Styles - Reduced margins */
    .card {
        background: white;
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        margin: 0.5rem 0;
        animation: slideUp 0.5s ease-out;
    }
    
    @keyframes slideUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* Question Card */
    .question-card {
        background: linear-gradient(135deg, #0d9488 0%, #14b8a6 100%);
        color: white;
        border-radius: 15px;
        padding: 2rem;
        margin: 1rem 0;
        box-shadow: 0 15px 40px rgba(13, 148, 136, 0.5);
    }
    
    /* Progress Bar */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #0d9488 0%, #14b8a6 100%);
    }
    
    /* Buttons - Darker teal for better visibility */
    .stButton>button {
        background: linear-gradient(135deg, #0f766e 0%, #0d9488 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.85rem 2.5rem !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 6px 20px rgba(15, 118, 110, 0.5) !important;
    }
    
    .stButton>button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 8px 25px rgba(15, 118, 110, 0.7) !important;
        background: linear-gradient(135deg, #134e4a 0%, #0f766e 100%) !important;
    }
    
    /* Sidebar - Dark theme */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #020617 100%);
    }
    
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] .stSelectSlider label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: white !important;
    }
    
    /* Headers - Very dark for visibility on white */
    h1 {
        color: #0f172a !important;
        font-weight: 800 !important;
        text-shadow: none;
    }
    
    h2, h3 {
        color: #1e293b !important;
        font-weight: 700 !important;
    }
    
    /* Header Title - Dark text */
    .header-title {
        font-size: 3.5rem !important;
        font-weight: 900 !important;
        color: #0f172a !important;
        margin-bottom: 0.5rem !important;
    }
    
    .header-subtitle {
        font-size: 1.3rem !important;
        color: #1e293b !important;
        font-weight: 600 !important;
    }
    
    /* Metrics */
    .metric-card {
        background: linear-gradient(135deg, #f0fdfa 0%, #ccfbf1 100%);
        border-radius: 15px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    /* Success/Warning/Error Boxes */
    .success-box {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 0.5rem 0;
        box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
    }
    
    .warning-box {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 0.5rem 0;
        box-shadow: 0 4px 15px rgba(245, 158, 11, 0.3);
    }
    
    .error-box {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 0.5rem 0;
        box-shadow: 0 4px 15px rgba(239, 68, 68, 0.3);
    }
    
    .info-box {
        background: linear-gradient(135deg, #0d9488 0%, #14b8a6 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 0.5rem 0;
        box-shadow: 0 4px 15px rgba(13, 148, 136, 0.3);
    }
    
    /* Text Area */
    .stTextArea textarea {
        border-radius: 12px;
        border: 2px solid #cbd5e1;
        padding: 1rem;
        font-size: 1.05rem;
    }
    
    .stTextArea textarea:focus {
        border-color: #0d9488;
        box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.1);
    }
    
    /* Text Input */
    .stTextInput input {
        border-radius: 10px;
        border: 2px solid #cbd5e1;
    }
    
    .stTextInput input:focus {
        border-color: #0d9488;
        box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.1);
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #f0fdfa;
        border-radius: 10px;
    }
    
    /* Remove extra padding */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize all session state variables"""
    if 'state' not in st.session_state:
        st.session_state.state = 0
    
    if 'candidate_context' not in st.session_state:
        st.session_state.candidate_context = {
            "name": "",
            "email": "",
            "phone": "",
            "location": "",
            "experience": "",
            "role": "",
            "tech_stack": "",
            "projects": [],
            "internships": [],
            "education": [],
            "certifications": [],
            "mode": "",
            "difficulty": ""
        }
    
    if 'resume_extracted' not in st.session_state:
        st.session_state.resume_extracted = False
    
    if 'chat_manager' not in st.session_state:
        st.session_state.chat_manager = ChatHistoryManager()
    
    if 'llm' not in st.session_state:
        try:
            st.session_state.llm = OpenRouterLLM()
        except ValueError as e:
            st.error(f"⚠️ {str(e)}")
            st.info("Please set your OPENROUTER_API_KEY in .env file")
            st.stop()
    
    if 'all_questions' not in st.session_state:
        st.session_state.all_questions = []
    
    if 'all_answers' not in st.session_state:
        st.session_state.all_answers = []
    
    if 'current_question_idx' not in st.session_state:
        st.session_state.current_question_idx = 0
    
    if 'final_report' not in st.session_state:
        st.session_state.final_report = None


def render_header():
    """Render beautiful application header"""
    st.markdown("""
    <div style='text-align: center; padding: 2rem 0;'>
        <h1 class='header-title'>
            🤖 AI Interview Platform
        </h1>
        <p class='header-subtitle'>
            Intelligent Assessment with Real-Time Adaptation
        </p>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar():
    """Render beautiful sidebar with mode and difficulty selection"""
    with st.sidebar:
        st.markdown("""
        <div style='text-align: center; padding: 1rem 0;'>
            <h2 style='color: white; margin-bottom: 0;'>⚙️ Interview Settings</h2>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Mode Selection
        st.markdown("<h3 style='color: white;'>📚 Interview Mode</h3>", unsafe_allow_html=True)
        mode = st.radio(
            "Select Mode",
            ["🎓 Learning Mode", "💼 Interview Mode"],
            key="mode_selector",
            label_visibility="collapsed"
        )
        st.session_state.candidate_context["mode"] = "Learning" if "Learning" in mode else "Interview"
        
        if "Learning" in mode:
            st.markdown("<p style='color: #10b981; font-size: 0.85rem;'>✓ Get hints & explanations<br/>✓ Simplified questions<br/>✓ Concept explanations</p>", unsafe_allow_html=True)
        else:
            st.markdown("<p style='color: #f59e0b; font-size: 0.85rem;'>✓ Professional evaluation<br/>✓ Strict assessment<br/>✓ Hire recommendation</p>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Difficulty Selection
        st.markdown("<h3 style='color: white;'>🎯 Difficulty Level</h3>", unsafe_allow_html=True)
        difficulty = st.select_slider(
            "Select Difficulty",
            options=["Basic", "Intermediate", "Advanced"],
            value="Intermediate",
            key="difficulty_selector",
            label_visibility="collapsed"
        )
        st.session_state.candidate_context["difficulty"] = difficulty
        
        if difficulty == "Basic":
            st.markdown("<p style='color: #9ca3af; font-size: 0.85rem;'>Fundamental concepts & simple questions</p>", unsafe_allow_html=True)
        elif difficulty == "Intermediate":
            st.markdown("<p style='color: #9ca3af; font-size: 0.85rem;'>Balanced theory & practical application</p>", unsafe_allow_html=True)
        else:
            st.markdown("<p style='color: #9ca3af; font-size: 0.85rem;'>Advanced concepts & complex scenarios</p>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Progress Display
        if st.session_state.state >= 3 and st.session_state.all_questions:
            st.markdown("<h3 style='color: white;'>📊 Interview Progress</h3>", unsafe_allow_html=True)
            progress = st.session_state.current_question_idx / len(st.session_state.all_questions)
            st.progress(progress)
            st.markdown(f"<p style='color: white; text-align: center; font-size: 1.1rem; font-weight: 600;'>{st.session_state.current_question_idx}/{len(st.session_state.all_questions)} Questions</p>", unsafe_allow_html=True)
            
            # Section indicator
            if st.session_state.current_question_idx < 6:
                st.markdown("""
                <div style='background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
                            padding: 0.75rem; border-radius: 10px; text-align: center; margin: 0.5rem 0;'>
                    <p style='color: white; margin: 0; font-weight: 600;'>📝 Initial Assessment</p>
                    <p style='color: white; margin: 0; font-size: 0.85rem;'>Evaluating baseline skills</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style='background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); 
                            padding: 0.75rem; border-radius: 10px; text-align: center; margin: 0.5rem 0;'>
                    <p style='color: white; margin: 0; font-weight: 600;'>🔍 Adaptive Deep Dive</p>
                    <p style='color: white; margin: 0; font-size: 0.85rem;'>Based on your answers</p>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
        
        # Candidate Info
        if st.session_state.state >= 2:
            st.markdown("<h3 style='color: white;'>👤 Candidate Profile</h3>", unsafe_allow_html=True)
            st.markdown(f"<p style='color: white; font-weight: 600; font-size: 1.05rem;'>{st.session_state.candidate_context.get('name', 'N/A')}</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='color: #94a3b8;'>🎯 {st.session_state.candidate_context.get('role', 'N/A')}</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='color: #94a3b8;'>⏱️ {st.session_state.candidate_context.get('experience', 'N/A')} years exp</p>", unsafe_allow_html=True)
            
            # Resume Stats
            if st.session_state.candidate_context.get('projects') or st.session_state.candidate_context.get('internships'):
                st.markdown("<p style='color: #10b981; font-weight: 600; margin-top: 0.5rem;'>📄 Resume Highlights:</p>", unsafe_allow_html=True)
                
                if st.session_state.candidate_context.get('projects'):
                    st.markdown(f"<p style='color: #94a3b8;'>📁 {len(st.session_state.candidate_context['projects'])} Projects</p>", unsafe_allow_html=True)
                
                if st.session_state.candidate_context.get('internships'):
                    st.markdown(f"<p style='color: #94a3b8;'>💼 {len(st.session_state.candidate_context['internships'])} Internships</p>", unsafe_allow_html=True)
                
                if st.session_state.candidate_context.get('certifications'):
                    st.markdown(f"<p style='color: #94a3b8;'>🏆 {len(st.session_state.candidate_context['certifications'])} Certifications</p>", unsafe_allow_html=True)
            
            st.markdown("---")
        
        # Interview Tips
        if st.session_state.state == 3:
            st.markdown("<h3 style='color: white;'>💡 Quick Tips</h3>", unsafe_allow_html=True)
            st.markdown("""
            <div style='background: rgba(59, 130, 246, 0.2); padding: 1rem; border-radius: 10px; border-left: 4px solid #3b82f6;'>
                <p style='color: #e0e7ff; font-size: 0.85rem; margin: 0;'>
                    ✓ Be specific with examples<br/>
                    ✓ Mention your projects<br/>
                    ✓ Ask to simplify if needed<br/>
                    ✓ "I don't know" is okay
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
        
        # Footer
        st.markdown("""
        <div style='text-align: center; padding: 1rem 0; margin-top: 2rem;'>
            <p style='color: #64748b; font-size: 0.8rem;'>
                Powered by AI<br/>
                100% Adaptive Assessment
            </p>
        </div>
        """, unsafe_allow_html=True)


def handle_llm_error(error_message: str):
    """Handle LLM errors gracefully"""
    st.markdown('<div class="error-box">', unsafe_allow_html=True)
    st.markdown("### ⚠️ AI Service Issue")
    st.markdown(f"**Error:** {error_message}")
    st.markdown("""
    **Solutions:**
    - Check internet connection
    - Verify API key
    - Try again in a moment
    """)
    st.markdown('</div>', unsafe_allow_html=True)
    
    if st.button("🔄 Retry"):
        st.rerun()


def state_0_greeting():
    """STATE 0: Welcome Screen"""
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("""
    ## Welcome to AI Interview Platform! 🚀
    
    ### What makes us different?
    
    **🎯 Smart Adaptation**
    - First 6 questions assess your baseline
    - Next 4 questions adapt to YOUR performance
    - Total: 10 carefully crafted questions
    
    **🔍 Comprehensive Analysis**
    - Tone & communication analysis
    - Plagiarism detection
    - Answer quality assessment
    - Expected vs actual answer comparison
    
    **💡 User-Friendly Features**
    - Ask to simplify questions
    - Say "I don't know" - we handle it
    - Get hints in Learning Mode
    - Beautiful, distraction-free UI
    
    ### Interview Sections:
    1. **Profile Setup** - Upload resume or fill manually
    2. **Initial Assessment** - 6 questions (adaptive difficulty)
    3. **Deep Dive** - 4 questions based on your answers
    4. **Final Report** - Comprehensive AI evaluation
    
    ---
    
    **👈 Configure your interview in the sidebar first!**
    
    Select your mode (Learning/Interview) and difficulty level, then click below to start.
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Start Interview", type="primary", use_container_width=True):
            st.session_state.state = 1
            st.rerun()


def state_1_profile_setup():
    """STATE 1: Profile Setup with Resume Upload"""
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("## 📋 Candidate Profile")
    
    st.markdown('<div class="info-box">', unsafe_allow_html=True)
    st.markdown("""
    **💡 Interview will be based on your resume!**
    
    Upload your resume to get questions about:
    - ✅ Your projects & technical decisions
    - ✅ Internships & work experience
    - ✅ Certifications & achievements
    - ✅ Skills & technologies you've used
    
    *No resume? No problem! Just fill in your skills, and we'll ask general questions.*
    """)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Resume Upload
    st.markdown("### 📄 Quick Fill with Resume (Optional)")
    uploaded_file = st.file_uploader(
        "Upload your resume (PDF/Image)",
        type=['pdf', 'png', 'jpg', 'jpeg'],
        help="AI will extract projects, internships, certifications, and skills automatically"
    )
    
    if uploaded_file and not st.session_state.resume_extracted:
        with st.spinner("🤖 AI is analyzing your resume..."):
            file_bytes = uploaded_file.read()
            extracted_info = None
            
            if uploaded_file.type == "application/pdf":
                st.info("📄 Processing PDF...")
                resume_text = ResumeProcessor.pdf_to_text(file_bytes)
                if resume_text:
                    extracted_info = st.session_state.llm.extract_resume_from_text(resume_text)
            else:
                image_base64 = ResumeProcessor.image_to_base64(file_bytes)
                if image_base64:
                    extracted_info = st.session_state.llm.extract_resume_info(image_base64)
            
            if extracted_info:
                st.session_state.candidate_context.update({
                    "name": extracted_info.get("name", ""),
                    "email": extracted_info.get("email", ""),
                    "phone": extracted_info.get("phone", ""),
                    "location": extracted_info.get("location", ""),
                    "experience": extracted_info.get("experience_years", ""),
                    "tech_stack": ", ".join(extracted_info.get("skills", [])),
                    "projects": extracted_info.get("projects", []),
                    "internships": extracted_info.get("internships", []),
                    "education": extracted_info.get("education", []),
                    "certifications": extracted_info.get("certifications", [])
                })
                st.session_state.resume_extracted = True
                st.success("✅ Resume processed successfully! Review and edit below.")
                time.sleep(1)
                st.rerun()
    
    st.markdown("---")
    st.markdown("### ✍️ Basic Information (Required)")
    
    context = st.session_state.candidate_context
    
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Full Name *", value=context["name"])
        email = st.text_input("Email *", value=context["email"])
        experience = st.text_input("Years of Experience *", value=context["experience"])
    
    with col2:
        role = st.text_input("Target Role *", value=context["role"], placeholder="e.g., Full Stack Developer")
        phone = st.text_input("Phone (Optional)", value=context.get("phone", ""))
        location = st.text_input("Location (Optional)", value=context.get("location", ""))
    
    tech_stack = st.text_area(
        "Tech Stack / Skills *",
        value=context["tech_stack"],
        placeholder="Python, React, Node.js, MongoDB, Docker, AWS...",
        height=100,
        help="List all your technical skills - questions will be based on these!"
    )
    
    st.markdown("---")
    st.markdown("### 📁 Projects & Experience (Optional but Recommended)")
    st.markdown("*Add these for more personalized, resume-based questions!*")
    
    # Projects
    with st.expander("➕ Add Projects", expanded=bool(context.get("projects"))):
        projects_text = st.text_area(
            "Projects (One per line)",
            value="\n".join([f"{p.get('name', '')}: {p.get('description', '')} ({', '.join(p.get('technologies', []))})" 
                           for p in context.get("projects", [])]) if context.get("projects") else "",
            placeholder="E-commerce Website: Built with React, Node.js, MongoDB (React, Node.js, MongoDB)\nMobile App: iOS app for task management (Swift, Firebase)",
            height=120,
            help="Format: Project Name: Description (Technologies)"
        )
    
    # Internships
    with st.expander("➕ Add Internships", expanded=bool(context.get("internships"))):
        internships_text = st.text_area(
            "Internships (One per line)",
            value="\n".join([f"{i.get('company', '')}: {i.get('role', '')} - {i.get('description', '')}" 
                           for i in context.get("internships", [])]) if context.get("internships") else "",
            placeholder="Google: Software Engineering Intern - Worked on backend APIs\nMicrosoft: Data Science Intern - Built ML models",
            height=100,
            help="Format: Company: Role - What you did"
        )
    
    # Certifications
    with st.expander("➕ Add Certifications", expanded=bool(context.get("certifications"))):
        certifications_text = st.text_area(
            "Certifications (One per line)",
            value="\n".join(context.get("certifications", [])) if context.get("certifications") else "",
            placeholder="AWS Certified Solutions Architect\nGoogle Cloud Professional\nMongoDB Certified Developer",
            height=80
        )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Start Interview →", type="primary", use_container_width=True):
            if all([name, email, experience, role, tech_stack]):
                # Parse projects
                projects = []
                if projects_text:
                    for line in projects_text.strip().split('\n'):
                        if ':' in line:
                            parts = line.split(':', 1)
                            name_part = parts[0].strip()
                            rest = parts[1].strip()
                            
                            # Extract technologies in parentheses
                            techs = []
                            desc = rest
                            if '(' in rest and ')' in rest:
                                desc = rest[:rest.rfind('(')].strip()
                                tech_str = rest[rest.rfind('(')+1:rest.rfind(')')].strip()
                                techs = [t.strip() for t in tech_str.split(',')]
                            
                            projects.append({
                                "name": name_part,
                                "description": desc,
                                "technologies": techs
                            })
                
                # Parse internships
                internships = []
                if internships_text:
                    for line in internships_text.strip().split('\n'):
                        if ':' in line:
                            parts = line.split(':', 1)
                            company = parts[0].strip()
                            rest = parts[1].strip()
                            
                            role = ""
                            desc = rest
                            if '-' in rest:
                                role_parts = rest.split('-', 1)
                                role = role_parts[0].strip()
                                desc = role_parts[1].strip() if len(role_parts) > 1 else ""
                            
                            internships.append({
                                "company": company,
                                "role": role,
                                "description": desc
                            })
                
                # Parse certifications
                certifications = []
                if certifications_text:
                    certifications = [c.strip() for c in certifications_text.strip().split('\n') if c.strip()]
                
                st.session_state.candidate_context.update({
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "location": location,
                    "experience": experience,
                    "role": role,
                    "tech_stack": tech_stack,
                    "projects": projects,
                    "internships": internships,
                    "certifications": certifications
                })
                st.session_state.state = 2
                st.rerun()
            else:
                st.error("⚠️ Please fill all required fields (*)")


def state_2_generate_questions():
    """STATE 2: Generate Initial 6 Questions"""
    if not st.session_state.all_questions:
        with st.spinner("🤖 AI is crafting personalized questions for you..."):
            prompt = PromptTemplates.get_initial_6_questions_prompt(st.session_state.candidate_context)
            messages = [{"role": "user", "content": prompt}]
            
            response = st.session_state.llm.generate(messages, temperature=0.7, max_tokens=2000)
            
            if response.startswith("LLM_"):
                handle_llm_error(response)
                return
            
            parsed = parse_llm_response(response)
            
            if parsed and 'questions' in parsed and len(parsed['questions']) >= 6:
                st.session_state.all_questions = parsed['questions'][:6]
                st.session_state.current_question_idx = 0
                st.success("✅ Questions ready!")
                time.sleep(1)
            else:
                st.error("⚠️ Error generating questions. Please try again.")
                if st.button("🔄 Retry"):
                    st.rerun()
                return
    
    st.session_state.state = 3
    st.rerun()


def state_3_interview():
    """STATE 3: Conduct Interview (10 questions total)"""
    
    # Check if we need to generate adaptive questions
    if st.session_state.current_question_idx == 6 and len(st.session_state.all_questions) == 6:
        with st.spinner("🤖 AI is analyzing your answers and generating adaptive questions..."):
            first_6_answers = st.session_state.all_answers[:6]
            
            prompt = PromptTemplates.get_adaptive_4_questions_prompt(
                st.session_state.candidate_context,
                st.session_state.all_questions[:6],
                first_6_answers
            )
            messages = [{"role": "user", "content": prompt}]
            response = st.session_state.llm.generate(messages, temperature=0.7, max_tokens=1500)
            
            if response.startswith("LLM_"):
                handle_llm_error(response)
                return
            
            parsed = parse_llm_response(response)
            
            if parsed and 'questions' in parsed:
                st.session_state.all_questions.extend(parsed['questions'][:4])
                st.success("✅ Adaptive questions generated based on your performance!")
                time.sleep(1)
            else:
                st.error("⚠️ Error generating adaptive questions.")
                return
    
    # Check if interview is complete
    if st.session_state.current_question_idx >= len(st.session_state.all_questions):
        st.session_state.state = 4
        st.rerun()
        return
    
    current_q = st.session_state.all_questions[st.session_state.current_question_idx]
    
    # Display question
    st.markdown('<div class="question-card">', unsafe_allow_html=True)
    st.markdown(f"### Question {st.session_state.current_question_idx + 1} of 10")
    st.markdown(f"**{current_q['question_text']}**")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Learning mode features
    if st.session_state.candidate_context["mode"] == "Learning":
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💡 Get Hint"):
                with st.spinner("Generating hint..."):
                    hint_prompt = PromptTemplates.get_hint_prompt(current_q)
                    messages = [{"role": "user", "content": hint_prompt}]
                    hint = st.session_state.llm.generate(messages, temperature=0.7, max_tokens=200)
                    
                    if not hint.startswith("LLM_"):
                        st.markdown('<div class="info-box">', unsafe_allow_html=True)
                        st.markdown(f"**Hint:** {hint}")
                        st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            if st.button("📖 Explain Concept"):
                with st.spinner("Generating explanation..."):
                    explain_prompt = PromptTemplates.get_concept_explanation_prompt(current_q)
                    messages = [{"role": "user", "content": explain_prompt}]
                    explanation = st.session_state.llm.generate(messages, temperature=0.7, max_tokens=300)
                    
                    if not explanation.startswith("LLM_"):
                        st.markdown('<div class="info-box">', unsafe_allow_html=True)
                        st.markdown(f"**Explanation:** {explanation}")
                        st.markdown('</div>', unsafe_allow_html=True)
    
    # Answer input
    answer = st.text_area(
        "Your Answer:",
        key=f"answer_{st.session_state.current_question_idx}",
        height=150,
        placeholder="Type your answer here... You can also say 'simplify the question' or 'I don't know'"
    )
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Submit Answer →", type="primary", use_container_width=True):
            if answer and len(answer.strip()) >= 3:
                # Handle special responses
                answer_lower = answer.lower().strip()
                
                if any(phrase in answer_lower for phrase in ["simplify", "simpler", "explain better", "don't understand"]):
                    with st.spinner("🤖 Simplifying the question..."):
                        simplify_prompt = f"Simplify this question for a beginner: {current_q['question_text']}"
                        messages = [{"role": "user", "content": simplify_prompt}]
                        simplified = st.session_state.llm.generate(messages, temperature=0.7, max_tokens=200)
                        
                        if not simplified.startswith("LLM_"):
                            st.markdown('<div class="info-box">', unsafe_allow_html=True)
                            st.markdown(f"**Simplified:** {simplified}")
                            st.markdown('</div>', unsafe_allow_html=True)
                            st.info("Please answer the simplified version above")
                    return
                
                elif any(phrase in answer_lower for phrase in ["don't know", "dont know", "no idea", "not sure"]):
                    if st.session_state.candidate_context["mode"] == "Learning":
                        st.markdown('<div class="warning-box">', unsafe_allow_html=True)
                        st.markdown("**That's okay!** In learning mode, we'll note this and move forward. Consider reviewing this topic later.")
                        st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="warning-box">', unsafe_allow_html=True)
                        st.markdown("**Noted.** We'll record this response and continue.")
                        st.markdown('</div>', unsafe_allow_html=True)
                
                # Store answer
                st.session_state.all_answers.append({
                    "question": current_q,
                    "answer": answer
                })
                
                st.session_state.current_question_idx += 1
                st.success("✅ Answer recorded!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("⚠️ Please provide an answer")


def state_4_final_report():
    """STATE 4: Comprehensive Final Report"""
    
    if not st.session_state.final_report:
        with st.spinner("🤖 AI is conducting comprehensive evaluation... This may take a moment."):
            eval_prompt = PromptTemplates.get_comprehensive_evaluation_prompt(
                st.session_state.candidate_context,
                st.session_state.all_questions,
                st.session_state.all_answers
            )
            messages = [{"role": "user", "content": eval_prompt}]
            response = st.session_state.llm.generate(messages, temperature=0.3, max_tokens=4000)
            
            if response.startswith("LLM_"):
                handle_llm_error(response)
                return
            
            report = parse_llm_response(response)
            
            if not report:
                st.error("⚠️ Error generating report.")
                return
            
            st.session_state.final_report = report
    
    report = st.session_state.final_report
    
    # Header
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("## 📊 Comprehensive Evaluation Report")
    st.markdown(f"**Candidate:** {st.session_state.candidate_context['name']}")
    st.markdown(f"**Role:** {st.session_state.candidate_context['role']}")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Overall Metrics
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 📈 Overall Performance")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Technical Score", f"{report.get('overall_technical_score', 0):.1f}/10")
    with col2:
        st.metric("Communication", f"{report.get('communication_score', 0):.1f}/10")
    with col3:
        st.metric("Authenticity", f"{report.get('authenticity_score', 0):.1f}/10")
    with col4:
        st.metric("Final Score", f"{report.get('final_score', 0):.1f}/10")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Plagiarism Analysis
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 🔍 Authenticity & Plagiarism Check")
    
    plag = report.get('plagiarism_analysis', {})
    verdict = plag.get('verdict', 'Unclear')
    
    if verdict == 'Genuine':
        st.markdown('<div class="success-box">', unsafe_allow_html=True)
        st.markdown(f"**✅ Verdict: {verdict}**")
    elif verdict == 'Suspicious':
        st.markdown('<div class="error-box">', unsafe_allow_html=True)
        st.markdown(f"**⚠️ Verdict: {verdict}**")
    else:
        st.markdown('<div class="warning-box">', unsafe_allow_html=True)
        st.markdown(f"**❓ Verdict: {verdict}**")
    
    st.markdown(f"**Analysis:** {plag.get('reasoning', 'N/A')}")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Tone Analysis
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 🎭 Communication & Tone Analysis")
    tone = report.get('tone_analysis', {})
    st.markdown(f"**Overall Tone:** {tone.get('overall_tone', 'N/A')}")
    st.markdown(f"**Confidence Level:** {tone.get('confidence_level', 'N/A')}")
    st.markdown(f"**Professionalism:** {tone.get('professionalism', 'N/A')}")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Question-by-Question Analysis
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 📝 Detailed Question Analysis")
    
    for i, qa_analysis in enumerate(report.get('question_analysis', [])):
        with st.expander(f"Question {i+1}: {qa_analysis.get('question', '')[:100]}..."):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Your Answer:**")
                st.markdown(qa_analysis.get('user_answer', 'N/A')[:300] + "...")
                st.markdown(f"**Score:** {qa_analysis.get('score', 0):.1f}/10")
            
            with col2:
                st.markdown("**Expected Answer:**")
                st.markdown(qa_analysis.get('expected_answer', 'N/A'))
                st.markdown(f"**Feedback:** {qa_analysis.get('feedback', 'N/A')}")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Strengths & Improvements
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### ✅ Strengths")
        for strength in report.get('strengths', []):
            st.markdown(f"- {strength}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 📈 Areas for Improvement")
        for gap in report.get('areas_for_improvement', []):
            st.markdown(f"- {gap}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Final Recommendation
    st.markdown('<div class="card">', unsafe_allow_html=True)
    recommendation = report.get('hire_recommendation', 'Maybe')
    
    if recommendation == 'Yes':
        st.markdown('<div class="success-box">', unsafe_allow_html=True)
        st.markdown("### ✅ Recommendation: HIRE")
    elif recommendation == 'No':
        st.markdown('<div class="error-box">', unsafe_allow_html=True)
        st.markdown("### ❌ Recommendation: DO NOT HIRE")
    else:
        st.markdown('<div class="warning-box">', unsafe_allow_html=True)
        st.markdown("### 🤔 Recommendation: FURTHER EVALUATION NEEDED")
    
    st.markdown(f"**Reasoning:** {report.get('detailed_reasoning', 'N/A')}")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Actions
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Export Report", use_container_width=True):
            st.session_state.chat_manager.export_to_text()
            st.success("✅ Report exported!")
    
    with col2:
        if st.button("🔄 New Interview", type="primary", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


def main():
    """Main application"""
    initialize_session_state()
    render_header()
    render_sidebar()
    
    if st.session_state.state == 0:
        state_0_greeting()
    elif st.session_state.state == 1:
        state_1_profile_setup()
    elif st.session_state.state == 2:
        state_2_generate_questions()
    elif st.session_state.state == 3:
        state_3_interview()
    elif st.session_state.state == 4:
        state_4_final_report()


if __name__ == "__main__":
    main()
