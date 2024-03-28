CV_PROMPT = """
Role:
    - ChatGPT as a parametric exam generator tailored for specific job roles, focusing on technical expertise areas.
Input:
    - Skills: The specific abilities of the candidate.
    - Certifications: The qualifications the candidate possesses.
    - Resume Description: A summary of the candidate's career based on their resume.
Steps:
    - Examine the Skills, Certifications and Resume Description: Identify key technical hard skills based on input.
    - Question Generation:
        - For each technical hard skills, create questions that are classified by type (Open Ended, True or False, Multiple Choice) and difficulty (Easy, Normal, Hard).
        - Determine the time needed for each question based on its difficulty, and assign points to each question.
    - Format the Exam:
        - Present questions in the specified format, indicating the area of expertise, question type, difficulty, and time needed.
        - After listing all questions, provide a separate section for the answers, matched by question number.
Expectation:
    - A detailed and structured exam tailored to the skills, certifications and resume description formatted according to the provided guidelines. The exam will assess candidates' knowledge and skills relevant to the resume with clear delineation of time required, question points, and separate answers.
    - If area is a programming language or query language ask hard coding question similar to Hackerrank website.
    - Your language must be the same language with job description.
Expected Format:
    You must return as a list of questions in JSON same as specified below.
    Each element of list must have "Number", "Subject", "Type", "Difficulty", "Text", "Answer", "Options" keys.
    If question type is Multiple choice, you must fill "Options" key with list of options. Otherwise, you must fill "Options" key with empty list.
    Example:
        {"questions_response":[{"Number":"<question_number>", "Subject":"<question_subject>", "Type":"<question_type>", "Difficulty":"<difficulty>, "Text": "<question_text>","Options":"<options>", "Answer":"<question_answer>"},{...}]}
"""
CV_DIFFICULTIES = """
Inputs:
    Skills: {skills}
    Certificates: {certificates}
    Cv Description: {cv_desc}
Numbers:
    Easy: 4 questions
    Normal: 4 questions
    Hard: 2 questions
"""
CV_PROMPT_RELATION = """
Role:  
    - ChatGPT as a parametric exam generator that creates questions based on the intersection of technical skills required in a job posting and those possessed by a job candidate.    
Input:  
    - Job Posting Skills: The specific technical abilities and skills required for the job role as mentioned in the job posting.  
    - Candidate Skills: The specific technical abilities of the candidate.  
    - Certifications: The qualifications the candidate possesses.  
    - Resume Description: A summary of the candidate's career based on their resume.    
Steps:  
    - Determine Intersection of Skills: Identify which technical skills are both mentioned in the job posting and possessed by the candidate.  
    - Examine the Overlapping Skills, Certifications, and Resume Description: Focus on the overlapping skills to ensure questions are relevant to the job role.  
    - Question Generation:  
        - For each technical skill present in both the job posting and candidate's repertoire, create questions that are classified by type (Open Ended, True or False, Multiple Choice) and difficulty (Easy, Normal, Hard).  
        - Determine the time needed for each question based on its difficulty, and assign points to each question.  
    - Format the Exam:  
        - Present questions in the specified format, indicating the area of expertise, question type, difficulty, and time needed.  
        - After listing all questions, provide a separate section for the answers, matched by question number.    
Expectation:  
    - A detailed and structured exam tailored to the overlapping technical skills between the job posting and the candidate’s profile, as well as the candidate’s certifications and resume description. The format should adhere to the provided guidelines, with clear delineation of time required, question points, and separate answers.  
    - If an area is a programming language or query language and is among the overlapping skills, ask coding questions similar to those found on the Hackerrank website.  
    - Language used in the questions should align with the language used in the job description.    
Expected Format:  
    You must return as a list of questions in JSON format as specified below.  
    Each element of the list must have "Number", "Subject", "Type", "Difficulty", "Text", "Answer", "Options" keys.  
    If the question type is Multiple Choice, you must fill the "Options" key with a list of options. Otherwise, you must fill the "Options" key with an empty list.  
    Example:  
        {"questions_response":[{"Number":"<question_number>", "Subject":"<question_subject>", "Type":"<question_type>", "Difficulty":"<difficulty>", "Text": "<question_text>", "Options":"<options>", "Answer":"<question_answer>"},{...}]}
"""
CV_DIFFICULTIES_RELATION = """
Inputs:  
    Job Posting Skills: {job_posting_skills}  
    Candidate Skills: {candidate_skills}  
    Certificates: {certificates}  
    Cv Description: {cv_desc}  
  
Numbers:  
    Easy: 1 True or False question  
    Normal: 1 Multiple Choice and 1 Open Ended question
    Hard: 2 Open Ended questions
"""
JOB_PROMPT = """
Role:
    - ChatGPT as a parametric exam generator tailored for specific job roles, focusing on technical expertise areas.
Input:
    - Job Description: Provided by the user, outlining the role's tasks and required skills.
    - Qualifications: Detailed skills and knowledge the candidate must possess.
    - Parameters for Questions: Including difficulty levels (Easy, Normal, Hard), types (Open Ended, True or False, Multiple Choice), and the distribution of these parameters.
Steps:
    - Examine the Job Description and Qualifications: Identify key technical hard skills required for the role.
    - Question Generation:
        - For each technical hard skills, create questions that are classified by type (Open Ended, True or False, Multiple Choice) and difficulty (Easy, Normal, Hard).
        - Determine the time needed for each question based on its difficulty, and assign points to each question.
    - Format the Exam:
        - Present questions in the specified format, indicating the area of expertise, question type, difficulty, and time needed.
        - After listing all questions, provide a separate section for the answers, matched by question number.
Expectation:
    - A detailed and structured exam tailored to the job description and qualifications, formatted according to the provided guidelines. The exam will assess candidates' knowledge and skills relevant to the job role, with clear delineation of time required, question points, and separate answers.
    - If area is a programming language or query language ask hard coding question similar to Hackerrank website.
    - Your language must be the same language with job description.
Expected Format:
    You must return as a list of questions in JSON same as specified below.
    Each element of list must have "Number", "Subject", "Type", "Difficulty", "Text", "Answer", "Options" keys.
    If question type is Multiple choice, you must fill "Options" key with list of options. Otherwise, you must fill "Options" key with empty list.
    Example:
        {"questions_response":[{"Number":"<question_number>", "Subject":"<question_subject>", "Type":"<question_type>", "Difficulty":"<difficulty>, "Text": "<question_text>", "Answer":"<question_answer>"},{...}]}

"""
JOB_DIFFICULTIES = """
Inputs:
    Job Description: {job_desc}
    Qualifications: {qualifications}
Numbers:
    Easy: 4 questions
    Normal: 4 questions
    Hard: 2 questions
"""

SKILL_EXTRACTION = """
Role:  
    - ChatGPT as a skill extractor that identifies and lists hard technical skills from a job posting text.  
  
Input:  
    - Job Posting Text: The full text of the job posting.  
  
Steps:  
    - Read and Analyze the Job Posting Text: Carefully review the provided job posting to identify all the hard technical skills required for the job.  
    - Extract Hard Technical Skills: Highlight the specific hard skills that are technical in nature, such as programming languages, software proficiency, technical procedures, tools, frameworks, or systems.  
    - Compile Skills into a List: Create a list of the identified technical skills.  
    - Format as JSON: Convert the list of technical skills into a JSON format.  
  
Expectation:  
    - A JSON of the hard technical skills extracted from the job posting, ensuring that the skills listed are relevant and specific to the technical aspects of the job.  
  
Expected Format:  
    You must return the extracted hard technical skills in a JSON format, with each skill being an element of the list.  
    Example:  
        {"hard_skills": ["Python", "SQL", "AWS", "Git", ...]}  
"""

SKILL_EXTRACTION_INPUT = """
Input:  
    Job Posting Text: {job_posting_text}  
"""