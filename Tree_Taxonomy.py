# import pywikibot

# item = "Salix nigra"

# site = pywikibot.Site()
# page = pywikibot.Page(site, item)
# text = page.
# print(text)

import requests 
import json
import xml.etree.ElementTree as ET 
import pprint as pp
import pandas as pd
from csv import reader

#latins = [x[0] for x in trees]

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

if __name__ == '__main__':    
    # tree_file = r"D:\Git\Tree_Family_Images\tree_list.csv"
    # with open(tree_file) as f:
    #     tree_list = list(reader(f))
    # print(tree_list)
    t = vt_va_trees()
    print(t)
    url = r"http://dendro.cnre.vt.edu/dendrology/syllabus/factsheet.cfm?ID="

    for tree in t:
        r = requests.get(url + tree[2])
        print(r.content)
        quit()