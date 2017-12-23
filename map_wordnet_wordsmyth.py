import csv
import nltk
import os
import ssl
import uuid
import urllib2
import wget
import xml.etree.ElementTree as ET
#from nltk.stemmer import PorterStemmer
from nltk.corpus import semcor
from bs4 import BeautifulSoup
from lxml import html
from multiprocessing import Pool
from nltk.corpus import stopwords
from nltk.corpus import wordnet as wn
from nltk.tokenize import RegexpTokenizer
from stemming.porter2 import stem

ssl._create_default_https_context = ssl._create_unverified_context

tokenizer = RegexpTokenizer(r'\w+') # no punctuation

NUM_PROCESSES = 16
OUTDIR = './semcor_convert'
STOPWORDS = frozenset(stopwords.words('english'))


def main():
    # create new directory
    if not os.path.exists(OUTDIR):
        os.makedirs(OUTDIR)

    pool = Pool(processes=NUM_PROCESSES)
    pool.map(main2, os.listdir(SEMCOR_DIR))    
    #main2('br-a02')

def main2(filename):
    # csv fieldnames
    fieldnames = ['word', 'lemma', 'pos', 'is_homonym', 'wn_synset', 'ws_meaning', 'confidence', 'nsenses']
    
    print('Reading {}...'.format(filename))
    outfile = open(os.path.join(OUTDIR, filename + '.tsv'), 'w')
    writer = csv.DictWriter(outfile, fieldnames=fieldnames, delimiter='\t')
    writer.writeheader()

    for i,sent in enumerate(semcor.tagged_sents(tag='both')):

        if i % 100 == 0:
            print('{} sentences read'.format(i))

        for t in sent:
            if type(t) == str:
                # no lemma
                continue
            word = t.flatten()[0].lower()
            pos = t.pos()[0][1]
            if pos != 'NN' or not pos.startswith('V'):
                # t is not a noun or verb
                continue
            lemma = t.label().name()
            wn_synset = t.label().synset()
            nsenses = len(wn.synsets(word))

            def_bag = set([stem(w.lower()) for w in wn_synset.definition()])
            urls = homonym_urls(lemma)
            if urls == []:
                row['is_homonym'] = False
                #row['ws_meaning'] = 1
                #row['confidence'] = 1
            else:

                if pos == 'N':
                    pos_ = 'noun'
                elif pos.startswith('V'):
                    pos_ = 'verb'
 
                meaning_bags = [meaning_bag(pos_, url) for url in urls]                
                confidence = [] # list of overlap size between bags
                for mb in meaning_bags:
                    confidence.append(len(mb & def_bag))

                row['is_homonym'] = True
                row['ws_meaning'] = confidence.index(max(confidence))
                row['confidence'] = '|'.join(str(x) for x in confidence)

            row['word'] = word
            row['lemma'] = lemma
            row['pos'] = pos
            row['wn_synset'] = wn_synset
            row['nsenses'] = nsenses   
       
            writer.writerow(row) 

    outfile.close()


def wordsmyth_meaning_bags(word):
    '''
    Return meanings (details: #TODO)
    If only one meaning (not a homonym), return False
    '''
    url = u"http://www.wordsmythclient.net/compass_learning/dictionary/dictionary.php?src=&ent={}".format(word)
    page = urllib2.urlopen(url)
    soup = BeautifulSoup(page, 'html.parser')
    #for x in soup.tbody.find_all('tr'):
    #    print(x)
    if soup.find_all('span', attrs={'class':'headword'}):
        return False
    else:
        result = []
        # extract urls
        for i, a in enumerate(soup.tbody.find_all('a', href=True), 1):
            bag = set()
            url = u"http://www.wordsmythclient.net/compass_learning/dictionary/" + a['href']
            page = urllib2.urlopen(url)
            soup = BeautifulSoup(page, 'html.parser')
            dds = soup.find_all('dd', attrs={'class':'definition_dd'})
            #<dd><script type="text/javascript">
            for dd1 in dds:
                # get text from definition
                def_ = dd1.find(text=True, recursive=False)
                bag.update([t.lower() for t in nltk.word_tokenize(def_)])
                # get text from synonyms and similar words
                for dd2 in dd1.find_all('dd'):
                    bag.update([t.lower() for t in nltk.word_tokenize(dd2.text)]) 
                tokens = nltk.word_tokenize(dd[0])
                tokens = [t.lower() for t in tokens]
                bag.update(tokens)
                print(dd[1:]).find_all('a')
            # remove stopwords from bag
            bag -= STOPWORDS
            result.append(bag)

    return result


def homonym_urls(word):
    '''
    Return urls of word definitions of a homonym.
    Return False if word is not a homonym.

    ***A word is considered a homonym if it has more than one definition on WordSmyth.
    '''
    url = "https://www.wordsmyth.net/?level=3&ent={}".format(word)
    filename = wget.download(url, out='{}.html'.format(uuid.uuid4().hex))
    page = open(filename).read()
    soup = BeautifulSoup(page, 'html.parser')
    os.remove(filename)
    #if len(soup.find_all('div', class_ = "more")) == 0:
    #    return []
    results = []
    if not soup.find('div', class_ = "wordlist"):
        return []
    tbody = soup.find('div', class_ = "wordlist").table.tbody
    for td in tbody.find_all('td'):
        if td.find('a') and td.find('a').find('sup'):
            results.append(td.find('a').get('href'))
    return results

def meaning_bag(pos, url):
    '''
    Return a "meaning bag" given a WordSmyth url. A meaning bag is a bag
    of stemmed words derived from a WordSmyth url of a definition page.

    pos - either "noun" or "verb"
    url - WordSmyth url (e.g. "https://www.wordsmyth.net/?level=3&ent=dog")
    '''

    # download page to file
    filename = wget.download(url, out='{}.html'.format(uuid.uuid4().hex))
    page = open(filename).read()
    soup = BeautifulSoup(page, 'html.parser')
    # delete file !!!
    os.remove(filename)
    
    bag = set()
    maintable = soup.tbody.find('table', class_="maintable")
    correct_pos = False
    for tr in maintable.tbody.findChildren():

        if tr.get("class") and tr.get("class")[0] == "postitle":
            if tr.find("td", class_ = "data").a:
                pos_ = tr.find("td", class_ = "data").a.text
            else:
                pos_ = tr.find("td", class_ = "data").text    

            if pos in pos_.split():
                correct_pos = True
            else:
                correct_pos = False
        
        elif tr.get("class") and tr.get("class")[0] == "definition" and correct_pos:
            def_ = tr.find("td", attrs={'class': 'data'}).find_all(text=True, recursive=False)[0]
            # update bag with words from definition
            bag.update([t.lower() for t in tokenizer.tokenize(def_)])
            # check for "similar words"
            if tr.find("td", attrs={'class': 'data'}).find("dl"):
                sim_words = tr.find("td", attrs={'class': 'data'}).dl.dd.a.text
                # update bag with words from "related words" section
                bag.update([t.lower() for t in tokenizer.tokenize(sim_words)])

        elif tr.get("class") and tr.get("class")[0] == "related_word" and correct_pos:
            rel_words = tr.find("td", class_="data").a.text
            # update bag with words from "related words" section
            bag.update([t.lower() for t in tokenizer.tokenize(rel_words)])

    # remove stopwords
    bag -= STOPWORDS
    # stem words
    bag = set([stem(w) for w in bag])
    return(bag)


if __name__ == "__main__":
    #main()
    main2('bigfile')

