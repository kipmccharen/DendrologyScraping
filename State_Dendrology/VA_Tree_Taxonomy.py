# CS 5010 Homework: Python and Web Scraper
# Kip McCharen (cam7cu)
# Clair Mclafferty (cm2rh)

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

def get_vt_dendro_IDs():
    """Collect a dictionary by scraping all species for each biome page
    where keys are VT plant IDs and dict values are all additional 
    information collected, comma delimited. """

    # First a dictionary to interpret biome codes
    biomes = {'BF': "Boreal Forest", 'EM': "Eastern Mixed Forest", \
        'ED':"Eastern Deciduous Forest", \
        'SM': "Southeastern Mixed/Evergreen Forest", 'TS': "Tropical Savanna", \
        'GP': "Great Plains Grasslands", 'RM': "Rocky Mountain Evergreen Forest", \
        'PC': "Pacific Coastal Forest", 'CC': "California Chaparral", \
        'CD': "Cool Desert", 'HD': "Hot Desert", 'MM': "Mexican Montane"}
    ID_list = {} #accumulate the dictionary 

    # Scrape each biome page for new IDs
    for b in biomes.keys(): 
        biome = biomes[b]

        # Generate soup object
        url = f"http://dendro.cnre.vt.edu/dendrology/data_results.cfm?Regions={b}"
        r = requests.get(url)
        soup = BeautifulSoup(r.content, features="lxml")

        # Find each list item which contains all the info we need
        lis  = soup.findAll("li")
        for l in lis:
            finda = l.find("a")['href']
            VT_ID = re.findall(r'([\d]+)',finda)[0]

            # If the key already exists, just append the biome,
            # otherwise add a new key with full information.
            if VT_ID in ID_list.keys():
                ID_list[VT_ID] = ID_list[VT_ID] + "/" + biome
            else:
                # There is a color image which indicates nativity status
                # scrape the color and use a dict to add real information.
                colors = {"green":"native", "red": "invasive", "yellow": "nonnative"}
                imgtag = l.findAll("img")[1]['src']
                for c in colors:
                    if c in imgtag:
                        nativity = colors[c]
                        break
                names = l.text.split(" - ")
                species = names[0].strip()
                common_name = names[1].strip()
                # Append new dict item where VT ID is the key, 
                # and remaining info is provided in the value, comma delim. 
                ID_list[VT_ID] = f"{species}, {common_name}, {nativity}, {biome}"
    return ID_list

def vt_state_trees(state_2char):
    """Va Tech publishes lists of trees that grow in each state 
    of the US, scrape one page of user's choice. State as 2 characters."""

    print("Getting a list of VA Trees from Virginia Tech")
    url = r"http://dendro.cnre.vt.edu/dendrology/" \
            + "data_results.cfm?state=" + state_2char
    r = requests.get(url)
    soup = BeautifulSoup(r.content, features="lxml")
    out = [] #accumulate tree list here

    # Each item we want is a list item, grab each tag and scrape
    for u in soup.find_all("li"):
        # The hyperlink tag contains the URL/text info we want
        a = u.find_all("a")[1]
        href = a['href'] #don't forget the URL
        href = href.replace(r"syllabus/factsheet.cfm?ID=", '')
        split = a.text.split(' - ') # species/common name separated by this
        split.append(href)
        out.append(split)
    return out
    
def extract_vt_dendro_data(VT_ID):
    """Scrape data from VA Tech dendrology pages, given a VT ID."""
    treeURL = f"http://dendro.cnre.vt.edu/dendrology/" \
            + f"syllabus/factsheet.cfm?ID={VT_ID}"
    
    # If URL request doesn't work, return None, otherwise proceed
    try:
        r = requests.get(treeURL).text
    except:
        print("request error") 
        return None 

    # Collect soup object to navigate
    soup = BeautifulSoup(r, 'html.parser')
    soup = soup.findAll('div', attrs={'class':'navbar-header'})[0].p

    # Initialize a dictionary of information about the plant
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

def extract_VT_landowner_data(VT_ID):
    """Scrape data from VA Tech landowner pages, given a plant's VT ID."""
    url = f"http://dendro.cnre.vt.edu/dendrology/landowner_detail.cfm?ID={VT_ID}"
    r = requests.get(url).text
    soup = BeautifulSoup(r, 'html.parser')
    strongs = soup.findAll("strong")
    thistree = {'VT_ID': VT_ID} #Initialize dict item for this species

    # The content is on the same html level as titles, need to find title
    # then go up a level with parent, then scrape content. 
    for stonks in strongs:
        txtval = stonks.text.strip()
        st_parent = stonks.parent
        st_imgs = st_parent.findAll("img")
        # Water is the unique situation where data is embedded in "src"
        # tag of the images, with "o" before the number indicating no. 
        if txtval == 'Water':
            st_imgs = [re.findall(r"[^o](\d*)\.gif",x['src'])[0] for x in st_imgs if 'o']
            st_imgs = ', '.join([inum for inum in st_imgs if inum != ''])
            thistree[txtval+"_vals"] = st_imgs
        # If number values are embedded in the image, extract and save
        elif st_imgs:
            imgsrc = st_imgs[0]['src']
            st_imgs = re.findall(r"(\d*)\.gif",imgsrc)[0]
            if st_imgs:
                thistree[txtval+"_vals"] = int(st_imgs)
        # Latin meaning is buried at a weirder inconsistent level
        if txtval == "Latin Meaning":
            txtv = st_parent.text.replace(txtval + '\n', "").strip()
            thistree[txtval+"_txt"] = txtv
        # Otherwise if there is text, just grab it and save
        else:
            txtv = st_parent.find("br")
            if txtv:
                thistree[txtval+"_txt"] = txtv.next.strip()
    #print(thistree)
    return thistree

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

def get_tsn(latin_species_name): 
    """Retrieve the TSN (taxonomy ID #) from ITIS' API. 
    The USGS runs the Integrated Taxonomic Information System (ITIS) 
    which has an API to get taxonomy info by species."""
    srctxt = "https://www.itis.gov/ITISWebService/services/" \
        + "ITISService/searchByScientificName?srchKey=" \
        + f"{latin_species_name.replace(' ', '_')}"
    r = requests.get(srctxt).text
    #https://docs.python.org/3/library/xml.etree.elementtree.html
    root = ET.fromstring(r) 
    for child in root[0]:
        for x in child:
            if x.tag[-3:] == 'tsn':
                return x.text

def get_hierarchy(tsn=-1,latin_species_name=""):
    """Retrieve the full hierarchy of a species based on 
    given TSN or species name"""
    # Grab raw HTML

    #if user provides no input, reject
    if tsn == -1 and latin_species_name == "": 
        return None
    elif tsn != -1: #if tsn given, use that first
        pass
    elif latin_species_name != "": #otherwise gather TSN from latin name
        tsn = get_tsn(latin_species_name)

    URL = "https://www.itis.gov/ITISWebService/services/" \
        + f"ITISService/getFullHierarchyFromTSN?tsn={tsn}"

    r = requests.get(URL).text
    # Initialize variables to accumulate/change
    root = ET.fromstring(r)

    #accumulate values to a dictionary, started with available info
    out = {'tsn': tsn, 'species_name': latin_species_name} 
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

def combine_forest(species_name_list, output_dir):
    """Accepts list of latin plant species names and gathers VT, ITIS, 
    and PFAF data on each. If list has more than one column, 
    retrieves the first column for latin species name. """

    # get VT IDs for all plants in their database
    VT_ID_list = get_vt_dendro_IDs()

    # if the latin_species_name_list consists of sublist, merge them together
    # so that item 1 is latin species, and item 2 is VT_ID
    if isinstance(species_name_list[0], list):
        species_only_list = [x[0] for x in species_name_list]    
    else:
        species_only_list = [x for x in species_name_list]

    latin_species_name_list = []

    for x in species_only_list:
        for vt in VT_ID_list.keys():
            vtval = VT_ID_list[vt]
            if x in vtval:
                latin_species_name_list.append([vt] + vtval.split(','))

    ## Combine all the techniques defined above to gather data for one plant
    treedata = []
    url = r"http://dendro.cnre.vt.edu/dendrology/syllabus/factsheet.cfm?ID="
    for treerow in latin_species_name_list:
        
        tree = treerow[1]  #set latin name
        VT_ID = treerow[0] #set VT ID
        print(tree)

        # Scrape VT's species page
        tree = extract_vt_dendro_data(VT_ID)
        tree['nativity'] = treerow[3]
        tree['biomes'] = treerow[4]
        landowner = extract_VT_landowner_data(VT_ID)
        tree.update(landowner)
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
    #return treedata
    # Pandas natively converts a list of dictionaries to a dataframe
    df = pd.DataFrame(treedata)
    df.to_csv(output_dir)

def analysis(df):
    """Finally do some analysis on the data to answer questions. """
    
    def edibledeets(x):
        # Convert mishmashed text into usable columns about edibility
        checkme = ['Edible Parts:','Edible Uses:']
        out = ["", "", ""]
        # list stored as literal text, need to make real
        x = ast.literal_eval(x) 
        if not x or x == ['None known']:
            return out[2], out[0], out[1]
        else:
            # Since titles and content are in the same list, make our 
            # list an iterable and call "next" to get content data 
            # at same time as title and extract it together.
            x = iter(x)
            i = -1
            for item in x:
                # If the text is really long, treat it as a paragraph
                # But break off the first section which is a list item
                if len(item) > 75:
                    index = item.find('. ')
                    out[1] = out[1] + ', ' + item[:index + 1]
                    out[2] = item[index + 2:]
                    break
                # For special sections, you can get content more easily
                if item in checkme:
                    i += 1
                    item = next(x)
                out[i] = out[i] + ', ' + item
        # remove leading delimeter from test items gathered
        out = [text[2:] if text.startswith(", ") else text for text in out]
        # initially I messed up the order I wanted, that's why it's not 0,1,2
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

    analysis_only = False 

    if not analysis_only:

        # get list of trees that grow in VA according to Virginia Tech
        t = vt_state_trees("VA") 

        # iteratively gather additional data and combine them together
        # then saves the output to variable named above
        combine_forest(t, filedir)
    else:
        # Reopen the file to easily/repeatably answer questions
        df = pd.read_csv(filedir)
        # Run analysis and print results
        analysis(df)

    # Print running time
    print("--- %s seconds ---" % (datetime.now() - start_time))
