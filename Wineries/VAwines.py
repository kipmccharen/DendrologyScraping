import pandas as pd 
import requests
from bs4 import BeautifulSoup
import collections
import re
import os
from datetime import datetime

def getvineyards(parent_url):
    page = requests.get(parent_url).text
    soup = BeautifulSoup(page, "lxml")

    # Get list of all the wineries
    linkrefs = soup.findAll('li' , attrs={'class':'winery-list__item'})
    refs = []
    # For each winery found in the parent page, scape its individual page
    for link in linkrefs:
        winery = {}
        hlinks = link.findAll('a')

        # Get basics header data from the main page
        for ahl in hlinks:
            if 'class=winery-list__text' in ahl['href']:
                winery['website'] = ahl.text 
            else:
                winery['name'] = ahl.text 
                winery['vapage'] = 'https://www.virginiawine.org' + ahl['href']
        print(winery['name'])
        if link.find('p'):
            winery['phone'] = link.find('p').text
        winery['address'] = link.find('address').text 

        # Get further header data from winery's individual page
        wpage = requests.get(winery['vapage']).text
        wsoup = BeautifulSoup(wpage, "lxml")
        winery['region'] = wsoup.find('span' , attrs={'class':'card__heading'}).text.replace('Region: ', '').strip()
        headersect = wsoup.find('div', attrs={'class':'col-xs-12 col-md-8'})
        try: #sometimes there is no description
            descard = headersect.find('div', attrs={'class':'markdown'})
            winery['descr'] = descard.find('p').text.strip()
        except:
            pass
        
        # Get info about wines currently available
        if headersect.findAll('div', attrs={'class':'record-detail__wine-cat-list-item'}):
            winelist = headersect.findAll('div', attrs={'class':'record-detail__wine-cat-list-item'})
            for winetype in winelist:
                wtype = winetype.find('span',class_='card__heading').text
                subtypes = winetype.findAll('a')
                tpwines = [x.text.strip() for x in subtypes]
                winery[f"wines_{wtype}"] = tpwines

        # Iterate through finding winery data using the "cards" construct
        cards = wsoup.find('div', attrs={'class':'col-xs-12 col-md-4'}).findAll('div', attrs={'class':'card'})
        for card in cards:
            clist = card.findAll('div', attrs={'class':'card__list'})

            # Different searching scenarios for different content "Cards"
            if re.search(r'(Tasting Fee|Tour Fee)', card.text):
                fees = card.findAll('div', attrs={'class':'card__content'})
                fees = [x.text.replace('Fee\n', 'Fee: ').strip() for x in fees]
                winery['fees'] = ', '.join(fees)
            elif re.search(r'Seasonal Hours', card.text):
                timelist = []
                for cl in clist:
                    divs = cl.findAll('div')
                    divs = [re.sub(r'\s{2,}','  ', x.text.replace('\n', '')).strip() for x in divs]
                    #if ' PM' in divs.text or 'Wed: ' in divs.text:
                    for it in divs:
                        catchvals = re.findall(r'\s?([\w]+)[\s]*([\w: 0-9-]+)',it)
                        catchvals = [(x[0], 'Closed') if 'Closed' in ''.join(x) else x for x in catchvals]
                        timelist.append(catchvals[0])
                    winery['hours'] = [a[0] + ': ' + a[1] for a in timelist]
                    #else:
                    del divs
                del clist
            elif re.search(r'Hours of Operation', card.text):
                winery['hours'] = card.find('p', attrs={'class':'card__text'}).text.strip()
            elif re.search(r"(Ships to)", card.text):
                sl = list(card.find('span', attrs={'class':'card__shipping-state-list'}).children)
                winery['shipsto'] = [x.string.strip() for x in sl if len(x.string.strip()) > 1]
            elif re.search(r"(Features)", card.text):
                cli = re.findall(r"[\s]*([\w\/ ]+)[\s]*", card.text)
                cli.remove('Features') #this is the section header, not a real value
                winery['amenities'] = cli
            elif re.search(r"(Trails)", card.text):
                winery['trails'] = [(am.text.strip(), am['href']) for cl in clist for am in cl.findAll('a')]
            elif re.search(r"data-lat", str(card)):
                latlong = card.find('div', attrs={'class':'card__map'}) 
                winery['reglatlong'] = (float(latlong['data-lat']), float(latlong['data-lng']))
        refs.append(winery)
    return refs

def munge(filedir):
    df = pd.read_csv(filedir)
    a = df.iloc[[0]]
    print(a)
    response = requests.get('https://maps.googleapis.com/maps/api/geocode/json?address=1600+Amphitheatre+Parkway,+Mountain+View,+CA')
    resp_json_payload = response.json()
    print(resp_json_payload['results'][0]['geometry']['location'])

if __name__ == '__main__':    
    start_time = datetime.now()
    vawinelist = r"https://www.virginiawine.org/wineries/all"
    currdir = os.path.dirname(os.path.abspath(__file__)) + "\\"

    winelist = getvineyards(vawinelist)
    pd.DataFrame(winelist).to_csv(currdir + r"VA_Wineries.csv")
    
    #munge_data = munge(currdir + r"VA_Wineries.csv")
    print("--- %s seconds ---" % (datetime.now() - start_time))