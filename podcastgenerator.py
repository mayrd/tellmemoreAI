#!/bin/python3
# Runs notebooklm automation to generate the podcast wav file

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import shutil
import wiki
import utils
import dotenv

dotenv.load_dotenv()

PROMPT_PODCAST = (
    "The title of the podcast is \"Tell me More - Stories Told as Podcast\" - welcome people and say the name of the podcast. Do not mention the wikipedia article. "
    "Make a podcast describing the event, how it happened, what was done and how it turned out. make it adventurous and catchy. "
    "In the middle of the podcast, tell people to hit the subscribe button, to not miss any another podcasts on \"Tell me More\". "
    "Make the podcast 30 minutes long."
)
LOCAL_DOWNLOAD = os.getenv("LOCAL_DOWNLOAD_FOLDER")


def get_chrome_driver():
    opts = webdriver.ChromeOptions()
    opts.add_argument(f"user-data-dir=" + os.getenv("CHROME_PROFILE_FOLDER"))
    opts.add_argument("start-maximized")
    if os.getenv("SELENIUM_HEADLESS") == "1":
        opts.add_argument("headless")

    return webdriver.Chrome(options = opts)

def get_firefox_driver():
    opts = webdriver.FirefoxOptions()
    opts.add_argument('-profile')
    opts.add_argument(os.getenv("FIREFOX_PROFILE_FOLDER"))
    if os.getenv("SELENIUM_HEADLESS") == "1":
        opts.add_argument("-headless")
        opts.headless = True
        
    return webdriver.Firefox(options=opts)


def gen_podcast(URL:str) ->str:
    # open browser
    # navigate to https://notebooklm.google.com
    # create a new notebook
    # add {wiki_article} to the sources
    # open overview menu
    # customize prompt for podcast generation
    # generate podcast
    # wait until podcast is generated
    # download podcast
    if os.getenv("SELENIUM_BROWSER") == "firefox":
        driver = get_firefox_driver()
    else:
        driver = get_chrome_driver()
    try:
        print("(1) Open Notebooklm")
        step1_open_notebooklm(driver)
        print("(2) New Notebook")
        step2_new_notebook(driver)
        print("(3) Add Website")
        step3_add_website(driver, URL)
        print("(4) Wait for processing")
        step4_wait_source_processing(driver)
        print("(5) Customize")
        step5_customize_podcast(driver)
        print("(6) Wait Podcast")
        step6_wait_podcast(driver)
        print("(7) Download Podcast")
        step7_download_podcast(driver)
        print("(8) Downloading")
        
        for i in range(1,301):
            time.sleep(1)
            for file in os.listdir(LOCAL_DOWNLOAD):
                if file.endswith(".wav"):
                    return file

        print("Time over, but file not found!")
    except:
        print("Error")
    finally:
        print("(X) Teardown")
        time.sleep(2)
        driver.close()
        time.sleep(2)
        driver.switch_to.window(driver.window_handles[0])
        driver.quit()
    
    return None


def step1_open_notebooklm(driver):
    driver.switch_to.new_window()
    driver.get("https://notebooklm.google.com")
    time.sleep(2)
    assert "NotebookLM" in driver.title


def step2_new_notebook(driver):
    driver.find_element(By.CLASS_NAME, "create-new-label").click()
    time.sleep(2)


def step3_add_website(driver, URL):
    driver.find_element(By.ID, "mat-mdc-chip-2").click()
    time.sleep(2)
    elem_url = driver.find_element(By.ID, "mat-input-0")
    elem_url.click()
    time.sleep(2)
    elem_url.send_keys(URL)
    time.sleep(2)
    elem_url.send_keys(Keys.RETURN)


def step4_wait_source_processing(driver):
    wait = WebDriverWait(driver, 360)
    wait.until(EC.visibility_of_element_located((By.CLASS_NAME, 'customize-button')))
    time.sleep(25)


def step5_customize_podcast(driver):
    
    elem_customize = driver.find_element(By.CLASS_NAME, "customize-button")
    elem_customize.click()

    time.sleep(2)
    elem_prompt = driver.find_element(By.CSS_SELECTOR, "textarea.mat-mdc-form-field-textarea-control")
    elem_prompt.send_keys(PROMPT_PODCAST)
    time.sleep(2)

    btns = driver.find_elements(By.CSS_SELECTOR, "button.generate-button.mat-mdc-unelevated-button")
    for btn in btns:
        try:
            btn.click()
        except:
            pass


def step6_wait_podcast(driver):
    wait = WebDriverWait(driver, 360)
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'button.playback-control-button')))


def step7_download_podcast(driver):
    driver.find_element(By.CSS_SELECTOR, "button.mat-mdc-menu-trigger.audio-controls-button").click()
    time.sleep(2)
    driver.find_element(By.CSS_SELECTOR,"a.mat-mdc-menu-item.mat-focus-indicator").click()


def process():
    # find first to gen_podcast
    # when done, store database.json and then restart (do not continue)
    db = utils.fromFile("database.json")
    for item in db["list"]:
        print(f"checking {item}")
        if "folder" in item:
            continue

        #found one..
        print("Generate podcast for " + item["title"])
        if "url" not in item:
            try:
                url = wiki.get_wiki_url(item["title"])
            except:
                print("could not find wiki url, try guessing...")
                url = wiki.guess_wiki_url(item["title"])
        else:
            url = item["url"]
        wavefile = gen_podcast(url)
        if not wavefile:
            print("hmm, wavefile not generated, continue with something else")
            continue

        item["folder"] = utils.build_folder_name(item["title"])
        utils.create_folder(item['folder'])
        shutil.move(os.path.join(os.getenv("LOCAL_DOWNLOAD_FOLDER"), wavefile), os.path.join(item["folder"], "podcast.wav"))
        
        md = dict()
        md["category"] = item["category"]
        md["wiki_title"] = item["title"]
        md["pageid"] = wiki.get_page_id(url)

        utils.toFile(md, os.path.join(item["folder"], "metadata.json"))
        utils.toFile(db, "database.json")
        print(f"Done with {item}")
        return


if __name__ == "__main__":
    while(True):
        process()
        #time.sleep(2*60)