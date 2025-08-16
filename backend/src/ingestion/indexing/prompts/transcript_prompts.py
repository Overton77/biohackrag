from ingestion.indexing.prompts.langsmith_client import langsmith_client  
from typing import Dict   
from langchain_core.prompts import PromptTemplate 







STRUCTURED_EXTRACTOR_PROMPTS: Dict[str, str] = {
    "product_information": (
        "Extract structured product data from the targeted summary. Use ONLY information in the summary—no external facts.\n"
        "Use the provided tool to submit product information with fields like name, description, features, protocols, benefits_as_stated, cost, buy_links, and attribution quotes.\n\n"
        "TARGETED SUMMARY:\n{summary}\n"
    ),
    "medical_treatment": (
        "Extract structured medical treatment/service data from the targeted summary. Use ONLY information in the summary—no external facts.\n"
        "Use the provided tool to submit medical treatment information with fields like name, description, procedure_or_protocol, outcomes_as_reported, risks_or_contraindications, confidence level, and attribution quotes.\n\n"
        "TARGETED SUMMARY:\n{summary}\n"
    ),
   
    "claims_made": (
        "Extract explicit claims from the targeted summary. Use ONLY information in the summary—no external facts.\n"
        "Use the provided tool to submit claims with fields like text, description, claim_type, speaker, evidence_present_in_transcript, and attribution quotes.\n\n"
        "TARGETED SUMMARY:\n{summary}\n"
    ),
    "businesses_entities": (
        "Extract businesses/organizations/entities from the targeted summary. Use ONLY information in the summary—no external facts.\n"
        "Use the provided tool to submit business/entity information with fields like canonical_name, aliases, role_or_relevance, biography, market_cap, first_timestamp, and attribution quotes.\n\n"
        "TARGETED SUMMARY:\n{summary}\n"
    ),
    "compounds": (
        "Extract compounds (e.g., supplements, herbs, adaptogens, foods) from the targeted summary. Use ONLY information in the summary—no external facts.\n"
        "Use the provided tool to submit compound information with fields like name, description, and type.\n\n"
        "TARGETED SUMMARY:\n{summary}\n"
    ),
} 




# ---------------------------
# Summarization prompts
# ---------------------------
SUMMARY_PROMPTS: Dict[str, str] = {
    "product_information": (
        "You are summarizing products discussed in the transcript to support downstream structured extraction. "
        "For each distinct product, produce a rich, self-contained entry that includes: (1) product name; (2) an extensive description "
        "(2–4 sentences capturing function, context of use, how it was characterized); (3) features (each with a brief explanation); "
        "(4) protocols or usage instructions if stated; and (5) benefits as stated.\n"
        "Critical formatting rule: after every single stated fact (each bullet, sentence, or field value), immediately add an <attribution> tag "
        "containing the exact quote in its original language and the timestamp, e.g., <attribution>\"…exact quote…\" | 00:12:34</attribution>. "
        "Do not invent facts. Keep quotes ≤20 words.\n\n"
        "Transcript:\n{transcript}"
    ),
    "medical_treatment": (
        "You are summarizing medical treatments or services mentioned in the transcript to support downstream structured extraction. "
        "For each treatment/service, include: (1) name; (2) procedure or protocol steps (ordered, concise); (3) outcomes as reported; "
        "(4) risks or contraindications; and (5) a brief narrative (2–3 sentences) giving context and details beyond simple lists.\n"
        "Critical formatting rule: after every single stated fact (each bullet, sentence, or field value), immediately add an <attribution> tag "
        "containing the exact quote in its original language and the timestamp, e.g., <attribution>\"…exact quote…\" | 00:12:34</attribution>. "
        "Do not invent facts. Keep quotes ≤20 words.\n\n"
        "Transcript:\n{transcript}"
    ),
    "high_level_overview": (
        "Provide a high-level overview aligned with downstream fields: (1) purpose of the conversation; (2) participants; (3) main sections "
        "with approximate time ranges when available; and (4) 5–7 key takeaways capturing the most important insights with added context. "
        "Write with clear, descriptive prose (2–4 sentences per subsection where appropriate).\n"
        "Critical formatting rule: after every single stated fact (each bullet, sentence, or field value), immediately add an <attribution> tag "
        "containing the exact quote in its original language and the timestamp, e.g., <attribution>\"…exact quote…\" | 00:12:34</attribution>. "
        "Do not invent facts. Keep quotes ≤20 words.\n\n"
        "Transcript:\n{transcript}"
    ),
    "claims_made": (
        "Identify explicit claims. For each claim, include: (1) speaker (if stated); (2) concise claim text (≤20 words if feasible); "
        "(3) claim type [causal | quantitative | experiential | other]; and (4) whether supporting evidence is present in the transcript [yes|no]. "
        "Provide a one-sentence explanation for each claim to add context beyond the minimal fields.\n"
        "Critical formatting rule: after every single stated fact (each bullet, sentence, or field value), immediately add an <attribution> tag "
        "containing the exact quote in its original language and the timestamp, e.g., <attribution>\"…exact quote…\" | 00:12:34</attribution>. "
        "Do not invent facts. Keep quotes ≤20 words.\n\n"
        "Transcript:\n{transcript}"
    ),
    "businesses_entities": (
        "List businesses/organizations/entities mentioned. For each entity, include: (1) canonical name; (2) aliases (if any); and (3) a concise, "
        "informative description (1–3 sentences) of the role/relevance as stated in the conversation.\n"
        "Critical formatting rule: after every single stated fact (each bullet, sentence, or field value), immediately add an <attribution> tag "
        "containing the exact quote in its original language and the timestamp, e.g., <attribution>\"…exact quote…\" | 00:12:34</attribution>. "
        "Do not invent facts. Keep quotes ≤20 words.\n\n"
        "Transcript:\n{transcript}"
    ),
    "compounds": (
        "You are summarizing compounds discussed in the transcript (e.g., supplements, herbs, adaptogens, foods) to support downstream structured extraction. "
        "For each distinct compound, include: (1) name; (2) an extensive description (2–4 sentences covering what it is, context of use, and mechanisms as discussed); "
        "(3) classification if stated or clearly implied [supplement | herb | food | other]; (4) typical form(s) or dosage(s) if stated; (5) protocols/stacking/co-ingredients if stated; "
        "(6) benefits as stated; and (7) risks or contraindications.\n"
        "Critical formatting rule: after every single stated fact (each bullet, sentence, or field value), immediately add an <attribution> tag "
        "containing the exact quote in its original language and the timestamp, e.g., <attribution>\"…exact quote…\" | 00:12:34</attribution>. "
        "Do not invent facts. Keep quotes ≤20 words.\n\n"
        "Transcript:\n{transcript}"
    ),
}




def push_prompts(suffix: str, prompt_dict: Dict[str, str]):
    for key, value in prompt_dict.items():
        prompt_name = f"{key}_{suffix}"
        prompt = PromptTemplate.from_template(value)
        langsmith_client.push_prompt(prompt_name, object=prompt)   


prompt_names = { 
    "structured": [
        "product_information_structured",
        "medical_treatment_structured",
       
        "claims_made_structured",
        "businesses_entities_structured",
    ], 
    "summary": [ 
        "product_information_summary",
        "medical_treatment_summary",
        "high_level_overview_summary",
        "claims_made_summary",
        "businesses_entities_summary",
        "compounds_summary",
    ]
} 

# Structured prompts
product_information_structured_prompt = langsmith_client.pull_prompt("product_information_structured")
medical_treatment_structured_prompt = langsmith_client.pull_prompt("medical_treatment_structured")
claims_made_structured_prompt = langsmith_client.pull_prompt("claims_made_structured")
businesses_entities_structured_prompt = langsmith_client.pull_prompt("businesses_entities_structured")

# Summary prompts 
product_information_summary_prompt = langsmith_client.pull_prompt("product_information_summary")
medical_treatment_summary_prompt = langsmith_client.pull_prompt("medical_treatment_summary")
high_level_overview_summary_prompt = langsmith_client.pull_prompt("high_level_overview_summary")
claims_made_summary_prompt = langsmith_client.pull_prompt("claims_made_summary")
businesses_entities_summary_prompt = langsmith_client.pull_prompt("businesses_entities_summary")
compounds_summary_prompt = langsmith_client.pull_prompt("compounds_summary")




if __name__ == "__main__": 
    print("Importing prompt functions")
    # push_prompts("structured", STRUCTURED_EXTRACTOR_PROMPTS)
    # push_prompts("summary", SUMMARY_PROMPTS)  

    print(product_information_structured_prompt.template)

    






