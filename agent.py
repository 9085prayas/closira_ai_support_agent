import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field


class ExtractedDetail(BaseModel):
    key: str = Field(description="The name of the attribute (e.g., 'treatment_area', 'past_history')")
    value: str = Field(description="The value of the attribute")

class AIResponseSchema(BaseModel):
    reply_to_user: str = Field(
        description="The warm, professional response to display directly to the client."
    )
    is_out_of_scope: bool = Field(
        description="Set to true ONLY if the user asks a specific question that the SOP cannot answer. False for greetings, small talk, or lead qualification.",
        default=False
    )
    should_escalate: bool = Field(
        description="Set to true ONLY if the user is angry, abusive, asks a medical question, or attempts to negotiate price."
    )
    escalation_reason: str = Field(
        default="", 
        description="Provide a brief explanation for the human handoff if should_escalate is true."
    )
    lead_details_extracted: list[ExtractedDetail] = Field(
        default_factory=list, 
        description="Any new qualification metrics safely gathered during this specific turn."
    )

class SummarySchema(BaseModel):
    customer_intent: str = Field(description="The primary objective or reason behind the customer's reaching out.")
    key_details_collected: list[ExtractedDetail] = Field(
        default_factory=list,
        description="Consolidated overview of all gathered customer metrics."
    )
    sop_gaps_identified: list[str] = Field(description="List of raw questions asked by the customer that could not be solved by the SOP.")
    recommended_next_action: str = Field(description="Clear, actionable next step for the human team.")

# =====================================================================
# CORE AGENT CLASS (GEMINI IMPLEMENTATION)
# =====================================================================

class ClosiraSupportAgent:
    def __init__(self, api_key: str, sop_path: str = "data/sop.json"):
        self.client = genai.Client(api_key=api_key)
        self.conversation_history: list[types.Content] = []
        self.unanswered_counter: int = 0
        self.lead_profile: dict = {}
        
        with open(sop_path, "r", encoding="utf-8") as f:
            self.sop_data = json.load(f)

    def _build_system_prompt(self) -> str:
        return f"""
You are the frontline customer success agent for "{self.sop_data['business_name']}". Your goal is to provide exceptional, human-like service via messaging platforms (like WhatsApp) while strictly adhering to the company's Standard Operating Procedure (SOP).

### 🏢 SOP DATA (SOURCE OF TRUTH)
{json.dumps(self.sop_data, indent=2)}

### 🛑 STRICT BEHAVIORAL RULES
1. ANTI-HALLUCINATION (Zero-Tolerance): You may ONLY provide information explicitly stated in the SOP DATA. If a customer asks about a service, price, timeline, or policy not listed, you must explicitly state that you need to check with the team, and set `is_out_of_scope = true`. DO NOT invent, assume, or guess information.
2. LEAD QUALIFICATION: If a customer shows intent to book or learn more, guide them through the `lead_qualification_questions` defined in the SOP. 
   - CRITICAL: Ask only ONE qualification question per turn. Never interrogate the user with multiple questions at once.
   - Weave the question naturally into your helpful response.
3. ESCALATION TRIGGERS: You must set `should_escalate = true` immediately ONLY if the user:
   - Expresses frustration, anger, or explicitly asks for a human/manager.
   - Asks a medical, diagnostic, or clinical safety question.
   - Attempts to negotiate prices or ask for unlisted discounts.
   (Do NOT escalate for greetings, small talk, or answering your questions. Do NOT escalate just because something is out of scope—use the `is_out_of_scope` flag for that).

### 🗣️ TONE & PERSONA
- Platform constraint: This is a WhatsApp/SMS environment. 
- Style: Warm, empathetic, professional, and concise. 
- Length: Keep responses brief (1-3 short sentences maximum). Never output large walls of text.
- IMMERSION (CRITICAL): You are roleplaying as a HUMAN receptionist. You must NEVER break character. NEVER refer to yourself as an "AI", a "bot", or an "assistant". If a customer asks about your personal life or experiences, politely deflect with a warm, human response and steer the conversation back to their clinic needs.
"""

    def process_turn(self, user_input: str) -> AIResponseSchema:
        self.conversation_history.append(
            types.Content(role="user", parts=[types.Part.from_text(text=user_input)])
        )
        
        response = self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=self.conversation_history,
            config=types.GenerateContentConfig(
                system_instruction=self._build_system_prompt(),
                response_mime_type="application/json",
                response_schema=AIResponseSchema,
                temperature=0.2, 
            )
        )
        
        structured_output: AIResponseSchema = response.parsed
        
        # Track out-of-scope trends safely
        if structured_output.is_out_of_scope:
            self.unanswered_counter += 1
        else:
            self.unanswered_counter = 0 
        
        if self.unanswered_counter >= 2:
            structured_output.should_escalate = True
            structured_output.escalation_reason = (
                f"Escalated automatically: Customer reached out with {self.unanswered_counter} "
                "consecutive out-of-scope/unanswered inquiries."
            )

        self.conversation_history.append(
            types.Content(role="model", parts=[types.Part.from_text(text=structured_output.reply_to_user)])
        )
        
        # Convert the returned list of ExtractedDetail objects back into our local Python dictionary
        if structured_output.lead_details_extracted:
            for detail in structured_output.lead_details_extracted:
                self.lead_profile[detail.key] = detail.value
            
        return structured_output

    def generate_session_summary(self) -> SummarySchema:
        history_text = "\n".join([
            f"{msg.role}: {msg.parts[0].text}" for msg in self.conversation_history
        ])

        analysis_prompt = f"""
Analyze the comprehensive dialog dataset provided below to extract structural takeaways.

TRANSCRIPT:
{history_text}

LATEST EXTRACTED PROFILE ATTRIBUTES:
{json.dumps(self.lead_profile, indent=2)}
"""
        response = self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=analysis_prompt,
            config=types.GenerateContentConfig(
                system_instruction="You are a backend business data analytical engine tasked with generating structured interaction logs.",
                response_mime_type="application/json",
                response_schema=SummarySchema,
                temperature=0.1,
            )
        )
        return response.parsed