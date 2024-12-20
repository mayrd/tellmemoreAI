#!/bin/python3

import wikipedia

wikipedia.set_lang("en")


def get_wiki_url(title: str) -> str:
    page = wikipedia.page(title)
    return page.url


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

def fetch_wiki_article_by_id(pageid: str)->str:
    try:
        page = wikipedia.page(pageid=pageid)
        content = page.content
    except wikipedia.exceptions.DisambiguationError as e:
        print("Disambiguation error:", e)
        content = None
    except wikipedia.exceptions.PageError as e:
        print("Page not found:", e)
        content = None

    return content