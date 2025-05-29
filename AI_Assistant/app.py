import random
from flask import Flask, render_template, request
import google.generativeai as genai
import os # For environment variables
from dotenv import load_dotenv 

load_dotenv() 

app = Flask(__name__)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# Prompt templates per function
prompt_templates = {
    "question": [
        "Answer this factual question concisely: {}",
        "Provide a detailed explanation for: {}",
        "List three interesting facts about: {}"
    ],
    "summary": [
        "Summarize the following text briefly:\n{}",
        "What are the main points of this text?\n{}",
        "Provide a concise overview of this document:\n{}"
    ],
    "creative": [
        "Write a short story based on this idea:\n{}",
        "Create a poem inspired by this:\n{}",
        "Generate a creative concept or idea related to:\n{}"
    ]
}

def generate_response_gemini(prompt_text):
    """Generates a response using the Gemini API."""
    try:
        # For text-only input, use "gemini-pro"
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Configure generation parameters
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            max_output_tokens=250 # Gemini uses max_output_tokens
        )

        # Generate content using the model
        
        response = model.generate_content(
            prompt_text,
            generation_config=generation_config
        )
        
        # Check for safety ratings or blocked prompts if necessary
        if response.prompt_feedback and response.prompt_feedback.block_reason:
            return f"Error: Prompt was blocked. Reason: {response.prompt_feedback.block_reason.name}"
        if not response.candidates or not response.candidates[0].content.parts:
             return "Error: No content generated. The prompt might have been blocked or the model produced no output."

        return response.text.strip()
    except Exception as e:
        print(f"Error during Gemini API call: {e}")
        return f"An error occurred while generating the response: {str(e)}"

def log_feedback(prompt, response, feedback):
    with open("feedback.txt", "a") as f:
        f.write(f"Prompt: {prompt}\nResponse: {response}\nFeedback: {feedback}\n\n")

def analyze_feedback():
    total = 0
    yes = 0
    no = 0
    try:
        with open("feedback.txt", "r") as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith("Feedback:"):
                    total += 1
                    fb = line.strip().split(": ")[1]
                    if fb.lower() == "yes":
                        yes += 1
                    elif fb.lower() == "no":
                        no += 1
    except FileNotFoundError:
        return total, yes, no

    return total, yes, no

@app.route('/', methods=['GET', 'POST'])
def index():
    result = ""
    feedback = ""
    prompt_used = ""
    if request.method == 'POST':
        function = request.form['function']
        user_input = request.form['user_input']
        feedback = request.form.get("feedback", "")

        # Select a random prompt template and format with user input
        prompt_template = random.choice(prompt_templates.get(function, ["{}"]))
        prompt_used = prompt_template.format(user_input)

        result = generate_response_gemini(prompt_used)

        # Log feedback only if user submitted it (avoid empty feedback logs)
        if feedback:
            log_feedback(prompt_used, result, feedback)

    return render_template('index.html', result=result, prompt=prompt_used)

@app.route('/feedback-summary')
def feedback_summary():
    total, yes, no = analyze_feedback()
    helpfulness = (yes / total * 100) if total > 0 else 0
    return (
        f"<h1>Feedback Summary</h1>"
        f"<p>Total responses: {total}</p>"
        f"<p>Helpful (Yes): {yes}</p>"
        f"<p>Not helpful (No): {no}</p>"
        f"<p>Helpfulness rate: {helpfulness:.2f}%</p>"
    )

if __name__ == '__main__':
    app.run(debug=True)
