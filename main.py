import requests
import json
import re
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor


class GDCVaultHelper:
    def __init__(self):
        self.vault_list = {}
        self.vault_classifications = {}
        self.year = 0

    def GetOverview(self, index) -> dict:
        _vault = self.vault_list["vaults"][index]
        _vault['index'] = index
        _response = requests.get(_vault["url"])
        _text = _response.text.replace("\n", "")
        _text = _text.replace("\r", "")
        _overview = re.match('.*?<h3>Overview:</h3>\s*?</dt>\s*?<dd>\s*?<p class="text-color-grey">(.*?)</p>', _text,
                             re.DOTALL)
        if _overview:
            _vault["overview"] = _overview.group(1)
        return _vault

    def DumpGDC(self, year, with_overview=False):
        self.year = year % 100
        baseUrl = f"https://gdcvault.com/free/gdc-{self.year}"
        raw = requests.get(baseUrl).text
        raw = raw.replace("\n", "")
        raw = raw.replace("\r", "")
        raw = raw.replace("&nbsp;", "")
        # remove all spaces that follows another space.
        raw = re.sub(r'\s{2,}', ' ', raw)
        self.vault_list = {"vaults": []}

        conference_section = re.match(r'.*?<section class="conference">(.*?)</section>', raw, re.DOTALL).groups(1)[0]

        list_items = re.findall(r'<li class="featured " count="" sponsor_id="" hide_sponsor="">(.*?)</li>', conference_section, re.DOTALL)

        for raw_vault in list_items:
            vault = {}
            name = re.match(r'.*?<span class="conference_name">(.*?)</span>', raw_vault, re.DOTALL)
            if name:
                vault["name"] = name.group(1)
            title = re.match(r'.*?<strong>(.*?)</strong>', raw_vault, re.DOTALL)
            if title:
                vault["title"] = title.group(1)
            author = re.match(r'.*?<em>by</em>(.*?)</span>', raw_vault, re.DOTALL)
            if author:
                groups = re.match(r'\s?(.*)(?:<strong>\(?(.*?)\)?</strong>)', author.group(1), re.DOTALL)
                if groups:
                    vault["author"] = groups.group(1)
                    # what will happen if there is no organization?
                    if groups.group(2):
                        vault["organization"] = groups.group(2)
                    else:
                        vault["organization"] = ""
            trackname = re.match(r'.*?<span class="track_name">(.*?)</span>', raw_vault, re.DOTALL)
            if trackname:
                vault["trackname"] = trackname.group(1)
            url = re.match(r'.*?<a class="session_item.*?href="(.*?)"', raw_vault, re.DOTALL)
            if url:
                vault["url"] = baseUrl + url.group(1)

            self.vault_list["vaults"].append(vault)

        if with_overview:
            # multi-threading to Call GetOverview for each vault and make a future obj to retrieve the result
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(self.GetOverview, i) for i in range(len(self.vault_list["vaults"]))]
                for future in tqdm(futures):
                    res = future.result()
                    self.vault_list["vaults"][res["index"]] = res

        with open(f"GDC{self.year}_vault_list.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(self.vault_list, indent=4))
            f.close()

    def LoadGDC(self, year):
        self.year = year % 100
        with open(f"GDC{self.year}_vault_list.json", "r", encoding="utf-8") as f:
            self.vault_list = json.load(f)
            f.close()

        for v in self.vault_list["vaults"]:
            self.vault_classifications[v['trackname']] = self.vault_classifications.get(v['trackname'], 0) + 1
        self.vault_classifications = dict(sorted(self.vault_classifications.items(), key=lambda x: x[1], reverse=True))

    def ShowClassifications(self):
        for k, v in self.vault_classifications.items():
            print(f"{k}: {v}")

    def Filter(self, classifications):
        filtered = {"vaults": []}
        for v in self.vault_list["vaults"]:
            if v["trackname"] in classifications:
                filtered["vaults"].append(v)

        filtered["vaults"] = sorted(filtered["vaults"], key=lambda x: x["trackname"])

        with open(f"GDC{self.year}_filtered.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(filtered, indent=4))
            f.close()


if __name__ == "__main__":
    helper = GDCVaultHelper()
    # helper.DumpGDC(23, with_overview=True)
    helper.LoadGDC(23)
    helper.ShowClassifications()
    helper.Filter(["Programming", "Design", "Visual Arts",
                   "Advanced Graphics Summit", "Tools Summit",
                   "Animation Summit"])
