import json
import re
from typing import Dict, List
from provider.yaml_provider import YamlProvider
from bs4 import BeautifulSoup
import requests

yamlProvider = YamlProvider
class HttpRequestProvider(object):
    headers = {
        'User-Agent': 'curl/7.64.1',
        'Cookie': yamlProvider.get_config("cookie")
    }

    def search_partial_list(self, keyword:str) -> List:
        r = requests.get(f"https://www.douban.com/search?cat=1002&q={keyword}", headers=self.headers)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        elements = soup.select("div.search-result div:nth-child(3) .result")
        elements = filter(lambda x: self._filter_func_movie_only(x), elements)

        def func_item_wrap(element) -> Dict:
            a = element.select_one("div.content div h3 a")
            img = element.select_one("div.pic a img")["src"]
            name = a.string
            sid = re.search(".*sid: (\\d+),.*", a["onclick"]).group(1)
            year = re.search(".*/ (\\d+)$", element.select_one("div.content div div span.subject-cast").string).group(1)
            rating = "0"
            try:
                element.select_one("div.content div div span.rating_nums").string
            except:
                pass

            return {
                "sid": sid,
                "name": name.strip(),
                "rating": rating.strip(),
                "img": img.strip(),
                "year": year
            }

        limits = 3
        result = map(func_item_wrap, list(elements)[:limits])
        return list(result)

    def search_full_list(self, keyword:str) -> List:
        r = requests.get(f"https://www.douban.com/search?cat=1002&q={keyword}", headers=self.headers)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        elements = soup.select("div.search-result div:nth-child(3) .result")
        elements = filter(lambda x: self._filter_func_movie_only(x), elements)

        def func_item_wrap(element) -> Dict:
            a = element.select_one("div.content div h3 a")
            sid = re.search(".*sid: (\\d+),.*", a["onclick"]).group(1)
            return self.fetch_detail_info(sid)

        limits = 3
        result = map(func_item_wrap, list(elements)[:limits])
        return list(result)

    def fetch_detail_info(self, sid:str) -> Dict:
        r = requests.get(f"https://movie.douban.com/subject/{sid}/", headers=self.headers)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.select_one("#content h1 span:nth-child(1)").string
        rating = soup.select_one("#interest_sectl div.rating_wrap.clearbox div.rating_self.clearfix strong").string
        img = soup.select_one("#mainpic a img")["src"]
        regex = r"photo/[sl](_ratio_poster|pic)/public/"
        img = re.sub(regex, "photo/raw/public/", img, 0, re.UNICODE)
        img = img.replace(r"[^.]*$", "jpg")
        print(img)
        info_text = soup.select_one(".subject #info").get_text()
        year = re.search("\\((\\d+)\\)", soup.select_one("#content h1 span.year").string).group(1)
        sid = re.search(".*/(\\d+)/.*", soup.select_one("#mainpic a")["href"]).group(1)
        titles = re.search("(.+第\w季|[\w\uff1a\uff01\uff0c\u00b7]+)\s*(.*)", title)
        name = titles.group(1)
        originalName = titles.group(2)

        intro = soup.select_one("#link-report span:nth-child(1)")
        intro = "".join(intro.stripped_strings) if intro else ""

        lines = info_text.split("\n")
        lines = map(lambda x: x.split(":", 1), lines)
        lines = filter(lambda x: len(x) > 1, lines)

        fields = ("导演", "编剧", "主演", "类型", "官方网站", "制片国家/地区", "语言", "上映日期", "片长", "又名", "IMDb链接", "IMDb", "单集片长", "首播")
        fields_names = ("director", "writer", "actor", "genre", "site", "country", "language", "screen", "duration", "subname", "imdb", "imdb", "duration", "screen")
        result:Dict[str, object] = {"name": name, "originalName": originalName, "rating": rating, "img": img, "sid": sid, "year": year, "intro": intro}

        for item in iter(lines):
            field = item[0]
            i = 0
            has = False

            while i < len(fields):
                if fields[i] == field:
                    has = True
                    break
                i+=1

            if has:
               result[fields_names[i]] = item[1].strip() 

        celebrities = soup.select("ul.celebrities-list li.celebrity")

        def func_element_wrap(element):
            cid = re.search(".*/(\\d+)/$", element.select_one("a")["href"]).group(1)
            img = re.search(".*url\\((.*)\\).*", element.select_one("div.avatar")["style"]).group(1)
            name = element.select_one("span.name").string.split(" ")[0]
            role = ""
            try:
                role = element.select_one("span.role").string.split(" ")[0]
            except:
                pass

            return {
                "id": cid,
                "img": img,
                "name": name,
                "role": role
            }

        celebrities = filter(lambda x: 'fake' not in x['class'], celebrities)
        celebrities = map(func_element_wrap, celebrities)
        celebrities = filter(lambda x: x["role"] in ["导演","配音","演员"], list(celebrities))
        result["celebrities"] = list(celebrities)

        return result

    def fetch_celebrities(self, sid:str) -> List:
        limits=15
        r = requests.get(f"https://movie.douban.com/subject/{sid}/celebrities", headers=self.headers)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        elements = soup.select("li.celebrity")

        def func_element_wrap(element) -> dict:
            cid = re.search(".*/(\\d+)/$", element.select_one("a")["href"]).group(1)
            img = re.search(".*url\\((.*)\\).*", element.select_one("div.avatar")["style"]).group(1)
            name = element.select_one("span.name").string.split(" ")[0]
            role = ""
            try:
                role = element.select_one("span.role").string.split(" ")[0]
            except:
                pass

            return {
                "id": cid,
                "img": img,
                "name": name,
                "role": role
            }

        # def load_detail(x) -> dict:
            # detail = self.fetch_celebrity_detail(x["id"])
            # return {**x, **detail}

        result = map(func_element_wrap, elements)
        result = filter(lambda x: x["role"] in ["导演","配音","演员"], list(result))
        # result = map(load_detail, list(result)[:limits])
        return list(result)[:limits]

    def fetch_celebrity_detail(self, cid) -> dict:
        r = requests.get(f"https://movie.douban.com/celebrity/{cid}/", headers=self.headers)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        info_text = soup.select_one("#headline div.info ul").get_text()
        name = soup.select_one("#content > h1").string
        img = soup.select_one("#headline > div.pic img")["src"]
        intro = "".join(soup.select_one("#intro div.bd").stripped_strings)

        lines = info_text.split("\n\n")
        lines = map(lambda x: "".join(x.split("\n")), lines)
        lines = map(lambda x: x.split(":", 1), lines)
        lines = filter(lambda x: len(x) > 1, lines)

        name = name.split(" ", 1)[0]

        fields = ("性别", "星座", "出生日期", "出生地", "职业", "更多外文名", "家庭成员", "imdb编号", "官方网站")
        fields_names = ("gender", "constellation", "birthdate", "birthplace", "role", "nickname", "friends", "imdb", "site")
        result:Dict[str, object] = {"intro": intro, "name": name, "id": cid, "img": img}

        for item in iter(lines):
            field = item[0]
            i = 0
            has = False

            while i < len(fields):
                if fields[i] == field:
                    has = True
                    break
                i+=1

            if has:
               result[fields_names[i]] = item[1].strip() 

        return result

    def _filter_func_movie_only(self, element) -> bool:
        category = element.select_one("div.content div h3 span")
        if category is None:
            return False
        text = category.string.strip()
        return "[电影]" == text or "[电视剧]" == text

    def fetch_wallpaper(self, sid) -> list[dict]:
        r = requests.get(f"https://movie.douban.com/subject/{sid}/photos?type=W&start=0&sortby=size&size=a&subtype=a", headers=self.headers)
        if r.status_code != 200:
            return []

        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select(".poster-col3 li")
        
        result = []
        for item in items:
            data_id = item["data-id"]
            small = f"https://img1.doubanio.com/view/photo/s/public/p{data_id}.jpg"
            medium = f"https://img1.doubanio.com/view/photo/m/public/p{data_id}.jpg"
            large = f"https://img1.doubanio.com/view/photo/l/public/p{data_id}.jpg"
            size = item.select_one(".prop").string.strip()
            width = size[0:size.index("x")]
            height = size[size.index("x") + 1:len(size)]
            result.append({"id": data_id, "small": small, "medium": medium, "large": large, "size": size, "width": int(width), "height": int(height)})

        return result

# if __name__ == "__main__":
    # p = HttpRequestProvider()
    # r = p.fetch_wallpaper("1295038")
    # print(r)
    # r = p.fetch_celebrity_detail("1032915")
    # print(r)
    # # # result = p.search_full_list("Harry Potter")
    # # # result = trans.search_partial_list("Harry Potter")
    # result = p.fetch_detail_info("3016187")
    # # result = p.fetch_celebrities("1295038")
    # result = json.dumps(result, ensure_ascii=False)
    # print(result)

