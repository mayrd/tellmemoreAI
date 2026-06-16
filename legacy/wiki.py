#!/bin/python3

import wikipedia
import requests
import urllib

wikipedia.set_lang("en")

def get_page_id(url):
    try:
        parsed_url = urllib.parse.urlparse(url)
        path = parsed_url.path
        title = path.split('/wiki/')[-1]
        title = urllib.parse.unquote(title)
        
        api_url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "format": "json",
            "titles": title,
            "redirects": 1
        }
        response = requests.get(api_url, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        data = response.json()
        pages = data.get("query", {}).get("pages", {})

        if pages:
          page_id = list(pages.values())[0].get("pageid")
          if page_id:
            return page_id
          else:
            print("No page found for the given title.")
            return None
        else:
            print("No pages found in the API response.")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {e}")
        return None
    except IndexError:
        print("Invalid Wikipedia URL format.")
        return None
    except KeyError:
        print("Unexpected API response format.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def get_page_by_title(title: str) -> wikipedia.page:
    return wikipedia.page(title)

def get_wiki_url(title: str) -> str:
    page = wikipedia.page(title)
    return page.url


def guess_wiki_url(title: str) -> str:
    return "https://en.wikipedia.org/wiki/" + title.replace(" ","_")


def get_wiki_summary(query: str) -> str:
    return wikipedia.summary(query)


def fetch_wiki_article(title: str) -> str:
    try:
        page = wikipedia.page(title)
        content = page.content
    except wikipedia.exceptions.DisambiguationError as e:
        print("Disambiguation error:", e)
        content = None
    except wikipedia.exceptions.PageError as e:
        print("Page not found:", e)
        content = None

    return content

def get_page_by_id(pageid: str) -> wikipedia.page:
    try:
        page = wikipedia.page(pageid=pageid)
        return page
    except wikipedia.exceptions.DisambiguationError as e:
        print("Disambiguation error:", e)
    except wikipedia.exceptions.PageError as e:
        print("Page not found:", e)
    return None

def fetch_wiki_article_by_id(pageid: str)->str:
    try:
        return get_page_by_id(pageid).content
    except Exception as e:
        print("Error:", e)

    return None