# CS 5010 Homework: Python and Web Scraper
# Kip McCharen (cam7cu)

# This project required extensive exploring of the BeautifulSoup 
# documentation, and general advice from others online to just stick 
# to the documentation unless you want to write a new parser. 

import requests 
import xml.etree.ElementTree as ET 
import pandas as pd
from bs4 import BeautifulSoup
import re 
from datetime import datetime
import ast
from collections import Counter

def vt_state_trees(state_2char):
    """Va Tech publishes lists of trees that grow in each state 
    of the US, scrape one page of user's choice. State as 2 characters."""
    print("Getting a list of VA Trees from Virginia Tech")
    url = r"http://dendro.cnre.vt.edu/dendrology/" \
            + "data_results.cfm?state=" + state_2char
    r = requests.get(url)
    soup = BeautifulSoup(r.content, features="lxml")
    out = [] #accumulate tree list here
    for u in soup.find_all("li"):
        a = u.find_all("a")[1]
        href = a['href'] #don't forget the URL
        href = href.replace(r"syllabus/factsheet.cfm?ID=", '')
        split = a.text.split(' - ')
        split.append(href)
        out.append(split)
    return out
    
def extract_vt_dendro_data(treeURL):
    """Scrape data from VA Tech dendrology pages, given a page's URL."""
    try:
        r = requests.get(treeURL).text
    except:
        print("request error") 
        return None #if URL request doesn't work, return None

    #If request works, scrape with BeautifulSoup
    soup = BeautifulSoup(r, 'html.parser')
    soup = soup.findAll('div', attrs={'class':'navbar-header'})[0].p
    #Initialize a dictionary of information about the plant
    output = {'URL': treeURL, 'common_name': soup.big.text, \
        'species': re.sub(r'[\s]{2,}', ' ', soup.em.text.strip()), \
        'lookslike': [], 'picslist': []}

    #Split the basic descriptor text to add
    searchme = re.split(r'\n|\r|\t| - ', soup.small.text)
    searchme = [x.strip() for x in searchme if x.strip() != '']
    descriptives = ' '.join(searchme)
    #Find instances if #text: other_text# to scrape
    descriptives = re.findall(r"(\w*): (.+?\.)", descriptives)
    #For each instance of above, add result to running dictionary
    for d in descriptives:
        output[d[0].strip().lower()] = \
            re.sub(r'[\s]{2,}', ' ', d[1].strip())

    #Search for list of specific tags to add in dictionary if exists
    extras = [['family', 'cfm?family'],
            ['genus', 'cfm?genus'], 
            ['symbol', 'profile?symbol']]
    for a in soup.find_all('a'):
        if 'USDA Plants Database' not in a:
            for x in extras:
                if x[1] in a['href']:
                    output[x[0]] = a.text
            if 'factsheet.cfm?ID=' in a['href']:
                output['lookslike'].append([a.text, a['href']])
            if r'../images/' in a['href']:
                output['picslist'].append(a['href'])
    
    # Grab the remaining text of the page and just add it all. 
    extratext = soup.text.replace(soup.big.text, '') \
                .replace(soup.small.text, '')
    extratext = [x.strip() for x in \
                re.split(r'\n|\r|\t| - ', extratext) \
                if "is native to" in x]
    output['range'] = ''.join(extratext) #join list together
    return output

def scrape_pfaf(latin_species_name):
    """Plants For A Future (pfaf.org) is a UK-based website with 
    lots of practical information about plants of all kinds. 
    Convert latin name to URL, and return 
    whatever possible as dictlist. """

    speciesdict = {}

    url = "https://pfaf.org/user/Plant.aspx?LatinName=" \
            + latin_species_name.replace(" ", "+")

    #Use requests to get html, BeautifulSoup to parse!
    r = requests.get(url).text
    soup = BeautifulSoup(r, 'html.parser')
    
    #Grab care-for-this-plant information, needs...special care
    care = soup.find("table", id="ctl00_ContentPlaceHolder1_tblIcons")
    #care info is hidden in the image titles, not in text
    cares = [x.get('title') for x in care.findAll('img')]
    speciesdict['care'] = cares

    #Grab info from table at the top
    #Already got care, ignore that one
    tbl = soup.find("table", class_="table table-hover table-striped")
    tbl = tbl.findAll("tr")
    for tr in tbl:
        if 'Care' not in tr.text:
            tds = [x.text.strip().replace('\n', ' ') \
                    for x in tr.findAll('td')]
            speciesdict[tds[0]] = tds[1]
    
    # For each in a list of specific details, use "find" on the "soup"
    # to find it and return the next real value. If that's available, 
    # then save it all into an accumulating dictionary
    grabthese = ["Summary", "Physical Characteristics", \
        "Synonyms", "Habitats", "Cultivation details", \
        "Propagation", 'Found in', "Edible Uses", \
        "Medicinal Uses", "Other Uses", "Special Uses"]
    for g in grabthese:
        try:
            findme = soup.find("h2", text=g)
            storage = findme.text.strip()
            findme = findme.next_sibling
            while isinstance(findme, str) or findme is None:
                findme = findme.next_sibling
            content_strings = [x for x in findme.stripped_strings]
            speciesdict[storage] = content_strings
            storage = ""
        except:
            pass
    return speciesdict

def get_tsn(txt): 
    """Retrieve the TSN (taxonomy ID #) from ITIS' API. 
    The USGS runs the Integrated Taxonomic Information System (ITIS) 
    which has an API to get taxonomy info by species."""
    srctxt = "https://www.itis.gov/ITISWebService/services/" \
        + "ITISService/searchByScientificName?srchKey=" \
        + f"{txt.replace(' ', '_')}"
    r = requests.get(srctxt).text
    #https://docs.python.org/3/library/xml.etree.elementtree.html
    root = ET.fromstring(r) 
    for child in root[0]:
        for x in child:
            if x.tag[-3:] == 'tsn':
                return x.text

def get_hierarchy(tsn, speciesname):
    """Retrieve the full hierarchy of a species based on 
    given TSN and species name"""
    # Grab raw HTML
    URL = "https://www.itis.gov/ITISWebService/services/" \
        + f"ITISService/getFullHierarchyFromTSN?tsn={tsn}"
    r = requests.get(URL).text
    # Initialize variables to accumulate/change
    root = ET.fromstring(r)
    #accumulate values to a dictionary, started with available info
    out = {'tsn': tsn, 'species_name': speciesname} 
    counter = 1
    rank = ''
    taxon = ''
    #Using the root/child structure, we can selectively find the parts
    for child in root[0]:
        for x in child:
            rank = x.text if 'rankName' in x.tag else rank
            taxon = x.text if 'taxonName' in x.tag else taxon
        if taxon:
            #if the right tax info is found, ensure output columns
            #are in logical order by appending order # before colname
            #add leading zeros to account for text sorting past 10
            out[str(counter).zfill(2) + '_' + rank] = taxon
            counter += 1
        rank = ''
        taxon = ''
    return out

def combine_forest(vt_trees):
    ## Combine all the techniques defined above to gather data for one plant
    treedata = []
    url = r"http://dendro.cnre.vt.edu/dendrology/syllabus/factsheet.cfm?ID="
    for tree in vt_trees:
        print(tree)
        curr_url = url + tree[2]
         #scrape VT's species page
        tree = extract_vt_dendro_data(curr_url)
        
        if tree: #if there's no other VT data, forget it

            try: # Try to get practical species data from pfaf
                pfaf = scrape_pfaf(tree['species'])
                tree.update(pfaf)
            except:
                print("oops no pfaf data")

            # Try to get ID according to ITIS, then scrape taxonomy
            try:
                tsn = get_tsn(tree['species'])
                hierarchy = get_hierarchy(tsn, tree['species'])
                tree.update(hierarchy)
            except:
                print("oops no ITIS data")
            treedata.append(tree)
        else:
            print("oh well, it's not a great tree anyways")
    return treedata

def analysis(df):
    """Finally do some analysis on the data to answer questions. """
    
    def edibledeets(x):
        # Convert mishmashed text into usable columns about edibility
        checkme = ['Edible Parts:','Edible Uses:']
        out = ["", "", ""]
        x = ast.literal_eval(x) #stored as literal text, need to make real
        if not x or x == ['None known']:
            return out[2], out[0], out[1]
        else:
            x = iter(x)
            i = -1
            for item in x:
                if len(item) > 75:
                    index = item.find('. ')
                    out[1] = out[1] + ', ' + item[:index + 1]
                    out[2] = item[index + 2:]
                    break
                if item in checkme:
                    i += 1
                    item = next(x)
                out[i] = out[i] + ', ' + item
        out = [text[2:] if text.startswith(", ") else text for text in out]
        return out[2], out[0], out[1]

    ## Let's create some additional columns to answer questions
    df['Poison'] = df['Known Hazards'].apply(lambda x: \
                    'poison' in str(x).lower() or 'toxic' in str(x).lower())
    df['EdibleText'], df['EdibleParts'], df['EdibleUses']  = \
                    zip(*df['Edible Uses'].map(edibledeets))
    df.drop(columns=['Edible Uses']) #don't need this anymore
    df['FreshFruit'] = df['EdibleUses'].apply(lambda x: \
                    ('Fruit - raw' in x))
    df['Berry'] = df.apply(lambda x: \
                    'berry' in x.fruit or 'berry' in x.common_name, axis=1)

    berrydf = df[df['Berry'] == True]
    print("\nThese berries grow in VA")
    print(berrydf.common_name.unique().tolist()) #print Berries

    berryfreshdf = berrydf[berrydf['FreshFruit'] == True]
    print("\nThese VA berries can be eaten fresh")
    print(berryfreshdf.common_name.unique().tolist()) #print Berries
    
    berrypoisondf = berrydf[berrydf['Poison'] == True]
    print("\nThese VA berries may be poisonous")
    print(berrypoisondf.common_name.unique().tolist()) #print Berries
    #print(df.head())
    
    specUse = df['Other Uses'].unique().tolist()
    alluses = []
    for u in specUse:
        u = ast.literal_eval(u) #stored as literal text, need to make real
        # Remove responses that we know are not real answers
        u = [x for x in u if \
            x not in ["None known", "Special Uses"] and len(x) < 40]
        alluses.extend(u)
    print("\nThese are the most prevalent other uses for trees and shrubs in VA")
    print(Counter(alluses))

if __name__ == '__main__':    
    start_time = datetime.now() # Let's see how long this runs
    filedir = r"VA_Dendro_data.csv"

    # get list of trees that grow in VA according to Virginia Tech
    t = vt_state_trees("VA") 

    # iteratively gather additional data and combine them together
    forest = combine_forest(t)
    # Pandas natively converts a list of dictionaries to a dataframe
    df = pd.DataFrame(forest)
    # Export dataframe as a csv
    df.to_csv(filedir)

    # Reopen the file to easily/repeatably answer questions
    filedir = r"VA_Dendro_data.csv"
    df = pd.read_csv(filedir)
    analysis(df)

    # Print running time
    print("--- %s seconds ---" % (datetime.now() - start_time))
