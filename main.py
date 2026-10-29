from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import requests
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin
import re

BASE_URL = "https://himpuh.or.id"
url = "https://himpuh.or.id/blog/kategori/2/berita"
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

kartu_elems = soup.find_all('article', class_='kartu')
articles = []

month_map = {
    'januari': 'January', 'februari': 'February', 'maret': 'March',
    'april': 'April', 'mei': 'May', 'juni': 'June',
    'juli': 'July', 'agustus': 'August', 'september': 'September',
    'oktober': 'October', 'november': 'November', 'desember': 'December'
}

DATE_RE = re.compile(
    r'Ditulis pada\s*:\s*(\d{1,2})\s+(\w+)\s+(\d{4}),\s*(\d{1,2}):(\d{2}):(\d{2})',
    re.IGNORECASE,
)


def absolute_url(href):
    if not href:
        return None
    return urljoin(BASE_URL, href)


def parse_published_date(text):
    if not text:
        return None
    match = DATE_RE.search(text)
    if not match:
        return None
    day, month_id, year, hour, minute, second = match.groups()
    month_en = month_map.get(month_id.lower(), month_id)
    try:
        published_date = datetime.strptime(
            f"{day} {month_en} {year} {hour}:{minute}:{second}",
            "%d %B %Y %H:%M:%S",
        )
        jakarta_tz = timezone(timedelta(hours=7))
        return published_date.replace(tzinfo=jakarta_tz)
    except ValueError:
        return None


def enclosure_type(image_url):
    lowered = image_url.lower()
    if '.webp' in lowered:
        return 'image/webp'
    if '.png' in lowered:
        return 'image/png'
    if '.gif' in lowered:
        return 'image/gif'
    return 'image/jpeg'


for kartu in kartu_elems:
    title_link = kartu.select_one('h2.kartu__judul a') or kartu.find('a')
    if not title_link:
        continue

    title = title_link.get_text(strip=True)
    article_link = absolute_url(title_link.get('href', url))

    intro_elem = kartu.find('p', class_='kartu__intro')
    content = intro_elem.get_text(strip=True) if intro_elem else "No content found"

    img = kartu.select_one('.kartu__media img') or kartu.find('img', class_='bb-thumb')
    image_url = absolute_url(img.get('src')) if img and img.get('src') else None

    meta_elem = kartu.find('p', class_='kartu__meta')
    published_date = parse_published_date(meta_elem.get_text(' ', strip=True) if meta_elem else '')

    articles.append({
        'title': title,
        'link': article_link,
        'content': content,
        'image': image_url,
        'published_date': published_date,
    })

# Sort articles by published_date (newest first), then take top 4
articles.sort(key=lambda x: x['published_date'] if x['published_date'] else datetime.min, reverse=True)
articles = articles[:4]

# Create an RSS feed
feed = FeedGenerator()
feed.title("Himpuh Blog Feed")
feed.link(href=url, rel='alternate')
feed.description("A feed of Himpuh blog posts")

# Add entries for each article (already sorted newest first)
for article in articles:
    entry = feed.add_entry()
    entry.title(article['title'])
    entry.content(article['content'])
    entry.link(href=article['link'])
    
    # Add published date if available
    if article['published_date']:
        entry.pubDate(article['published_date'])
    
    # Add image as enclosure (proper RSS format for media)
    if article['image']:
        entry.enclosure(url=article['image'], length=0, type=enclosure_type(article['image']))

# Save the RSS feed
with open('output.xml', 'wb') as f:
    f.write(feed.rss_str(pretty=True))
