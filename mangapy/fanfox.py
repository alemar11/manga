import re
import requests

from mangapy.mangarepository import MangaRepository, Manga, Chapter, Page
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

def baseN(num, b, numerals="0123456789abcdefghijklmnopqrstuvwxyz"):
    return ((num == 0) and numerals[0]) or (baseN(num // b, b, numerals).lstrip(numerals[0]) + numerals[num % b])


def unpack(p, a, c, k, e=None, d=None):
    while (c):
        c -= 1
        if (k[c]):
            p = re.sub("\\b" + baseN(c, a) + "\\b",  k[c], p)
    return p


session = requests.Session()

headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=1.0,image/webp,image/apng,*/*;q=1.0', 
    'Accept-Encoding': 'gzip, deflate',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.101 Safari/537.36',
    'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
    'Referer': 'http://fanfox.net',
    'Connection': 'keep-alive'
    }

session.cookies['isAdult'] = '1'
session.headers = headers


class FanFoxRepository(MangaRepository):
    name = "FanFox"
    base_url = "http://fanfox.net"

    def search(self, manga_name):
        # support alphanumeric names with multiple words
        manga_name_adjusted = re.sub(r'[^A-Za-z0-9]+', '_', re.sub(r'^[^A-Za-z0-9]+|[^A-Za-z0-9]+$', '', manga_name)).lower()
        manga_url = "{0}/manga/{1}".format(self.base_url, manga_name_adjusted)
        
        response = session.get(url=manga_url)

        if response is None or response.status_code != 200:
            return None

        content = response.text
        soup = BeautifulSoup(content, features="html.parser")
        chapters_detail = soup.find('ul', {'class': 'detail-main-list'})
        
        if chapters_detail is None:
            return None
        
        chapters = chapters_detail.findAll('a', href=True)
        chapters_url = map(lambda c: c['href'], reversed(chapters))
        manga_chapters = []
        
        for url in chapters_url:
            number = url.split("/")[-2][1:]  # relative url, todo: regex
            absolute_url = "{0}{1}".format(self.base_url, url)
            chapter = FanFoxChapter(absolute_url, number)
            manga_chapters.append(chapter)
        
        manga = Manga(manga_name, manga_chapters)
        return manga


class FanFoxChapter(Chapter):
    def _get_links(self, content):
        js = re.search(r'eval\((function\b.+)\((\'[\w ].+)\)\)', content).group(0)
        encrypted = js.split('}(')[1][:-1]
        unpacked = eval('unpack(' + encrypted) 
        return unpacked

    def _get_key(self, content):
        js = re.search(r'eval\((function\b.+)\((\'[\w ].+)\)\)', content).group(0)
        encrypted = js.split('}(')[1][:-1]
        unpacked = eval('unpack(' + encrypted)
        key_match = re.search(r'(?<=var guidkey=)(.*)(?=\';)', unpacked)
        key = key_match.group(1)
        key = key.replace('\'', '')
        key = key.replace('\\', '')
        key = key.replace('+', '')
        return key

    def _one_link_helper(self, content, page, base_url):
        cid = re.search(r'chapterid\s*=\s*(\d+)', content).group(1)
        key = self._get_key(content)
        final_url = '{}/chapterfun.ashx?cid={}&page={}&key={}'.format(base_url, cid, page, key)
        response = session.get(final_url, headers=headers)
        content = response.text
        return content

    def _parse_links(self, data):
        base_path = re.search(r'pix="(.+?)"', data).group(1)
        images = re.findall(r'"(/\w.+?)"', data)
        return [base_path + i for i in images]

    def pages(self):
        base_url = self.first_page_url[:self.first_page_url.rfind('/')]
        response = session.get(self.first_page_url, headers=headers)
        content = response.text

        soup = BeautifulSoup(content, features="html.parser")
        page_numbers = soup.findAll("a", {"data-page": True})

        page_numbers = map(lambda x: int(x['data-page']), page_numbers)
        last_page_number = max(page_numbers)
        
        links = []
        for i in range(0, int(last_page_number / 2 + .5)):
            data = self._one_link_helper(soup.text, (i * 2) + 1, base_url)
            links += self._parse_links(self._get_links(data))

        pages = []
        for i, link in enumerate(links):
            pages.append(Page(i, link))

        return pages


if __name__ == '__main__':
    repository = FanFoxRepository()
    manga = repository.search("kimetsu no yaiba")
    firstChapter = manga.chapters[0]
    firstChapter.pages()


#repository.search("kimetsu no yaiba")
# test: Kimetsu no Yaiba: Tomioka Giyuu Gaiden

#repository.search('Kimetsu no Yaiba: Tomioka Giyuu Gaiden')


#repository.suggest("kimetsu")
#repository.search('Free! dj - Kekkon Shitara Dou Naru!?') # adult content
#http://fanfox.net/manga/gentleman_devil/v01/c038/1.html # adult content
