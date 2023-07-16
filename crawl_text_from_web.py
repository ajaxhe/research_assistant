import configparser
import os
import requests
import re
import time
import urllib.request

from bs4 import BeautifulSoup
from collections import deque
from html.parser import HTMLParser
from urllib.parse import urlparse


config = configparser.ConfigParser()
config.read('default.cfg')
d_conf = config['DEFAULT']


# Regex pattern to match a URL
http_url_pattern = r'^http[s]*://.+'
date_format_str= '%Y-%m-%d'

full_urls = {
    'qinglian': [
        'https://mp.weixin.qq.com/s/PzgcLsHwOvNhrvAtWnYsRg',
        'https://mp.weixin.qq.com/s/u9cshXsHqvLauM60IQ5DIg',
        'https://mp.weixin.qq.com/s/5kilMZeGruy8hr9gtCxekQ',
        'https://mp.weixin.qq.com/s/0oIwJuojcPtqbCTOaLmCvQ',
        'https://mp.weixin.qq.com/s/qYCJdUwHjue51EhKT1fXjg',
        'https://mp.weixin.qq.com/s/A5Pm1fT4hKsFjss8U60NIg',
        'https://mp.weixin.qq.com/s/iOWrSQZJfCb_shMJGzYwjQ',
        'https://mp.weixin.qq.com/s/HNWOH0MrzqUqxmLDacKaag',
        'https://mp.weixin.qq.com/s/UnYY9S8taho9k12NHx8XFA',
        'https://mp.weixin.qq.com/s/njz8Mw9hPvqeq4P6LmPAsA',
        'https://mp.weixin.qq.com/s/347ft16626JsamZqhCg5QA',
        'https://mp.weixin.qq.com/s/O3Fz9QcSf3KGH_gItRJogg',
    ],
}


# Create a class to parse the HTML and get the hyperlinks
class HyperlinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        # Create a list to store the hyperlinks
        self.hyperlinks = []

    # Override the HTMLParser's handle_starttag method to get the hyperlinks
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        # If the tag is an anchor tag and it has an href attribute, add the href attribute to the list of hyperlinks
        if tag == "a" and "href" in attrs:
            self.hyperlinks.append(attrs["href"])

# Function to get the hyperlinks from a URL
def get_hyperlinks(url):
    
    # Try to open the URL and read the HTML
    try:
        # Open the URL and read the HTML
        with urllib.request.urlopen(url) as response:

            # If the response is not HTML, return an empty list
            if not response.info().get('Content-Type').startswith("text/html"):
                return []
            
            # Decode the HTML
            html = response.read().decode('utf-8')
    except Exception as e:
        print(e)
        return []

    # Create the HTML Parser and then Parse the HTML to get hyperlinks
    parser = HyperlinkParser()
    parser.feed(html)

    return parser.hyperlinks

# Function to get the hyperlinks from a URL that are within the same domain
def get_domain_hyperlinks(local_domain, url):
    clean_links = []
    for link in set(get_hyperlinks(url)):
        clean_link = None

        # If the link is a URL, check if it is within the same domain
        if re.search(http_url_pattern, link):
            # Parse the URL and check if the domain is the same
            url_obj = urlparse(link)
            if url_obj.netloc == local_domain:
                clean_link = link

        # If the link is not a URL, check if it is a relative link
        else:
            if link.startswith("/"):
                link = link[1:]
            elif link.startswith("#") or link.startswith("mailto:"):
                continue
            clean_link = "https://" + local_domain + "/" + link

        if clean_link is not None:
            if clean_link.endswith("/"):
                clean_link = clean_link[:-1]
            clean_links.append(clean_link)

    # Return the list of hyperlinks that are within the same domain
    return list(set(clean_links))

# Function to get the publish date from 'var ct = "1683612031";' line
def get_publish_date(article):
    pattern = r"var ct = \"(\d+)\""
    dt = int(re.search(pattern, article).group(1))
    dt_format = time.strftime(date_format_str, time.localtime(dt))
    return dt_format


def crawl(domain, urls):
    # Parse the URL and get the domain
    local_domain = domain

    # Create a queue to store the URLs to crawl
    queue = deque(urls)

    # Create a set to store the URLs that have already been seen (no duplicates)
    seen = set(urls)

    # Create a directory to store the text files
    text_path = d_conf['text_path']
    if not os.path.exists(text_path):
            os.mkdir(text_path)

    if not os.path.exists(text_path + local_domain + "/"):
            os.mkdir(text_path + local_domain + "/")

    # Create a directory to store the csv files
    if not os.path.exists("processed"):
            os.mkdir("processed")

    counter = 0
    # While the queue is not empty, continue crawling
    while queue:

        # Get the next URL from the queue
        url = queue.pop()
        print(url) # for debugging and to see the progress
        
        # Get the text from the URL using BeautifulSoup
        response = requests.get(url).text
        soup = BeautifulSoup(response, "html.parser")

        publish_date = get_publish_date(response)
        print(f"domain:{domain}, publish_date:{publish_date}, url:{url}")

        # Get the text but remove the tags
        text = soup.get_text()

        # Save text from the url to a <url>.txt file
        with open(text_path + f"{local_domain}/{publish_date}__" + url[8:].replace("/", "_") + ".txt", "w") as f:

            # If the crawler gets to a page that requires JavaScript, it will stop the crawl
            if ("You need to enable JavaScript to run this app." in text):
                print("Unable to parse page " + url + " due to JavaScript being required")
            else:
                # Otherwise, write the text to the file in the text directory
                f.write(text)
                counter += 1


        '''
        # Get the hyperlinks from the URL and add them to the queue
        for link in get_domain_hyperlinks(local_domain, url):
            if link not in seen:
                queue.append(link)
                seen.add(link)

        '''

def main():
    for domain, urls in full_urls.items():
        crawl(domain, urls)

if __name__ == '__main__':
    main()
