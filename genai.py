#!/bin/python3

import os
import google.genai
import google.generativeai
from openai import OpenAI
import dotenv

dotenv.load_dotenv()

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_TEXT_MODEL")
MODEL_IMAGE = os.getenv("OPENAI_IMAGE_MODEL")

GOOGLE_CLOUD_API_KEY = os.getenv("GOOGLE_CLOUD_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")


def openai(prompt: str) -> str:
    try:
        client = OpenAI(api_key=OPENAI_KEY)
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"


def openai_image(prompt: str) -> str:
    client = OpenAI(api_key=OPENAI_KEY)
    response = client.images.generate(
        model=MODEL_IMAGE,
        prompt=prompt,
        size="1792x1024",
        quality="standard",
        n=1,
    )
    return response.data[0].url


# https://ai.google.dev/gemini-api/docs/models/gemini-v2
def gemini(prompt: str) -> str:
    client = google.genai.Client(api_key=GOOGLE_CLOUD_API_KEY)
    response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    return response.text

#https://ai.google.dev/gemini-api/docs/imagen?hl=en
def imagen(prompt: str) -> str:
    #TODO does not work
    google.generativeai.configure(api_key=GOOGLE_CLOUD_API_KEY)
    client = google.generativeai.ImageGenerationModel("imagen-3.0-generate-001")
    #print(google.generativeai.models.list())
    response = client.generate_images(
        prompt=prompt,
        number_of_images=1,
        safety_filter_level="block_only_high",
        person_generation="allow_all",
        aspect_ratio="3:4",
    )
    return response
    #response.generated_images[0].image.show()


def genai_text(prompt: str) -> str:
    if(os.getenv("GENERATE_TEXT") == "OPENAI"):
        return openai(prompt)
    return gemini(prompt)


def genai_summarize(text: str) -> str:
    return openai("Please summarize the following: "+text)


def genai_image(prompt: str) -> str:
    if(os.getenv("GENERATE_IMAGE") == "OPENAI"):
        return openai_image(prompt)
    return imagen(prompt)


if __name__ == "__main__":
    print(imagen("Write a cool welcome message for a geek"))
