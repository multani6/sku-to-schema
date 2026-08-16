import requests
from bs4 import BeautifulSoup

search_url = "https://dir.indiamart.com/search.mp?ss=relay+industrial&prdsrc=1&search_type=p&v=4"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.indiamart.com/",
}

response = requests.get(search_url, headers=headers)
print("Status Code:", response.status_code)

soup = BeautifulSoup(response.text, "html.parser")

all_links = soup.find_all("a", href=True)
product_links = [link['href'] for link in all_links if 'proddetail' in link['href']]

print("Total product links found:", len(product_links))
for link in product_links[:5]:
    print(link)

# Debug: check karte hain ki raw HTML mein "proddetail" hai bhi ya nahi
print("\n--- DEBUG ---")
print("'proddetail' in raw HTML text?:", "proddetail" in response.text)
print("Total <a> tags found:", len(all_links))
print("HTML length:", len(response.text))