import pandas as pd
import spacy
from spacy.matcher import PhraseMatcher
from collections import Counter
import re

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Downloading language model...")
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

ALL_KNOWN_SKILLS = [
    
    "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Go", "Rust", "Swift", "Kotlin", "PHP", "Ruby", "SQL", "R", "Matlab",
    
    "React", "Angular", "Vue", "Next.js", "Node.js", "Django", "Flask", "Spring Boot", "ASP.NET", "Laravel", "HTML", "CSS", "Redux", "jQuery", "Bootstrap", "Tailwind",
   
    "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "Pandas", "NumPy", "Scikit-learn", "Keras", "OpenCV", "NLP", "LLM", "Generative AI", "Hugging Face",
   
    "AWS", "Azure", "Google Cloud", "GCP", "Docker", "Kubernetes", "Jenkins", "Terraform", "Ansible", "Linux", "Git", "CI/CD", "GitHub", "GitLab",
    
    "Unity", "Unreal Engine", "Godot", "OpenGL", "DirectX", "Shaders", "Blender", "Maya", "3D Math", "Physics", "C#", "Lua",
   
    "PostgreSQL", "MongoDB", "MySQL", "Redis", "Elasticsearch", "Oracle", "DynamoDB", "Firebase",
    
    "Agile", "Scrum", "JIRA", "Rest API", "GraphQL", "Microservices"
]


matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
patterns = [nlp.make_doc(text) for text in ALL_KNOWN_SKILLS]
matcher.add("TECH_SKILL", patterns)

def extract_skills(df):
    """
    Uses NLP to find skills in Title (and Description if available).
    """
    if df.empty:
        return pd.DataFrame(columns=['Skill', 'Count'])

    skill_counter = Counter()

    for index, row in df.iterrows():
        title_text = str(row.get('Title', ''))
        desc_text = str(row.get('description', ''))
        
        full_text = f"{title_text} {title_text} {desc_text}"
        
        doc = nlp(full_text)
        matches = matcher(doc)
        
        found_in_this_job = set()
        for match_id, start, end in matches:
            span = doc[start:end]
            found_in_this_job.add(span.text)
            
        skill_counter.update(found_in_this_job)

    if not skill_counter:
        return pd.DataFrame(columns=['Skill', 'Count'])
        
    skills_df = pd.DataFrame(skill_counter.items(), columns=['Skill', 'Count'])
    return skills_df.sort_values(by='Count', ascending=False).head(20)

def clean_location(location_text):
    if not isinstance(location_text, str): return "Unknown"
    return location_text.split(",")[0].strip()