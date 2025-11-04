from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import requests
from datetime import datetime, timezone, timedelta
import re

# Parse the website
url = "https://himpuh.or.id/blog"
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

# Find all article containers (assuming articles are in a common parent structure)
# We'll group by finding all judul divs and their associated content
judul_divs = soup.find_all('div', class_='judul')
articles = []

# Indonesian month names mapping
month_map = {
    'januari': 'January', 'februari': 'February', 'maret': 'March',
    'april': 'April', 'mei': 'May', 'juni': 'June',
    'juli': 'July', 'agustus': 'August', 'september': 'September',
    'oktober': 'October', 'november': 'November', 'desember': 'December'
}

# Extract articles with date/time
for i, judul_div in enumerate(judul_divs):
    # Get title and link
    title_link = judul_div.find('a')
    if not title_link:
        continue
    
    title = title_link.text.strip()
    article_link = title_link.get('href', url)
    # Make sure link is absolute
    if article_link.startswith('/'):
        article_link = 'https://himpuh.or.id' + article_link
    
    # Find the content (intro) - it should be in the same parent container or nearby
    # Try to find it relative to the judul div
    parent = judul_div.parent
    content_elem = parent.find('div', class_='intro mb5') if parent else None
    if not content_elem:
        # Try finding in the same row/container
        content_elem = soup.find('div', class_='intro mb5')
    
    content = content_elem.text.strip() if content_elem else "No content found"
    
    # Find the thumbnail for this article - look in the same parent container
    thumbnail = parent.find('div', class_='thumbnail') if parent else None
    if not thumbnail:
        # Try to find all thumbnails and match by index
        all_thumbnails = soup.find_all('div', class_='thumbnail')
        if i < len(all_thumbnails):
            thumbnail = all_thumbnails[i]
    
    # Extract webp image from thumbnail
    image_url = None
    if thumbnail and 'data-origin' in thumbnail.attrs:
        img_url = thumbnail['data-origin']
        if img_url.endswith('.webp'):
            image_url = img_url
    
    # Extract date and time from waktu-posting div
    waktu_posting = parent.find('div', class_='waktu-posting') if parent else None
    if not waktu_posting:
        # Try to find all waktu-posting divs and match by index
        all_waktu = soup.find_all('div', class_='waktu-posting')
        if i < len(all_waktu):
            waktu_posting = all_waktu[i]
    
    published_date = None
    if waktu_posting:
        waktu_text = waktu_posting.get_text()
        # Extract date/time from "Ditulis pada : 04 November 2025, 10:00:53"
        match = re.search(r'Ditulis pada\s*:\s*(\d{1,2})\s+(\w+)\s+(\d{4}),\s*(\d{1,2}):(\d{2}):(\d{2})', waktu_text, re.IGNORECASE)
        if match:
            day, month_id, year, hour, minute, second = match.groups()
            # Convert Indonesian month to English
            month_id_lower = month_id.lower()
            month_en = month_map.get(month_id_lower, month_id)
            try:
                # Parse the date string
                date_str = f"{day} {month_en} {year} {hour}:{minute}:{second}"
                published_date = datetime.strptime(date_str, "%d %B %Y %H:%M:%S")
                # Add timezone info (UTC+7 for Indonesia/Asia/Jakarta)
                jakarta_tz = timezone(timedelta(hours=7))
                published_date = published_date.replace(tzinfo=jakarta_tz)
            except ValueError:
                published_date = None
    
    articles.append({
        'title': title,
        'link': article_link,
        'content': content,
        'image': image_url,
        'published_date': published_date
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
        entry.enclosure(url=article['image'], length=0, type='image/webp')

# Save the RSS feed
with open('output.xml', 'wb') as f:
    f.write(feed.rss_str(pretty=True))
