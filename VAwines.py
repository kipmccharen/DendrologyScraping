import pandas as pd 
import requests
from bs4 import BeautifulSoup

def getvineyards(parent_url):
    page = requests.get(parent_url).text
    soup = BeautifulSoup(page, "lxml")
    linkrefs = soup.findAll('a')
    refs = []
    for link in linkrefs:
        if parent_url + r'/' in link['href']:
            refs.append(link['href'])
    refs = sorted(list(set(refs)))

if __name__ == '__main__':    
    vawinelist = r"https://www.virginiawine.org/wineries/all"