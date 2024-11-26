#!/usr/bin/env python3

__version__ = "0.1.0"

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from anthropic import Anthropic
import json
import time
import os
import json
from bs4 import BeautifulSoup
import re
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
memoize_file_path = json_file = os.path.join(current_dir, "memoize.json")
timestamp = int(time.time()) 

class DataScraperWithLLM:
    def __init__(self, api_key):
        """initialize with anthropic API key"""
        self.anthropic = Anthropic(api_key=api_key)
        self.driver = None #to be setup in another function
        
    def setup_selenium(self):
        """selenium driver using chrome."""
        opt = webdriver.ChromeOptions()
        opt.add_argument('--headless')  # run in headless mode
        self.driver = webdriver.Chrome(options=opt)
        
    def get_source_urls(self, question, memoize_for_debug=False):
        """ask Claude for relevant source URLs to answer the question at hand"""
        
        #memoize the answer to reduce api costs if debugging
        if memoize_for_debug:
            # if memoize json file exists read from it
            try:
                
                if not os.path.exists(memoize_file_path): 
                    open(memoize_file_path, 'w') #create memoize file to be wriiten to
                else:
                    with open(memoize_file_path, 'r') as f:
                        try:
                            mem_data = json.load(f)
                            print("taking from memoized data, no api call for initial question")
                            return mem_data[question]
                        except:
                            print("calling api, then memoizing that data...")
            
            except Exception as e:
                print(e)
                raise RuntimeError("unexpected failure") from e

                    
        
        initial_prompt = f"""Given the following question, provide ONLY a JSON list of specific URLs (maximum 6) 
        that would contain the information needed to answer it. Do not answer the question itself, only provide sources.
        
        Question: {question}
        
        Respond with only a JSON array of URLs, nothing else.
        """
        
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=300,
            temperature=0,
            messages=[{
                "role": "user",
                "content": initial_prompt
            }]
        )
        
        try:
            urls = json.loads(response.content[0].text)

            #add new data to the memoize file
            if memoize_for_debug:
                #read existing data in memoize
                try: 
                    with open(memoize_file_path, 'r') as f:
                        existing_data = json.load(f)
                        existing_data[question] = urls
                except json.JSONDecodeError:
                    existing_data = {}
                    existing_data[question] = urls
                
                with open(memoize_file_path, 'w') as f:
                    json.dump(existing_data, f, indent=4)

            return urls
        except json.JSONDecodeError as je:
            print(f"Error: Claude didn't return valid JSON; Using empty URL list | {je}")
            return []

    def scrape_url(self, url):
        """scrape content from a given URL using Selenium."""
        try:
            self.driver.get(url)
            # wait for body to load
            WebDriverWait(self.driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            #if not found then use google
            logic_1 = "404" in self.driver.title.lower()
            logic_2 = "not found" in self.driver.title.lower()
            logic_3 = self.driver.current_url != url
            if logic_1 or logic_2 or logic_3: 
                self.driver.get(f"https://www.google.com/search?q={url} games")
                first_result = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#search .g:first-child a:first-child")))
                self.driver.get(first_result.get_attribute('href'))
                WebDriverWait(self.driver, 12).until(EC.presence_of_element_located((By.TAG_NAME, "body")))


            print(f"Scraping {self.driver.current_url}")

            # get page source and parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
                
            # Get text content
            text = soup.get_text(separator=' ', strip=True)
            
            # Basic cleaning
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
            return ""

    def get_answer(self, question, context):
        """Get answer from Claude using the scraped context."""
        prompt = f"""Using ONLY the following context, answer this question: {question}
        
        Context:
        {context}
        
        Provide a clear, concise answer based solely on the context provided."""

        message_obj = [{
                "role": "user",
                "content": prompt
            }]

        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            temperature=0.5,
            messages=message_obj
        )
        
        return (response.content, message_obj)
    
    def continue_answer(self, prev_message_obj, last_answer):
        """ask the LLM to continue their answer. If it is cut off intentionally or not"""
        
        prompt = f"""please continue your answer"""

        message_obj = prev_message_obj
        message_obj.append(
            {"role": "assistant", "content": last_answer}
        )
        message_obj.append(
            {"role": "user", "content": prompt}
        )

        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            temperature=0.5,
            messages=message_obj
        )
        
        return (response.content, message_obj)

    def main_question_answer(self, question):
        """now answer the main question"""
        print(f"Researching question: {question}")
        
        urls = self.get_source_urls(question, memoize_for_debug=True) # get source URLs from Claude
        print(f"Found {len(urls)} potential sources")
        
        self.setup_selenium()  # Set up Selenium
        
        # scrape content from each URL
        all_content = []
        for url in urls:
            content = self.scrape_url(url)
            all_content.append(content)
        
        # save scraped content to file
        #with open('scraped_data.txt', 'w', encoding='utf-8') as f:
        #    for i, content in enumerate(all_content):
        #        f.write(f"=== Source {i+1} ===\n")
        #        f.write(content + "\n\n")
        
        # get final answer from Claude
        context = "\n".join(all_content)
        (answer, prev_message_obj) = self.get_answer(question, context)
        
        self.driver.quit() # clean up
        
        return (answer, prev_message_obj)

def main():
    
    all_outputs = []

    api_key = os.environ["API_KEY_ANTHROPIC"] # replace with your Anthropic API key in env vars
    
    scraper = DataScraperWithLLM(api_key)
    
    question = "what were the top 30 games of 2024, both indie and mainstream games. create a bullet-point list of them with sub-bullets answering the following questions: (1) what is the genre of the gameplay, the genre of the story, and the quickly explain the art direction (2) What was Youtube content creator's response to the game vs traditional/blog media's response to the game (3) Was there any culture-war discussion around the game or not (political & non-political discussions) (if true give a brief explanation, else just write false) (4) what was the meta-critique score of the game (5) how good is the story (out of 10) and give a brief explanation on why (6) is this game innovative graphically (true or false) (7) is this game innovative in the moment-to-moment game-play (true or false) (8) what is the average time-to-beat the game (9) is is available on pc (true or false) (10) if there is a steamdb entry for the game, what is the trend in player base (explain if this trend is normal or abnormal) (11) any game award nominations?; return 5 at a time and i will respond to each answer with 'next' for you to generate the next 5 responses"
    question = input("\n \n type in your question (if you type a number, this will lookup the index of the example questions (see examples.json) to use):  "); # input the question; see examples file
    try:
        question = int(question) #if it is a number this try block wont fail due to this
        print(f"\n using example input at index {question}")
        try:
            with open('examples.json', 'r') as f:
                example_data = json.load(f)
                question = example_data['example_inputs'][question]
        except Exception:
            print("Quesiton index does not exist OR examples.json does not exist, aborting.")
            sys.exit(1)
    except Exception as e:
        print(f"Your question or index for example question was invalid: {e}")
    finally:
        print(f"using the following question: {question}")
    
    (answer, prev_message_obj) = scraper.main_question_answer(question) # Get researched answer

    print("\nInitial Answer:")
    print(answer)
    all_outputs.append(answer)

    continue_answer_bool = True
    while continue_answer_bool:
        continue_input = input("continue answer? (Y/N)")
        if continue_input == "Y" or continue_input == "y":
            print("\n getting next answer ... \n")
            (answer, prev_message_obj) = scraper.continue_answer(prev_message_obj, answer)
            print(answer)
            all_outputs.append(answer)
        else:
            print("Finished outputting. Thanks!")
            continue_answer_bool = False
            break 

    
    with open(f'output_{timestamp}.txt', 'w', encoding='utf-8') as f:
        for i, content in enumerate(all_outputs):
            f.write(f"=== ANSWER {i+1} ===\n")
            f.write(content[0].text + "\n\n")


if __name__ == "__main__":
    main()
