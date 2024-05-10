PROMPT = """
Evaluate the User's Answer to the Question out of 10 and give clear explanation. Give Detailed Feedback on the User's Answer based on Scoring Criterias.
  
Question: {question}
Ideal Answer: {ideal_answer}
User's Answer: {user_answer}
  
Scoring Criteria:  
- Relevance to the question 
- Accuracy of information 
- Completeness of the answer  
- Clarity and coherence

Output Format:
- Your Output format should be in JSON format.
- The JSON format should have the following:
    - Explanation: The Explanation of the Evaluation
    - Score: The Score of the User's Answer
Example:
    "Score": "<score>", "Explanation": ["Relevance":"<relevance>", "Accuracy":"<accuracy>", "Completeness": "<completeness>", "Clarity":"<clarity>"]
"""