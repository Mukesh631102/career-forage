# recommender.py

def recommend_careers(skills):
    """
    Recommends career paths based on provided skills.
    Input: List of skills (e.g. ["python", "sql"])
    Output: List of career paths (e.g. ["Data Analyst", "ML Engineer"])
    """
    mapping = {
        "python": ["Data Analyst", "ML Engineer", "Backend Developer"],
        "sql": ["Data Analyst", "Database Administrator"],
        "html": ["Frontend Developer"],
        "css": ["Frontend Developer"],
        "javascript": ["Frontend Developer", "Full Stack Developer"],
        "excel": ["Data Analyst"],
        "java": ["Android Developer", "Software Engineer"],
        "c++": ["System Programmer", "Competitive Programmer"],
        "design": ["UI/UX Designer", "Product Designer"],
    }

    recommended = set()
    for skill in skills:
        skill = skill.strip().lower()
        if skill in mapping:
            recommended.update(mapping[skill])

    return list(recommended)
