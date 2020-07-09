import pandas as pd 
import requests
from bs4 import BeautifulSoup
import collections
import re

def getvineyards(parent_url):
    page = requests.get(parent_url).text
    soup = BeautifulSoup(page, "lxml")
    linkrefs = soup.findAll('li' , attrs={'class':'winery-list__item'})
    refs = []
    for link in linkrefs:
        winery = {}
        hlinks = link.findAll('a')
        for ahl in hlinks:
            if 'class=winery-list__text' in ahl['href']:
                winery['website'] = ahl.text 
            else:
                winery['name'] = ahl.text 
                winery['vapage'] = 'https://www.virginiawine.org' + ahl['href']
        print(winery['name'])
        try:
            winery['phone'] = link.find('p').text
        except:
            pass
        winery['address'] = link.find('address').text 
        #winery = {a: winery[a] for a in ('name', 'vapage', 'address', 'phone', 'website')}
        wpage = requests.get(winery['vapage']).text
        wsoup = BeautifulSoup(wpage, "lxml")
        winery['region'] = wsoup.find('span' , attrs={'class':'card__heading'}).text.replace('Region: ', '').strip()
        headersect = wsoup.find('div', attrs={'class':'col-xs-12 col-md-8'})
        try:
            descard = headersect.find('div', attrs={'class':'markdown'})
            winery['descr'] = descard.find('p').text.strip()
        except:
            pass
        try:
            winelist = headersect.findAll('div', attrs={'class':'record-detail__wine-cat-list-item'})
            for winetype in winelist:
                type = winetype.find('span', attrs={'class':'card__heading'}).text
                tpwines = [x.text.strip() for x in winetype.findall('a', attrs={'class':'detail-list-link'})]
            winery['wines_{}'.format(type): tpwines]
        except:
            pass
        cards = wsoup.find('div', attrs={'class':'col-xs-12 col-md-4'}).findAll('div', attrs={'class':'card'})
        for card in cards:
            clist = wsoup.findAll('div', attrs={'class':'card__list'})
            if re.search(r'(Tasting Fee|Tour Fee)', card.text):
                fees = card.findAll('div', attrs={'class':'card__content'})
                fees = [x.text.replace('Fee\n', 'Fee: ').strip() for x in fees]
                winery['fees'] = ', '.join(fees)
            elif re.search(r'Seasonal Hours', card.text):
                timelist = [re.findall(r'\s([\w]+)[\s]*([\w: 0-9-]+)',it.text)[0] for cl in clist for it in cl.findAll('div')]
                winery['times'] = [a[0] + ': ' + a[1] for a in timelist]
            elif re.search(r'Hours of Operation', card.text):
                winery['times'] = card.find('p', attrs={'class':'card__text'}).text.strip()
            elif re.search(r"(Ships to)", card.text):
                sl = list(card.find('span', attrs={'class':'card__shipping-state-list'}).children)
                #sl = sl.findall('span')
                winery['shipsto'] = [x.string.strip() for x in sl if len(x.string.strip()) > 1]
            elif re.search(r"(Features)", card.text):
                cli = re.findall(r"[\s]*([\w\/ ]+)[\s]*", card.text)
                winery['amenities'] = cli
            elif re.search(r"(Trails)", card.text):
                winery['trails'] = [(am.text.strip(), am['href']) for cl in clist for am in cl.findAll('a')]
            elif re.search(r"data-lat", str(card)):
                latlong = card.find('div', attrs={'class':'card__map'}) 
                winery['reglatlong'] = (float(latlong['data-lat']), float(latlong['data-lng']))
        #     elif  card.text.strip() not in ('View Upcoming Events', 'Find nearby wineries'):
        #         print(card)
        #         print('wait')
        # print(winery)
        refs.append(winery)
    # refs = sorted(refs)
    return refs

if __name__ == '__main__':    
    vawinelist = r"https://www.virginiawine.org/wineries/all"
    winelist = getvineyards(vawinelist)
    pd.DataFrame(winelist).to_csv(r"D:\Git\Tree_Family_Images\VA_Wineries.csv")
    