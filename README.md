# Data-Scraper-For-LLM-Prompts (version 0.1.0)
* Scrapes the necessary webpages to fulfill a prompt for an LLM without access to the internet (or just generally out of date)
* assumes Anthropic API specficially, in version 0.1.0 at least
* simple script, after download you can run with: `python main.py` or `python3 main.py` 
    * There will be many prompts for the user, this is due to the chat-bot like structure of the LLM API
* examples.json has some example prompts you can use

## Dependencies
```json
{
    'selenium': 'selenium>=4.0.0',
    'anthropic': 'anthropic>=0.7.0',
    'beautifulsoup4': 'beautifulsoup4>=4.9.0'
}
```

## Quick Documentation

##### Quick Example (if not using the script standalone, but rather importing functionality)
```python
api_key = os.environ["API_KEY_ANTHROPIC"]
scraper = DataScraperWithLLM(api_key)
answer, message_obj = scraper.main_question_answer("What were the top games of 2024?")
```

### DataScraperWithLLM

Main class that handles web scraping and LLM interactions.

### Methods

`__init__(api_key: str)`
* Initializes scraper with Anthropic API key.

`setup_selenium()`
* Configures headless Chrome WebDriver for scraping.

`get_source_urls(question: str, memoize_for_debug: bool = False) -> list[str]`
* Gets relevant URLs from Claude to answer the given question. Supports memoization for debugging.

`scrape_url(url: str) -> str`
* Scrapes content from given URL. Includes fallback to Google search for 404 errors.

`get_answer(question: str, context: str) -> tuple[anthropic.Message, list[dict]]`
* Gets answer from Claude using scraped context. Returns response and message history.

`continue_answer(prev_message_obj: list[dict], last_answer: str) -> tuple[anthropic.Message, list[dict]]`
* Continues previous answer with Claude. Useful for handling truncated or incomplete responses.

`main_question_answer(question: str) -> tuple[anthropic.Message, list[dict]]`
* Main workflow: gets URLs, scrapes content, and generates answer.

## Roadmap For Future Updates
* handling selenium timeouts
* recursive url traversing to get more details
* abstract out to other LLM APIs (e.g. OpenAI)