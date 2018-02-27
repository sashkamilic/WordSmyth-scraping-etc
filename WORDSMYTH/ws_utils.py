import re
import multiprocessing
import collections
import csv
import os
import ssl
import sys
import time
import uuid
import urllib2
import wget
from nltk.tokenize import RegexpTokenizer
#from nltk.stemmer import PorterStemmer
from bs4 import BeautifulSoup
#from multiprocessing import Pool
reload(sys)
sys.setdefaultencoding('utf-8')

#ssl._create_default_https_context = ssl._create_unverified_context

tokenizer = RegexpTokenizer(r'\w+') # no punctuation

NUM_PROCESSES = 8
OUTDIR = './semcor_convert3'
#STOPWORDS = frozenset(stopwords.words('english'))

def homonym_urls(word):
    '''
    Return urls of word definitions of a homonym.
    Return False if word is not a homonym.

    ***A word is considered a homonym if it has more than one definition on WordSmyth.
    '''
    url = "https://www.wordsmyth.net/?level=3&ent={}".format(word)
    #filename = wget.download(url, out='{}.html'.format(uuid.uuid4().hex))
    #page = open(filename).read()
    try:
        time.sleep(3)
        response = urllib2.urlopen(url)
    except urllib2.HTTPError, e:
        print(word, e)
        return [False, []]
    page = response.read()
    soup = BeautifulSoup(page, 'html.parser')
    #os.remove(filename)
    #if len(soup.find_all('div', class_ = "more")) == 0:
    #    return []
    results = []
    derived = False
    if not soup.find('div', class_ = "wordlist"):
        return derived, []
    tbody = soup.find('div', class_ = "wordlist").table.tbody
    for td in tbody.find_all('td'):
        if td.find('a'):
            text = td.find('a').find(text=True, recursive=False)
            if text == word:
                href = td.find_all('a', href=True)[0]['href'] 
                results.append(href)
            elif text[0] != '-' or text[-1] != '-':
                derived = True
                
    return derived, results


def urls2(word):
    '''
    Return urls of word definitions of a homonym.
    Return False if word is not a homonym.

    ***A word is considered a homonym if it has more than one definition on WordSmyth.
    '''
    url = "https://www.wordsmyth.net/?level=3&ent={}".format(word.replace(" ", "%20"))
    #filename = wget.download(url, out='{}.html'.format(uuid.uuid4().hex))
    #page = open(filename).read()
    time.sleep(3)
    response = urllib2.urlopen(url)
    page = response.read()
    soup = BeautifulSoup(page, 'html.parser')
    #os.remove(filename)
    #if len(soup.find_all('div', class_ = "more")) == 0:
    #    return []
    results = []
    if not soup.find('div', class_ = "wordlist"):
        return None
    tbody = soup.find('div', class_ = "wordlist").table.tbody
    potential_derived = False
    for td in tbody.find_all('td'):
        if td.find('a'):
            text = td.find('a').find(text=True, recursive=False)
            results.append(text)
            if text[0] != "-" and text[-1] != "-":
                if text != word:
                    potential_derived = True
            '''
            if td.find('a').find(text=True, recursive=False) == word:
                results.append(td.find('a').get('href'))
            '''
    if potential_derived:
        return [word] + results


def definitions(url, pos=False):
    '''
    Return a list of definitions given a WordSmyth url.
    url - WordSmyth url (e.g. "https://www.wordsmyth.net/?level=3&ent=dog")
    '''

    try:
        time.sleep(3)
        response = urllib2.urlopen(url)
    except urllib2.HTTPError, e:
        print(url, e)
        return None

    page = response.read()
    soup = BeautifulSoup(page, 'html.parser')

    maintable = soup.tbody.find('table', class_="maintable")
    if not maintable:
        # no results
        return None
    defs = collections.OrderedDict() # remember order of insertion
    cur_pos = None
    for tr in maintable.tbody.findChildren():

        if tr.get("class"):

            if tr.get("class")[0] == "postitle":
                if tr.find("td", attrs={'class': 'data'}).a:
                    cur_pos = tr.find("td", attrs={'class': 'data'}).a.text
                else:
                    cur_pos = tr.find("td", attrs={'class': 'data'}).text
                defs[cur_pos] = []

            if tr.get("class")[0] == "definition":
                def_ = tr.find("td", attrs={'class': 'data'}).find_all(text=True, recursive=False)[0]
                # update bag with words from definition
                defs[cur_pos].append(' '.join([t.lower() for t in tokenizer.tokenize(def_)]))

    # remove stopwords
    # bag -= STOPWORDS
    # stem words
    # bag = set([stem(w) for w in bag])
    if not pos:
        return flatten(defs.values())
    return defs


def meaning_bag(pos, url):
    '''
    Return a "meaning bag" given a WordSmyth url. A meaning bag is a bag
    of stemmed words derived from a WordSmyth url of a definition page.

    pos - either "noun" or "verb"
    url - WordSmyth url (e.g. "https://www.wordsmyth.net/?level=3&ent=dog")
    '''

    """
    # download page to file
    filename = wget.download(url, out='{}.html'.format(uuid.uuid4().hex))
    page = open(filename).read()
    soup = BeautifulSoup(page, 'html.parser')
    # delete file !!!
    os.remove(filename)
    """

    response = urllib2.urlopen(url)
    page = response.read()
    soup = BeautifulSoup(page, 'html.parser')
 
    bag = set()
    maintable = soup.tbody.find('table', class_="maintable")
    if not maintable:
        # no results
        return None
    correct_pos = False
    number_of_senses = 0
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
            number_of_senses += 1
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
    return(number_of_senses, bag)


def reparse():
    filename = '/h/118/sasa/homonymy_polysemy/matched_stimuli.tsv'
    out = open('reparsed_stimuli2.tsv', 'w')
    fieldnames = ['word', 'cat', 'nM_b', 'nM_s', 'nS_b', 'nS_s', 'n|v|a|o', 'derived']
    writer = csv.DictWriter(out, fieldnames=fieldnames, delimiter='\t')
    writer.writeheader()
    with open(filename) as csvfile:
        reader = csv.DictReader(csvfile)
        for i,row in enumerate(reader):
            
            if i % 50 == 0:
                print(i)

            word = row['word|s']
            derived, urls = homonym_urls(word)
            defs = []
            for url in urls:
                defs.append(definitions(url, pos=True)) 

            nsenses_per_pos = [0, 0, 0, 0]
            for d in defs:
                for k,v in d.items():
                    if 'noun' in k:
                        nsenses_per_pos[0] += len(v)
                    elif 'verb' in k:
                        nsenses_per_pos[1] += len(v)
                    elif 'adjective' in k:
                        nsenses_per_pos[2] += len(v)
                    else:
                        nsenses_per_pos[3] += len(v)
                        
            row_out = {}
            row_out['word'] = word
            row_out['nM_b'] = row['nMeaningWordsmyth|f']
            row_out['nM_s'] = len(urls)
            row_out['nS_b'] = row['nSenseWordsmyth|f']
            row_out['nS_s'] = sum(nsenses_per_pos)
            row_out['n|v|a|o'] = '|'.join([str(x) for x in nsenses_per_pos])
            row_out['derived'] = derived 

            if row_out['nM_s'] > 1:
                row_out['cat'] = 'H'
            elif row_out['nS_s'] > 1:
                row_out['cat'] = 'P'
            else:
                row_out['cat'] = 'M'

            writer.writerow(row_out)


def derived_forms(): 
    filename = '/h/118/sasa/homonymy_polysemy/matched_stimuli.tsv'
    words = [line.split(',')[1] for line in open(filename).readlines()[1:]]
    for w in words:
        result = urls2(w)
        if result:
            print('\t'.join(u'"{}"'.format(w) for w in result).encode('utf-8'))


def get_all_definitions(wordlist, letter):

    out1 = open('/u/sasa/sasa/HOMONOMY_POLYSEMY/WORDSMITH2/homonyms.{}.txt'.format(letter), 'w')
    out2 = open('/u/sasa/sasa/HOMONOMY_POLYSEMY/WORDSMITH2/non_homonyms.{}.txt'.format(letter), 'w')
    out3 = open('/u/sasa/sasa/HOMONOMY_POLYSEMY/WORDSMITH2/derived.{}.txt'.format(letter), 'w')

    #wordlist = sorted(wordlist, reverse=True)
    n = float(len(wordlist))

    for i,word in enumerate(wordlist):

        if int(round(i / n, 5) * 100000) % 10 == 0:
            print("{}\t{}".format(letter, round(i / n, 2)))
             

        '''
        if i < 2774:
            continue
        '''
        m = re.match('([A-Za-z]+)', word)
        if not m:
            continue
        word = m.group(1)

        result = urls2(word)
        if result:
            # derived form
            out3.write('\t'.join(w for w in result) + '\n')
        derived, urls = homonym_urls(word)
        if not derived and len(urls) > 1:
            # word is a homonym
            for i,url in enumerate(urls, start=1):
                out1.write('#{}.{}'.format(word, i) + '\n')
                defs = definitions(url, pos=True)
                for pos in defs.keys():
                    for d in defs[pos]:
                        out1.write('{}\t{}\n'.format(pos, d))
            continue
        # at this point, only non-homonym, non-derived forms remaining
        url = "https://www.wordsmyth.net/?level=3&ent={}".format(word)
        defs = definitions(url, pos=True)
        if not defs:
            continue
        out2.write('#{}'.format(word) + '\n') 
        for pos in defs.keys():
            for d in defs[pos]:
                sentence = '{}\t{}\n'.format(pos, d)
                out2.write(sentence)



def scrape_all_words(outfile):
    '''
    Save a list of all words on WordSmyth
    '''
    url = "https://www.wordsmyth.net/?mode=browse"
    out = open(outfile, 'w')

    while True:
        response = urllib2.urlopen(url)
        page = response.read()
        soup = BeautifulSoup(page, 'html.parser')

        tbody = soup.find('div', class_ = "wordlist").table.tbody
        for td in tbody.find_all('td'):
            if td.a:
                out.write(td.a.text.encode('utf-8') + '\n')
        arrow_div = soup.find('div', class_ = "arrow")
        if arrow_div:
            url = arrow_div.a.get('href')


if __name__ == "__main__":
    #main()
    #l = semcor.tagged_sents(tag='both')
    #main2(1, l)

    #url = "https://www.wordsmyth.net/?level=3&ent_l=bank&rid=3205"
    #definitions(url)#, pos=True)
    #print(homonym_urls("post"))
    #reparse()
    #derived_forms()
    #filename = '/u/sasa/sasa/HOMONOMY_POLYSEMY/WORDSMYTH/all_wordsmyth_words.txt'
    #scrape_all_words(filename)
    master_wordlist = open('/u/sasa/sasa/HOMONOMY_POLYSEMY/WORDSMYTH/all_wordsmyth_words.txt').readlines()
    master_wordlist = [w.strip() for w in master_wordlist]
    #get_all_definitions('/u/sasa/sasa/HOMONOMY_POLYSEMY/WORDSMYTH/all_wordsmyth_words.txt')

    alphabet = collections.defaultdict(list)
    for word in master_wordlist:
        alphabet[word[0].upper()].append(word)
    
    jobs = []
    #k = 'R'
    #l = ['Zephaniah']
    for k,l in alphabet.items():
        p = multiprocessing.Process(target=get_all_definitions, args=(l,k))
        jobs.append(p)
        p.start()

