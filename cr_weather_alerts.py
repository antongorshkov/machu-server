import feedparser
import requests
from bs4 import BeautifulSoup

# Replace with your DeepL API key if using translation
DEEPL_API_KEY = "7cdd98b5-31e3-46a0-91ca-923a04eb389c:fx"

# Fetch the RSS feed
def fetch_latest_feed(feed_url):
    feed = feedparser.parse(feed_url)
    if feed.entries:
        latest_entry = feed.entries[0]
        return latest_entry
    else:
        raise Exception("No entries found in the feed.")

# Fetch the content from the entry's URL
def fetch_entry_content(entry_url):
    response = requests.get(entry_url)
    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"Failed to fetch content from {entry_url}")

# Extract description from the HTML/XML content
def extract_description(content):
    soup = BeautifulSoup(content, features="xml")
    # Attempt different ways to find the description
    description = None
    
    # Check for meta description tag
    meta_description = soup.find('meta', attrs={'name': 'description'})
    if meta_description and 'content' in meta_description.attrs:
        description = meta_description['content']
    
    # Fallback: Check for any <description> or similar tag in XML
    if not description:
        description_tag = soup.find('description')
        if description_tag:
            description = description_tag.get_text(strip=True)
    
    if not description:
        raise Exception("No description found in the page.")
    
    return description

# Translate the description using DeepL
def translate_description(description, target_language="EN"):
    url = "https://api-free.deepl.com/v2/translate"
    params = {
        "auth_key": DEEPL_API_KEY,
        "text": description,
        "target_lang": target_language
    }
    response = requests.post(url, data=params)
    if response.status_code == 200:
        return response.json()["translations"][0]["text"]
    else:
        raise Exception(f"Translation failed: {response.status_code} {response.text}")

# Main function to execute the logic
def main():
    feed_url = "https://cap-sources.s3.amazonaws.com/cr-imn-es/rss.xml"
    try:
        # Step 1: Fetch the latest entry from the feed
        latest_entry = fetch_latest_feed(feed_url)
        entry_url = latest_entry.link
        
        # Step 2: Fetch the HTML/XML content of the entry
        content = fetch_entry_content(entry_url)
        
        # Step 3: Extract the description
        description = extract_description(content)
        
        # Step 4: Translate the description to English (optional)
        print("Original Description (Spanish):", description)
        translated_description = translate_description(description)
        print("Translated Description (English):", translated_description)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
