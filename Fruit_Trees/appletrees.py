import pandas as pd 
import requests 
from bs4 import BeautifulSoup 
import os

def getappletreedeets(parent_url, exportdir, addcol):
    page = requests.get(parent_url).text
    soup = BeautifulSoup(page, "lxml")
    linkrefs = soup.findAll('a')
    refs = []
    for link in linkrefs:
        if parent_url + r'/' in link['href']:
            refs.append(link['href'])
    refs = sorted(list(set(refs)))
    #print(len(refs), refs)
    alltreelist = []
    for i, r in enumerate(refs):
        treedict = {}
        rpage = requests.get(r).text
        rsoup = BeautifulSoup(rpage, "lxml")
        treedict['apple_name'] = rsoup.find('h1', attrs={'itemprop':'name'}).text.strip()
        treedict['treetype'] = addcol
        print(treedict['apple_name'], '{} of {}'.format(i, len(refs)), r)
        try:
            sect1 = rsoup.find('ul', attrs={'class':'mt-3 mt-md-0'})
            for x in sect1.contents:
                split = x.text.split(':')
                treedict[split[0].lower().replace(' ', '_')] = split[1].strip()
        except:
            pass
        ps = rsoup.find('div', attrs={'itemtype':'http://schema.org/Product'}).findAll('p')
        textcontext = ''
        for p in ps:
            textcontext += '\n' + p.text.strip()
        treedict['context'] = textcontext.strip()
        #print(applename, sect1)
        table = rsoup.findAll('li', attrs={'class':'list-group-item list-group-item-action'})
        for item in table:
            icons = item.contents
            cat = icons[0].string.strip()
            treedict[cat.lower().replace(' ', '_')] = ', '.join([x.string.strip() for x in icons if x.string != cat])
            # print(catlist)
            # print(treedict)
            # quit()
        alltreelist.append(treedict)
    df = pd.DataFrame(alltreelist)
    df.to_csv(exportdir, index=False)

def add_col_to_csv(filedir, colname, colval):
    df = pd.read_csv(filedir)
    df[colname] = colval
    df.to_csv(filedir, index=False)


if __name__ == '__main__':    
    # parent_url = r"https://www.orangepippintrees.com/trees/perry-pear-trees"
    # outdir = r"D:\Git\Tree_Family_Images\OrangePippinPerryTrees.csv"
    # # outdir1 = r"D:\Git\Tree_Family_Images\OrangePippinAppleTrees.csv"
    # # outdir2 = r"D:\Git\Tree_Family_Images\OrangePippinCrabappleTrees.csv"
    # # outdir3 = r"D:\Git\Tree_Family_Images\OrangePippinPearTrees.csv"
    # addcol = 'Perry tree'
    # # finaldir = r"D:\Git\Tree_Family_Images\OrangePippinTreeFull.csv"
    # getappletreedeets(parent_url, outdir, addcol)

    # xlist = [[r"D:\Git\Tree_Family_Images\OrangePippinAppleTrees.csv", "Apple tree"],
    #             [r"D:\Git\Tree_Family_Images\OrangePippinCiderTrees.csv", "Apple Cider tree"],
    #             [r"D:\Git\Tree_Family_Images\OrangePippinCrabappleTrees.csv", "Crabapple tree"]]
    # for x in xlist:
    #     add_col_to_csv(x[0], 'treetype', x[1])
    # df = pd.read_csv(outdir)
    # df['Tree'] = 'Cider tree'
    # df1 = pd.read_csv(outdir1)
    # df1['Tree'] = 'Apple tree'
    # df2 = pd.read_csv(outdir2)
    # df2['Tree'] = 'Crabapple tree'
    # result = pd.merge(df, df1, how='outer').sort_index(axis=1)
    srcdir = r"D:\Git\Tree_Family_Images"

    f = [r'{}\{}'.format(srcdir,x) for x in os.listdir(srcdir) if 'OrangePippin' in x]
    df = pd.read_csv(f.pop())
    for x in f:
        df = pd.merge(df, pd.read_csv(x), how='outer').sort_index(axis=1)
    df = df[['apple_name', 'treetype', 'context', 'picking_season', 'uses', 'cropping', 'keeping_(of_fruit)', 'flavor_style_(apples)', 'juice_style', 'juice_color', 'fruit_persistence', 'bitter_pit', 'cooking_result', 'gardening_skill', 'self-fertility', 'pollination_group', 'pollinating_others', 'ploidy', 'vigour', 'precocity', 'bearing_regularity', 'fruit_bearing', 'organic_culture', 'general_resistance', 'scab', 'mildew', 'fireblight', 'cedar_apple_rust', 'canker', 'woolly_aphid', 'cold_hardiness_(usda)', 'summer_average_maximum_temperatures', 'chill_requirement', 'frost_resistance_of_blossom', 'country_of_origin', 'period_of_origin', 'fruit_color', 'fruit_size', 'awards']]
    df.rename(columns={'apple_name': 'tree_name'})
    df.to_csv(r'{}\{}'.format(srcdir,"OrangePippinTreeFull.csv"), index=False)

    # print(f)
    
