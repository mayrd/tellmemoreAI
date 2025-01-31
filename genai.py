#!/bin/python3

import os
import sys
import tempfile
import media
import shutil
import utils
import dotenv
import vertexai
import google.auth
import google.genai
import google.generativeai
from openai import OpenAI
from google.cloud import aiplatform
from vertexai.preview.vision_models import ImageGenerationModel

dotenv.load_dotenv()

## openAI methods

def openai(prompt: str) -> str:
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_TEXT_MODEL"),
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error openai({prompt}): {ex}")
        return None


def openai_image(prompt: str) -> str:
    """text to image as jpg file."""
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.images.generate(
            model=os.getenv("OPENAI_IMAGE_MODEL"),
            prompt=prompt,
            size="1792x1024",
            quality="standard",
            n=1,
        )
    except Exception as ex:
        print(f"Error openai_image({prompt}): {ex}")
        return None

    #convert from webp to jpg and then return
    temp_webp = tempfile.NamedTemporaryFile(suffix=".webp", delete=False)
    utils.download_file(response.data[0].url, temp_webp.name)
    temp_jpg = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    media.convert(temp_webp.name, temp_jpg.name)
    return temp_jpg.name


## google (gemini, vertexAI, imagen) methods

# https://ai.google.dev/gemini-api/docs/models/gemini-v2
def gemini(prompt: str) -> str:
    client = google.genai.Client(api_key=os.getenv("GOOGLE_CLOUD_API_KEY"))
    response = client.models.generate_content(model=os.getenv("GEMINI_MODEL"), contents=prompt)
    return response.text


def _get_google_credentials():
    if os.getenv("GOOGLE_SERVICE_ACCOUNT"):
        credentials, project = google.auth.load_credentials_from_file(os.getenv("GOOGLE_SERVICE_ACCOUNT"))
        return credentials
    else:
        credentials, project = google.auth.default()

    if not credentials.valid:
        if credentials.expired:
            credentials.refresh(google.auth.transport.requests.Request())
        else:
            raise ValueError("Credentials are not valid. Check your environment configuration.")
    return credentials


def imagen3(prompt: str) -> str:
    vertexai.init(
        project=os.getenv("GOOGLE_CLOUD_PROJECT_ID"), location=os.getenv("GOOGLE_CLOUD_LOCATION"),
        credentials=_get_google_credentials(),
    )
    generation_model = ImageGenerationModel.from_pretrained(os.getenv("IMAGEN_MODEL"))

    images = generation_model.generate_images(
        prompt=prompt,
        number_of_images=1,
        aspect_ratio="16:9",
        safety_filter_level="block_some",
        #safety_filter_level="block_only_high",
        #person_generation="allow_adult", # not GA
    )

    # store as tmp file as jpg and return
    temp_jpg = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    images[0].save(location=temp_jpg.name, include_generation_parameters=False)
    return temp_jpg.name


### generic methods

def genai_text(prompt: str) -> str:
    """takes text prompt and replies with text. """
    if(os.getenv("GENERATE_TEXT") == "OPENAI"):
        return openai(prompt).strip()
    return gemini(prompt).strip()

def genai_image(prompt: str) -> str:
    """takes takes text and generates image and replies with tempfile in jpg."""
    if(os.getenv("GENERATE_IMAGE") == "OPENAI"):
        return openai_image(prompt)
    return imagen3(prompt)

def genai_image_expanded(prompt: str) -> str:
    return genai_image(expand_image_prompt(prompt))


## prompt helper methods

def genai_summarize(text: str) -> str:
    """takes text and summarizes it. """
    return genai_text("Please summarize the following and only reply with the summary: "+text).strip()

def expand_image_prompt(prompt: str) -> str:
  expanded_prompt = """
Write a prompt for a text-to-image model following the style of the examples of prompts, and then I will give you a prompt that I want you to rewrite.
Examples of prompts:
A close-up of a sleek Siamese cat perched regally, in front of a deep purple background, in a high-resolution photograph with fine details and color grading.
Flat vector illustration of "Breathe deep" hand-lettering with floral and leaf decorations. Bright colors, simple lines, and a cute, minimalist design on a white background.
Long exposure photograph of rocks and sea, long shot of cloudy skies, golden hour at the rocky shore with reflections in the water. High resolution.
Three women stand together laughing, with one woman slightly out of focus in the foreground. The sun is setting behind the women, creating a lens flare and a warm glow that highlights their hair and creates a bokeh effect in the background. The photography style is candid and captures a genuine moment of connection and happiness between friends. The warm light of golden hour lends a nostalgic and intimate feel to the image.
A group of five friends are standing together outdoors with tall gray mountains in the background. One woman is wearing a black and white striped top and is laughing with her hand on her mouth. The man next to her is wearing a blue and green plaid shirt, khaki shorts, and a camera around his neck, he is laughing and has his arm around another man who is bent over laughing wearing a gray shirt and black pants with a camera around his neck. Behind them, a blonde woman with sunglasses on her head and wearing a beige top and red backpack is laughing and pushing the man in the gray shirt.
An elderly woman with gray hair is sitting on a park bench next to a medium-sized brown and white dog, with the sun setting behind them, creating a warm orange glow and lens flare. She is wearing a straw sun hat and a pink patterned jacket and has a peaceful expression as she looks off into the distance.
A woman with blonde hair wearing sunglasses stands amidst a dazzling display of golden bokeh lights. Strands of lights and crystals partially obscure her face, and her sunglasses reflect the lights. The light is low and warm creating a festive atmosphere and the bright reflections in her glasses and the bokeh. This is a lifestyle portrait with elements of fashion photography.
A closeup of an intricate, dew-covered flower in the rain. The focus is on the delicate petals and water droplets, capturing their soft pastel colors against a dark blue background. Shot from eye level using natural light to highlight the floral texture and dew's glistening effect. This image conveys the serene beauty found within nature's miniature worlds in the style of realist details
A closeup of a pair of worn hands, wrinkled and weathered, gently cupping a freshly baked loaf of bread. The focus is on the contrast between the rough hands and the soft dough, with flour dusting the scene. Warm light creates a sense of nourishment and tradition in the style of realistic details
A Dalmatian dog in front of a pink background in a full body dynamic pose shot with high resolution photography and fine details isolated on a plain stock photo with color grading in the style of a hyper realistic style
A massive spaceship floating above an industrial city, with the lights of thousands of buildings glowing in the dusk. The atmosphere is dark and mysterious, in the cyberpunk style, and cinematic
An architectural photograph of an interior space made from interwoven, organic forms and structures inspired in the style of coral reefs and patterned textures. The scene is bathed in the warm glow of natural light, creating intricate shadows that accentuate the fluidity and harmony between the different elements within the design
Prompt to rewrite:
'{PROMPT}'
Don't generate images, just reply with the prompt.
"""
  return genai_text(expanded_prompt.replace("{PROMPT}", prompt))


if __name__ == "__main__":
    PROMPT=(
        expand_image_prompt("dog in a red dress.")
    )
    file = imagen3(PROMPT)
    shutil.move(file, "generated.jpg")
