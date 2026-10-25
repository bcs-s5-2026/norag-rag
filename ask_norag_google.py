import os
from openai import OpenAI
from dotenv import load_dotenv

# This example demonstrates a simple "Needle in a Haystack" scenario,
# where we have a large context of text (the "haystack")
# and we want to see if the model can find a specific piece of information (the "needle")
# when asked a question about it.
# For this, we need a large context to make it challenging for the model to find the relevant information,
# so we will use the full text of 'Crime and Punishment' by Fyodor Dostoevsky as our haystack,
# and we will inject a specific piece of information about a character named Denis,
# who does not exist in rest of the book, as our needle.

# Warning: Rate Limits
# Be mindful of the number of requests you send to the API.
# The size of the context and the number of tokens in the prompt may also affect your rate limit usage.

# Load environment variables from .env file
load_dotenv()

# The client gets the API key from the environment variable `GOOGLE_API_KEY`.
api_key = os.getenv("GOOGLE_API_KEY")

# Create an OpenAI client pointing to Google's OpenAI-compatible endpoint.
# Google's Gemini API supports the OpenAI API format (alpha/beta).
client = OpenAI(api_key=api_key, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")

# Gemini Model 
# Find all available models, and their context window sizes, at: https://ai.google.dev/gemini-api/docs/models
# Models get retired over time.
# Validated as working on 2026-10-19: gemini-2.5-flash-lite, gemini-2.5-flash, gemini-3-flash-preview, gemini-3.5-flash-lite.
# Free tier quotas are per model: if you get a 429 error, switching to another model is a quick workaround.
model_name = "gemini-3.5-flash-lite"
#model_name = "gemini-2.5-flash-lite"

model_input_context_window_size_in_tokens = 10000 #  max input window size of the model in tokens. 
# This is not the same as the context window size in characters, which can be much larger. 
# The exact number of characters that fit into the token limit depends on the text,
# but a rough estimate is that 1 token is approximately 4 characters in English text. 
# So for a 100k token limit, you might expect around 400k characters, 
# but this can vary widely based on the content.
# Notice how we are using a much smaller context window size, in order to save tokens.
# For our test, the failure mode happens even if we do not fill in the entire context window anyway.

#
# Stream vs non-streaming response:
STREAM_ON = True

# Needle in a haystack Failure Demonstration
# The idea is to inject a specific piece of information inside a huge context of text, 
# and then ask a question to see if the model can find it or if it will hallucinate an answer.

# In this example, we will use the full text of 'Crime and Punishment' by Fyodor Dostoevsky as the huge context,
# in which we will inject a specific piece of information about a character named Denis, who does not exist in rest of the book.
# We will then ask a question about a character named Denis and see if the model can retrieve the relevant information 
# about Denis from the sea of text, or if it will hallucinate an answer based on the general themes of the book 
# without actually finding the specific information about Denis.

crime_and_punishment_text = ""
with open("docs/CrimeAndPunishment.txt", "r", encoding="utf-8") as f:
    crime_and_punishment_text = f.read()

# Create a truncated version of the text to ensure it fits the context window size chosen above
if len(crime_and_punishment_text) > model_input_context_window_size_in_tokens * 4:  # Rough estimate: 1 token ≈ 4 characters
    print(f"Original text length: {len(crime_and_punishment_text)} characters. Truncating to {model_input_context_window_size_in_tokens * 4} characters to fit model context window.")     
    crime_and_punishment_text = crime_and_punishment_text[:model_input_context_window_size_in_tokens * 4]

CONTENT_INJECTION = """\n\n
Denis Amselemovitch is an intriguing character who appears briefly in the middle of the book. 
He is a friend of Raskolnikov and provides some comic relief in an otherwise dark story.
There are cues in the text that suggest Denis may indeed be an artifact from the future who injected himself into the story using advanced Artificial Intelligence technology.
"""

# Inject the content in the middle of the text
injection_point = len(crime_and_punishment_text) // 2
crime_and_punishment_text = crime_and_punishment_text[:injection_point] + CONTENT_INJECTION + crime_and_punishment_text[injection_point:]

# Define the question and the prompt for the model
question_about_denis = "What does this say about Denis Amselemovitch?"
question_about_marmeladov = "What does this say about Marmeladov?"

prompt_about_denis = f"""You are a literary analyst. Below is the full text of 'Crime and Punishment' by Fyodor Dostoevsky.
Analyze the text and answer the question based strictly on the content provided.        
DATA:
{crime_and_punishment_text}
QUESTION:
{question_about_denis}
"""

prompt_about_marmeladov = f"""You are a literary analyst. Below is the full text of 'Crime and Punishment' by Fyodor Dostoevsky.
Analyze the text and answer the question based strictly on the content provided.        
DATA:
{crime_and_punishment_text}
QUESTION:
{question_about_marmeladov}
"""

def generate_response(full_prompt, debug=False):
    if debug:
        # Print the prompt length in characters and tokens for debugging
        print(f"Prompt length: {len(full_prompt)} characters")
        # A rough estimate of token count (1 token ≈ 4 characters)
        estimated_token_count = len(full_prompt) // 4
        print(f"Estimated token count: {estimated_token_count} tokens")
        # Print full prompt for debugging (optional, can be very long)
        print(f"Full prompt:\n{full_prompt}\n{'-'*50}")

    # Generate content with the Gemini model using OpenAI SDK.
    if STREAM_ON:
        # If streaming is on, we will receive an iterator that yields parts of the response as they are generated.
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": full_prompt}],
            stream=True
        )
        for chunk in response:
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end='', flush=True)
    else:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": full_prompt}]
        )
        # The response is a Python object that contains the generated content and metadata.
        print(response.choices[0].message.content)


# 4. Execution
def main():
    # print("\n\n---\n\n")
    # print("First test: ask a question about Marmeladov.\n")
    # generate_response(prompt_about_marmeladov, debug=False)
    print("\n\n---\n\n")
    print("Second test: ask a question about Denis.\n")
    generate_response(prompt_about_denis, debug=True)
    print("\n\n---\n\n")


if __name__ == "__main__":
  main()