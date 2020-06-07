import requests 
import json
import xml.etree.ElementTree as ET 
import pprint as pp
import pandas as pd
from csv import reader
from bs4 import BeautifulSoup
import re 

def get_tsn(txt):
    r = requests.get(r"https://www.itis.gov/ITISWebService/services/ITISService/searchByScientificName?srchKey={}".format(txt.replace(' ', '_'))).text
    root = ET.fromstring(r) 
    for child in root[0]:
        for x in child:
            if x.tag[-3:] == 'tsn':
                return x.text

def get_hierarchy(tsn, treename):
    r = requests.get(r"https://www.itis.gov/ITISWebService/services/ITISService/getFullHierarchyFromTSN?tsn={}".format(tsn)).text
    root = ET.fromstring(r)
    out = {}
    counter = 1
    rank = ''
    taxon = ''
    for child in root[0]:
        for x in child:
            rank = x.text if 'rankName' in x.tag else rank
            taxon = x.text if 'taxonName' in x.tag else taxon
        if taxon:
            out[str(counter).zfill(2) + '_' + rank] = taxon
            counter += 1
        rank = ''
        taxon = ''
    out['treename'] = treename
    out['tsn'] = tsn
    return out

def vt_va_trees():
    from bs4 import BeautifulSoup as bs
    import requests
    url = r"http://dendro.cnre.vt.edu/dendrology/data_results.cfm?state=VA"
    r = requests.get(url)
    soup = bs(r.content, features="lxml")
    out = []
    for u in soup.find_all("li"):
        a = u.find_all("a")[1]
        href = a['href']
        out_i = a.text.split(' - ') + [href.replace(r"syllabus/factsheet.cfm?ID=", '')] 
        out.append(out_i)
    return out

def retrieve_itis_tree_data(tree_list, output_dir):
    out_list = []
    for tree in tree_list:
        latin = tree[0]
        tsn = get_tsn(latin)
        print(tree, tsn)
        h = get_hierarchy(tsn, tree[1])
        out_list.append(h.copy())
    df = pd.DataFrame(out_list)
    df.to_csv(r"D:\Py_ML_CS\trees.csv")

def extract_vt_dendro_data(treeURL):
    try:
        r = requests.get(treeURL).text
    except:
        print("request error")
        return None
    soup = BeautifulSoup(r, 'html.parser')
    soup = soup.findAll('div', attrs={'class':'navbar-header'})[0].p
    output = {'URL': treeURL, 'common_name': soup.big.text, 'species': re.sub(r'[\s]{2,}', ' ', soup.em.text.strip()), \
        'lookslike': [], 'picslist': []}
    print(output['common_name'])

    descriptives = ' '.join([x.strip() for x in re.split(r'\n|\r|\t| - ', soup.small.text) if x.strip() != ''])
    descriptives = re.findall(r"(\w*): (.+?\.)", descriptives)
    for d in descriptives:
        output[d[0].strip().lower()] = re.sub(r'[\s]{2,}', ' ', d[1].strip())

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
    
    extratext = soup.text.replace(soup.big.text, '').replace(soup.small.text, '')
    extratext = [x.strip() for x in re.split(r'\n|\r|\t| - ', extratext) if "is native to" in x]
    output['range'] = ''.join(extratext)
    return output

if __name__ == '__main__':    
    # tree_file = r"D:\Git\Tree_Family_Images\tree_list.csv"
    # with open(tree_file) as f:
    #     tree_list = list(reader(f))
    # print(tree_list)
    t = vt_va_trees()
    #print(t)
    url = r"http://dendro.cnre.vt.edu/dendrology/syllabus/factsheet.cfm?ID="
    treedata = []
    for tree in t:
        curr_url = url + tree[2]
        treed = extract_vt_dendro_data(curr_url)
        
        if treed != None:
            tsn = get_tsn(treed['species'])
            try:
                hierarchy = get_hierarchy(tsn, treed['species'])
                treed.update(hierarchy)
            except:
                pass
            # print(treed)
            # quit()
            treedata.append(treed)

    df = pd.DataFrame(treedata).drop(['common'], axis=1)
    df.to_csv('VT_Dendro_data.csv')
