#!/bin/python3

import os
from openai import OpenAI
import dotenv

dotenv.load_dotenv()

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_TEXT_MODEL")
MODEL_IMAGE = os.getenv("OPENAI_IMAGE_MODEL")


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


def genai_text(prompt: str) -> str:
    return openai(prompt)


def genai_summarize(text: str) -> str:
    return openai("Please summarize the following: "+text)


def genai_image(prompt: str) -> str:
    return openai_image(prompt)