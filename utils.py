import os
import json
import re
import base64
from typing import Dict, List, Any, Optional
from io import BytesIO
import requests
from PIL import Image
import PyPDF2
from pdf2image import convert_from_bytes


def load_env_file(filepath: str = ".env"):
    """Load environment variables from .env file"""
    if not os.path.exists(filepath):
        return
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    os.environ[key] = value
    except Exception as e:
        print(f"Warning: Could not load .env file: {e}")


load_env_file()



class OpenRouterLLM:
    """Wrapper for OpenRouter API with vision support"""
    
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")
        
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        # Using correct OpenRouter model name
        self.text_model = "meta-llama/llama-3.1-8b-instruct"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8501",
            "X-Title": "AI Interview Platform"
        }
    
    
    def generate(self, messages: List[Dict[str, Any]], temperature: float = 0.7, 
                max_tokens: int = 2000, use_vision: bool = False) -> str:
        """Generate response from OpenRouter API"""
        # Always use text model (vision disabled due to API issues)
        model = self.text_model
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(self.base_url, headers=self.headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            return "LLM_TIMEOUT"
        except requests.exceptions.RequestException as e:
            return f"LLM_ERROR: {str(e)}"
        except Exception as e:
            return f"LLM_ERROR: {str(e)}"
    
    
    def extract_resume_info(self, image_base64: str) -> Dict[str, Any]:
        """Extract information from resume using vision model"""
        # Simple text-based prompt for vision model
        prompt = """Extract ALL information from this resume image and return ONLY a JSON object.

Return this exact structure:
{
    "name": "full name",
    "email": "email",
    "phone": "phone",
    "location": "location",
    "skills": ["skill1", "skill2"],
    "experience_years": "X",
    "projects": [{"name": "project", "description": "desc", "technologies": ["tech1"]}],
    "internships": [{"company": "company", "role": "role", "duration": "duration", "description": "desc"}],
    "education": [{"degree": "degree", "institution": "university", "year": "year"}],
    "certifications": ["cert1"]
}

Extract everything you see. Return ONLY the JSON."""

        # Use vision model for image
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                ]
            }
        ]
        
        # Use google/gemini-flash-1.5 for vision
        payload = {
            "model": "mistralai/mistral-small-3.1-24b-instruct:free",
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1500
        }
        
        try:
            response = requests.post(self.base_url, headers=self.headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            llm_response = result["choices"][0]["message"]["content"]
            
            print(f"Vision LLM Response: {llm_response[:200]}...")
            
            if llm_response.startswith("LLM_"):
                return None
            
            return parse_llm_response(llm_response)
        except Exception as e:
            print(f"Vision extraction error: {e}")
            return None
    
    def extract_resume_from_text(self, resume_text: str) -> Dict[str, Any]:
        """Extract information from resume text (fallback method)"""
        # Truncate if too long
        if len(resume_text) > 3000:
            resume_text = resume_text[:3000] + "..."
        
        prompt = f"""Extract information from this resume and return ONLY a JSON object.

RESUME:
{resume_text}

Return ONLY this JSON structure (fill with actual data from resume):
{{
    "name": "candidate name",
    "email": "email address",
    "phone": "phone number",
    "location": "city/country",
    "skills": ["skill1", "skill2", "skill3"],
    "experience_years": "number of years",
    "projects": [{{"name": "project name", "description": "what it does", "technologies": ["tech1", "tech2"]}}],
    "internships": [{{"company": "company name", "role": "role", "duration": "when", "description": "what you did"}}],
    "education": [{{"degree": "degree name", "institution": "university", "year": "year"}}],
    "certifications": ["cert1", "cert2"]
}}

Extract ALL information you can find. Return ONLY the JSON, no explanation."""

        messages = [{"role": "user", "content": prompt}]
        
        try:
            response = self.generate(messages, temperature=0.2, max_tokens=1500, use_vision=False)
            
            print(f"LLM Response: {response[:200]}...")  # Debug log
            
            if response.startswith("LLM_"):
                print(f"LLM Error: {response}")
                return None
            
            parsed = parse_llm_response(response)
            
            if not parsed:
                print(f"Failed to parse response: {response[:500]}")
            
            return parsed
        except Exception as e:
            print(f"Exception in extract_resume_from_text: {e}")
            return None


class ResumeProcessor:
    """Process resume files (PDF/Image) for information extraction"""
    
    @staticmethod
    def pdf_to_image(pdf_bytes: bytes) -> Optional[str]:
        """Convert PDF first page to base64 image (requires Poppler)"""
        try:
            images = convert_from_bytes(pdf_bytes, first_page=1, last_page=1)
            if images:
                img = images[0]
                buffered = BytesIO()
                img.save(buffered, format="JPEG", quality=85)
                img_base64 = base64.b64encode(buffered.getvalue()).decode()
                return img_base64
            return None
        except Exception as e:
            print(f"PDF conversion error: {e}")
            return None
    
    @staticmethod
    def pdf_to_text(pdf_bytes: bytes) -> Optional[str]:
        """Extract text from PDF (fallback when Poppler not available)"""
        try:
            pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_bytes))
            text = ""
            for page in pdf_reader.pages[:3]:  # First 3 pages
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            print(f"PDF text extraction error: {e}")
            return None
    
    @staticmethod
    def image_to_base64(image_bytes: bytes) -> Optional[str]:
        """Convert image to base64"""
        try:
            img = Image.open(BytesIO(image_bytes))
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=85)
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            return img_base64
        except Exception as e:
            print(f"Image conversion error: {e}")
            return None


class PromptTemplates:
    """AI prompt templates for interview intelligence"""
    
    @staticmethod
    def get_initial_6_questions_prompt(candidate_context: Dict[str, Any]) -> str:
        """AI generates first 6 questions for initial assessment"""
        projects_info = ""
        if candidate_context.get('projects'):
            projects_info = "\nPROJECTS:\n" + "\n".join([
                f"- {p['name']}: {p.get('description', '')} (Tech: {', '.join(p.get('technologies', []))})"
                for p in candidate_context['projects'][:3]
            ])
        
        internships_info = ""
        if candidate_context.get('internships'):
            internships_info = "\nINTERNSHIPS:\n" + "\n".join([
                f"- {i.get('company', '')}: {i.get('role', '')} - {i.get('description', '')}"
                for i in candidate_context['internships'][:3]
            ])
        
        certifications_info = ""
        if candidate_context.get('certifications'):
            certifications_info = "\nCERTIFICATIONS:\n" + "\n".join([
                f"- {c}" for c in candidate_context['certifications'][:5]
            ])
        
        difficulty = candidate_context.get('difficulty', 'Intermediate')
        
        return f"""Generate 6 RESUME-BASED technical questions for initial assessment.

CANDIDATE PROFILE:
- Name: {candidate_context['name']}
- Role: {candidate_context['role']}
- Experience: {candidate_context['experience']} years
- Tech Stack: {candidate_context['tech_stack']}
- Difficulty Level: {difficulty}{projects_info}{internships_info}{certifications_info}

CRITICAL INSTRUCTIONS:
1. If they have PROJECTS → Ask about their technical decisions, challenges, and implementations
2. If they have INTERNSHIPS → Ask about their work experience and what they learned
3. If they have CERTIFICATIONS → Ask about the certified technologies
4. If NO resume details → Ask general questions about their tech stack

TASK: Generate EXACTLY 6 questions that:
1. Progress from EASY → MEDIUM → HARD
2. Are SPECIFIC to their resume (projects, internships, certifications)
3. Match the {difficulty} difficulty level
4. Cover different aspects:
   - Project implementation details
   - Internship experience
   - Certified technologies
   - Problem-solving in their projects
   - Technical decisions they made

Return ONLY valid JSON:
{{
    "questions": [
        {{
            "id": 1,
            "skill": "specific_technology_from_resume",
            "concept": "fundamental_concept",
            "difficulty": "easy",
            "question_text": "In your [specific project], you used [technology]. Can you explain [basic concept]?"
        }},
        {{
            "id": 2,
            "skill": "project_technology",
            "concept": "practical_application",
            "difficulty": "easy",
            "question_text": "During your internship at [company], what was your approach to [task]?"
        }},
        {{
            "id": 3,
            "skill": "certification_technology",
            "concept": "intermediate_concept",
            "difficulty": "medium",
            "question_text": "You're certified in [technology]. How would you [intermediate task]?"
        }},
        {{
            "id": 4,
            "skill": "project_challenge",
            "concept": "problem_solving",
            "difficulty": "medium",
            "question_text": "What was the biggest technical challenge in [project name] and how did you solve it?"
        }},
        {{
            "id": 5,
            "skill": "advanced_concept",
            "concept": "technical_decision",
            "difficulty": "hard",
            "question_text": "In [project], why did you choose [technology] over alternatives?"
        }},
        {{
            "id": 6,
            "skill": "expert_concept",
            "concept": "architecture",
            "difficulty": "hard",
            "question_text": "How would you scale [their project] to handle [advanced scenario]?"
        }}
    ]
}}

IMPORTANT: 
- Reference their ACTUAL projects, internships, and certifications
- Make questions SPECIFIC to their resume
- If no resume details, ask general tech stack questions

Return ONLY the JSON object."""

    @staticmethod
    def get_adaptive_4_questions_prompt(candidate_context: Dict[str, Any],
                                       first_6_questions: List[Dict[str, Any]],
                                       first_6_answers: List[Dict[str, Any]]) -> str:
        """AI generates 4 adaptive questions based on first 6 answers"""
        
        qa_summary = "\n".join([
            f"Q{i+1}: {qa['question']['question_text']}\nAnswer: {qa['answer'][:200]}..."
            for i, qa in enumerate(first_6_answers)
        ])
        
        projects_info = ""
        if candidate_context.get('projects'):
            projects_info = "\n".join([
                f"- {p['name']}: {p.get('description', '')}"
                for p in candidate_context['projects'][:3]
            ])
        
        return f"""Generate 4 adaptive follow-up questions based on the candidate's performance.

CANDIDATE PROFILE:
- Role: {candidate_context['role']}
- Experience: {candidate_context['experience']} years
- Projects:
{projects_info if projects_info else "No projects listed"}

THEIR FIRST 6 ANSWERS:
{qa_summary}

TASK: Analyze their answers and generate 4 questions that:
1. Probe deeper into areas where they showed weakness
2. Explore their project experience in detail
3. Test practical application of concepts they mentioned
4. Challenge their understanding with real-world scenarios

Return ONLY valid JSON:
{{
    "questions": [
        {{
            "id": 7,
            "skill": "area_to_probe",
            "concept": "deeper_concept",
            "difficulty": "adaptive",
            "question_text": "Based on your answer about [X], can you explain [Y]?"
        }},
        {{
            "id": 8,
            "skill": "project_related",
            "concept": "practical_application",
            "difficulty": "adaptive",
            "question_text": "In your [project name], how did you handle [specific challenge]?"
        }},
        {{
            "id": 9,
            "skill": "weakness_area",
            "concept": "clarification",
            "difficulty": "adaptive",
            "question_text": "You mentioned [concept]. Can you elaborate on [specific aspect]?"
        }},
        {{
            "id": 10,
            "skill": "real_world",
            "concept": "problem_solving",
            "difficulty": "adaptive",
            "question_text": "How would you solve [real-world scenario related to their answers]?"
        }}
    ]
}}

Make questions SPECIFIC to their answers and projects. Return ONLY the JSON."""

    @staticmethod
    def get_comprehensive_evaluation_prompt(candidate_context: Dict[str, Any],
                                           all_questions: List[Dict[str, Any]],
                                           all_answers: List[Dict[str, Any]]) -> str:
        """AI conducts comprehensive evaluation with tone, plagiarism, and expected answers"""
        
        qa_pairs = "\n\n".join([
            f"Q{i+1} ({qa['question'].get('skill', 'N/A')}): {qa['question']['question_text']}\n"
            f"Candidate's Answer: {qa['answer']}"
            for i, qa in enumerate(all_answers)
        ])
        
        return f"""Conduct a COMPREHENSIVE evaluation of this interview.

CANDIDATE PROFILE:
- Name: {candidate_context['name']}
- Role: {candidate_context['role']}
- Experience: {candidate_context['experience']} years
- Tech Stack: {candidate_context['tech_stack']}
- Mode: {candidate_context.get('mode', 'Interview')}

COMPLETE INTERVIEW TRANSCRIPT:
{qa_pairs}

EVALUATION TASK:

Analyze EVERY aspect:

1. **Technical Assessment** (0-10 scale)
   - Depth of knowledge
   - Accuracy of answers
   - Problem-solving ability

2. **Communication & Tone Analysis**
   - Overall tone (professional/casual/nervous/confident)
   - Confidence level (high/medium/low)
   - Professionalism score
   - Clarity of expression

3. **Plagiarism & Authenticity Check**
   - Are answers genuine or memorized?
   - Generic vs personalized responses
   - Consistency across answers
   - Verdict: Genuine/Suspicious/Unclear

4. **Question-by-Question Analysis**
   - For EACH question, provide:
     * User's answer
     * Expected/ideal answer
     * Score (0-10)
     * Specific feedback

Return ONLY valid JSON:
{{
    "overall_technical_score": 7.5,
    "communication_score": 8.0,
    "authenticity_score": 9.0,
    "final_score": 8.0,
    "tone_analysis": {{
        "overall_tone": "Professional and confident",
        "confidence_level": "High",
        "professionalism": "Strong"
    }},
    "plagiarism_analysis": {{
        "verdict": "Genuine",
        "reasoning": "Answers show personal understanding with specific examples"
    }},
    "question_analysis": [
        {{
            "question": "Question text",
            "user_answer": "Their answer",
            "expected_answer": "What we expected to hear",
            "score": 8.0,
            "feedback": "Specific feedback on this answer"
        }}
    ],
    "strengths": [
        "Specific strength with example",
        "Another strength"
    ],
    "areas_for_improvement": [
        "Specific area with suggestion",
        "Another area"
    ],
    "hire_recommendation": "Yes",
    "detailed_reasoning": "Comprehensive 4-5 sentence justification covering technical skills, communication, authenticity, and role fit"
}}

SCORING: 0-10 for all metrics
RECOMMENDATION: "Yes" | "Maybe" | "No"

Be thorough, fair, and provide actionable feedback. Return ONLY the JSON object."""

    @staticmethod
    def get_answer_evaluation_prompt(question: Dict[str, Any], answer: str, mode: str) -> str:
        """AI evaluates answer with nuanced understanding"""
        return f"""You are an expert technical interviewer evaluating a candidate's answer.

QUESTION CONTEXT:
- Skill: {question['skill']}
- Concept: {question['concept']}
- Difficulty: {question['difficulty']}
- Question: {question['question_text']}

CANDIDATE'S ANSWER:
{answer}

INTERVIEW MODE: {mode}

EVALUATION TASK:
Analyze this answer comprehensively considering:
1. Technical correctness and accuracy
2. Depth of understanding
3. Clarity of explanation
4. Completeness of response
5. Confidence level (detect hesitation phrases)
6. Practical knowledge vs theoretical
7. Whether follow-up is needed to probe deeper

Return ONLY valid JSON:
{{
    "score": 0.85,
    "correctness": "correct",
    "confidence_level": "high",
    "has_hesitation": false,
    "clarity": "clear",
    "completeness": "complete",
    "depth_of_understanding": "strong",
    "practical_knowledge": true,
    "feedback": "Specific, constructive feedback in 1-2 sentences",
    "needs_followup": true,
    "followup_reason": "depth",
    "key_strengths": ["strength1", "strength2"],
    "areas_to_probe": ["area1"]
}}

SCORING: 0.9-1.0=Excellent, 0.7-0.9=Good, 0.5-0.7=Partial, 0.3-0.5=Weak, 0.0-0.3=Incorrect
Return ONLY the JSON object."""

    @staticmethod
    def get_followup_question_prompt(question: Dict[str, Any], answer: str, evaluation: Dict[str, Any]) -> str:
        """AI generates intelligent follow-up question"""
        followup_type = evaluation.get('followup_reason', 'depth')
        
        return f"""Generate ONE intelligent follow-up question.

ORIGINAL: {question['question_text']}
ANSWER: {answer}
EVALUATION: {evaluation.get('correctness')} | {evaluation.get('confidence_level')} confidence
TYPE: {followup_type}

STRATEGIES:
- depth: Probe deeper, ask about edge cases
- clarification: Ask for specific examples
- recovery: Guide to correct understanding
- applied: Real-world application

Return ONLY valid JSON:
{{
    "followup_type": "{followup_type}",
    "skill": "{question['skill']}",
    "concept": "related_concept",
    "question": "Natural follow-up question?",
    "rationale": "Why this matters"
}}"""

    @staticmethod
    def get_project_based_followups_prompt(candidate_context: Dict[str, Any], 
                                           all_qa_pairs: List[Dict[str, Any]]) -> str:
        """AI generates 4 follow-up questions based on answers and projects"""
        
        # Summarize answers
        qa_summary = "\n".join([
            f"Q{i+1}: {qa['question']['question_text']}\nAnswer: {qa['answer'][:200]}..."
            for i, qa in enumerate(all_qa_pairs)
        ])
        
        projects_info = ""
        if candidate_context.get('projects'):
            projects_info = "\n".join([
                f"- {p['name']}: {p.get('description', '')} (Tech: {', '.join(p.get('technologies', []))})"
                for p in candidate_context['projects']
            ])
        
        return f"""Generate 4 intelligent follow-up questions based on the candidate's answers and projects.

CANDIDATE PROFILE:
- Role: {candidate_context['role']}
- Experience: {candidate_context['experience']} years
- Projects:
{projects_info if projects_info else "No projects listed"}

THEIR ANSWERS SO FAR:
{qa_summary}

Generate 4 follow-up questions that:
1. Probe deeper into their project experience
2. Connect their answers to real-world scenarios
3. Test practical application of concepts they mentioned
4. Explore technical decisions in their projects

Return ONLY valid JSON:
{{
    "questions": [
        {{
            "id": 1,
            "type": "project_deep_dive",
            "question": "Based on your [specific project], can you explain [specific technical aspect]?",
            "rationale": "Tests practical application"
        }},
        {{
            "id": 2,
            "type": "answer_expansion",
            "question": "You mentioned [concept from answer]. How would you apply this in [scenario]?",
            "rationale": "Connects theory to practice"
        }},
        {{
            "id": 3,
            "type": "technical_decision",
            "question": "In your [project], why did you choose [technology]? What were the trade-offs?",
            "rationale": "Evaluates decision-making"
        }},
        {{
            "id": 4,
            "type": "problem_solving",
            "question": "What was the biggest technical challenge in [project] and how did you solve it?",
            "rationale": "Tests problem-solving ability"
        }}
    ]
}}

Make questions specific to THEIR projects and answers. Return ONLY the JSON."""

    @staticmethod
    def get_final_evaluation_prompt(candidate_context: Dict[str, Any], 
                                    all_qa_pairs: List[Dict[str, Any]],
                                    followup_answers: List[Dict[str, Any]]) -> str:
        """AI conducts comprehensive final evaluation with plagiarism check"""
        
        # Technical Q&A summary
        qa_summary = "\n\n".join([
            f"Q{i+1} ({qa['question']['skill']} - {qa['question']['difficulty']}): {qa['question']['question_text']}\n"
            f"Answer: {qa['answer']}\n"
            f"Score: {qa['evaluation'].get('score', 0):.2f}\n"
            f"Feedback: {qa['evaluation'].get('feedback', '')}"
            for i, qa in enumerate(all_qa_pairs)
        ])
        
        # Follow-up summary
        followup_summary = "\n\n".join([
            f"Follow-up {i+1} ({ans['question'].get('type', 'general')}): {ans['question'].get('question', '')}\n"
            f"Answer: {ans['answer']}"
            for i, ans in enumerate(followup_answers)
        ])
        
        projects_info = ""
        if candidate_context.get('projects'):
            projects_info = "\n".join([
                f"- {p['name']}: {p.get('description', '')} ({', '.join(p.get('technologies', []))})"
                for p in candidate_context['projects']
            ])
        
        return f"""You are a senior technical hiring manager conducting a COMPREHENSIVE final evaluation.

CANDIDATE PROFILE:
- Name: {candidate_context['name']}
- Role: {candidate_context['role']}
- Experience: {candidate_context['experience']} years
- Tech Stack: {candidate_context['tech_stack']}
- Projects:
{projects_info if projects_info else "No projects listed"}

TECHNICAL INTERVIEW TRANSCRIPT:
{qa_summary}

PROJECT-BASED FOLLOW-UP QUESTIONS:
{followup_summary}

COMPREHENSIVE EVALUATION TASK:

Analyze the ENTIRE interview and provide:

1. **Technical Assessment**: Depth of knowledge, practical application
2. **Plagiarism & Authenticity Check**: 
   - Analyze if answers seem memorized/copied vs genuine understanding
   - Check for generic/templated responses vs personalized answers
   - Evaluate consistency across answers
   - Flag any suspicious patterns
3. **Project Authenticity**: Do their project answers align with claimed experience?
4. **Communication Quality**: Clarity, structure, professionalism
5. **Problem-Solving Ability**: Approach to challenges
6. **Overall Competency**: Ready for the role?

Return ONLY valid JSON:
{{
    "technical_depth": 0.85,
    "conceptual_clarity": 0.80,
    "problem_solving": 0.75,
    "communication": 0.90,
    "confidence": 0.70,
    "project_authenticity": 0.85,
    "overall_score": 0.80,
    "plagiarism_analysis": {{
        "authenticity_score": 0.90,
        "concerns": ["concern1 if any"],
        "verdict": "Genuine|Suspicious|Unclear",
        "reasoning": "Why you think answers are genuine or suspicious"
    }},
    "strengths": [
        "Specific strength with example from interview",
        "Another strength with example",
        "Third strength"
    ],
    "gaps": [
        "Specific weakness with example",
        "Another area for improvement"
    ],
    "project_analysis": "How well do their project answers match their claimed experience?",
    "growth_observed": "Did they improve during interview?",
    "red_flags": ["any concerning patterns"],
    "hire_recommendation": "Yes",
    "confidence_in_recommendation": "high",
    "detailed_reasoning": "Comprehensive 4-5 sentence justification covering technical skills, authenticity, project experience, and role fit. Be specific and reference actual interview moments."
}}

SCORING: 0.0-1.0 for all metrics
PLAGIARISM VERDICT: "Genuine" | "Suspicious" | "Unclear"
RECOMMENDATION: "Yes" | "Maybe" | "No"
CONFIDENCE: "high" | "medium" | "low"

Be thorough, fair, and HONEST about plagiarism concerns.

Return ONLY the JSON object."""

    @staticmethod
    def get_hint_prompt(question: Dict[str, Any]) -> str:
        """AI generates helpful hint"""
        return f"""Provide a helpful hint for this question without giving the answer:

QUESTION: {question['question_text']}
SKILL: {question['skill']}

Return ONLY the hint text (1-2 sentences)."""

    @staticmethod
    def get_concept_explanation_prompt(question: Dict[str, Any]) -> str:
        """AI explains concept"""
        return f"""Explain the concept behind this question clearly:

QUESTION: {question['question_text']}
CONCEPT: {question['concept']}

Return ONLY the explanation (2-3 sentences with example)."""


class ChatHistoryManager:
    """Manages chat history and conversation state"""
    
    def __init__(self):
        self.chat_history: List[Dict[str, str]] = []
        self.technical_qa_pairs: List[Dict[str, Any]] = []
        self.followup_answers: List[Dict[str, Any]] = []
    
    def add_message(self, role: str, content: str):
        self.chat_history.append({"role": role, "content": content})
    
    def add_technical_qa(self, question: Dict[str, Any], answer: str, evaluation: Dict[str, Any],
                         followup_question: Optional[Dict[str, Any]] = None,
                         followup_answer: Optional[str] = None):
        self.technical_qa_pairs.append({
            "question": question,
            "answer": answer,
            "evaluation": evaluation,
            "followup_question": followup_question,
            "followup_answer": followup_answer
        })
    
    def add_followup_answer(self, question: Dict[str, Any], answer: str):
        """Add project-based follow-up answer"""
        self.followup_answers.append({
            "question": question,
            "answer": answer
        })
    
    
    def get_chat_history(self) -> List[Dict[str, str]]:
        return self.chat_history
    
    def get_technical_qa_pairs(self) -> List[Dict[str, Any]]:
        return self.technical_qa_pairs
    
    def get_followup_answers(self) -> List[Dict[str, Any]]:
        """Get all project-based follow-up answers"""
        return self.followup_answers
    
    def get_performance_insights(self) -> Dict[str, Any]:
        weaknesses = []
        strengths = []
        
        for qa in self.technical_qa_pairs:
            eval_data = qa.get('evaluation', {})
            score = eval_data.get('score', 0)
            skill = qa['question'].get('skill', 'Unknown')
            
            if score < 0.6:
                weaknesses.append(skill)
            elif score > 0.8:
                strengths.append(skill)
        
        return {
            "observed_weaknesses": list(set(weaknesses)),
            "observed_strengths": list(set(strengths))
        }
    
    def export_to_text(self, filename: str = "interview_transcript.txt"):
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=== AI-DRIVEN INTERVIEW TRANSCRIPT ===\n\n")
            for msg in self.chat_history:
                f.write(f"{msg['role'].upper()}: {msg['content']}\n\n")


def parse_llm_response(response: str) -> Optional[Dict[str, Any]]:
    """Parse LLM response to extract JSON object with robust error handling"""
    if response.startswith("LLM_"):
        return None
    
    try:
        # Remove markdown code blocks
        if '```' in response:
            parts = response.split('```')
            for part in parts:
                part_stripped = part.strip()
                if part_stripped.startswith('json') or part_stripped.startswith('{'):
                    response = part.replace('json', '').strip()
                    break
        
        # Find JSON object boundaries
        start_idx = response.find('{')
        end_idx = response.rfind('}')
        
        if start_idx != -1 and end_idx != -1:
            dict_str = response[start_idx:end_idx+1]
            
            # Clean up common issues
            dict_str = dict_str.replace('True', 'true').replace('False', 'false')
            dict_str = dict_str.replace('None', 'null')
            
            # Fix common escape sequence issues
            # Replace invalid escape sequences with safe versions
            
            # Fix paths and backslashes - replace single backslash with double
            # But be careful not to break valid JSON escapes like \n, \t, etc.
            def fix_escapes(match):
                text = match.group(1)
                # Replace backslashes that aren't followed by valid escape chars
                text = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', text)
                return f'"{text}"'
            
            # Fix escape sequences in string values
            dict_str = re.sub(r'"([^"]*)"', fix_escapes, dict_str)
            
            # Try to parse with strict=False for more lenient parsing
            try:
                return json.loads(dict_str, strict=False)
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                print(f"Problematic JSON substring: {dict_str[max(0, e.pos-50):min(len(dict_str), e.pos+50)]}")
                
                # Last resort: try to fix common JSON issues
                # Remove trailing commas
                dict_str = re.sub(r',(\s*[}\]])', r'\1', dict_str)
                
                # Try one more time
                return json.loads(dict_str, strict=False)
        
        return None
    except Exception as e:
        print(f"Error parsing LLM response: {e}")
        print(f"LLM Response: {response[:500]}...")
        return None
