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

#STOPWORDS = frozenset(stopwords.words('english'))

def homonym_urls(word):
    '''
    Return urls of word definitions of a homonym.
    Return False if word is not a homonym.

    ***A word is considered a homonym if it has more than one definition on WordSmyth.
    '''
    url = "https://www.wordsmyth.net/?level=3&ent={}".format(word.replace(' ', '_'))
    #filename = wget.download(url, out='{}.html'.format(uuid.uuid4().hex))
    #page = open(filename).read()
    try:
        #time.sleep(4)
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
            elif text[0] != u'-' and text[-1] != u'-':
                derived = True
                
    return derived, results


def suffix_urls(word):
    '''
    Return urls of word definitions of a homonym.
    Return False if word is not a homonym.

    ***A word is considered a homonym if it has more than one definition on WordSmyth.
    '''
    url = "https://www.wordsmyth.net/?level=3&ent={}".format(word.replace(' ', '_'))
    #filename = wget.download(url, out='{}.html'.format(uuid.uuid4().hex))
    #page = open(filename).read()
    try:
        #time.sleep(4)
        response = urllib2.urlopen(url)
    except urllib2.HTTPError, e:
        print(word, e)
        return None
    page = response.read()
    soup = BeautifulSoup(page, 'html.parser')
    #os.remove(filename)
    #if len(soup.find_all('div', class_ = "more")) == 0:
    #    return []
    results = []
    if not soup.find('div', class_ = "wordlist"):
        return None
    tbody = soup.find('div', class_ = "wordlist").table.tbody
    for td in tbody.find_all('td'):
        if td.find('a'):
            text = td.find('a').find(text=True, recursive=False)
            if text == word:
                href = td.find_all('a', href=True)[0]['href'] 
                results.append(href)
                
    return results


def get_homonym_url(word, num):
    '''
    Return urls of word definitions of a homonym.
    Return False if word is not a homonym.

    ***A word is considered a homonym if it has more than one definition on WordSmyth.
    '''
    url = "https://www.wordsmyth.net/?level=3&ent={}".format(word.replace(' ', '_'))
    #filename = wget.download(url, out='{}.html'.format(uuid.uuid4().hex))
    #page = open(filename).read()
    try:
        #time.sleep(1)
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
            text = ''.join(td.find('a').findAll(text=True, recursive=True))
            href = td.find_all('a', href=True)[0]['href']
            if text == word + num:
                return(href)
            elif text == word and num == "1":
                return(href)

    assert False, "should have returned something"


def urls2(word):
    '''
    Return urls of word definitions of a homonym.
    Return False if word is not a homonym.

    ***A word is considered a homonym if it has more than one definition on WordSmyth.
    '''
    url = "https://www.wordsmyth.net/?level=3&ent={}".format(word.replace(" ", "_"))
    #filename = wget.download(url, out='{}.html'.format(uuid.uuid4().hex))
    #page = open(filename).read()
    #time.sleep(1)
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
            first_word = td.find('a').find(text=True, recursive=False)
            break

    tbody = soup.find('div', class_ = "wordlist").table.tbody
    for td in tbody.find_all('td'):
        if td.find('a'):
            url = td.find('a').get('href')
            def_string = td.find('a').findNext('td').text
            text = ''.join(td.find('a').findAll(text=True, recursive=True)).strip()


            #results.append(text)
            if text[0] != "-" and text[-1] != "-":
                #if text != first_word:
                if True:
                    potential_derived = True
                    
                    reason = "unknown"

                    if text.lower()[0] != text[0]:
                        reason = "capitalization"
                    elif is_participle(def_string):
                        reason = "participle"
                    elif "." in text:
                        reason = "period"

                    results.append((text, url, reason))
            '''
            if td.find('a').find(text=True, recursive=False) == word:
                results.append(td.find('a').get('href'))
            '''
    if potential_derived:
        return results


def definitions(url, pos=False):
    '''
    Return a list of definitions given a WordSmyth url.
    url - WordSmyth url (e.g. "https://www.wordsmyth.net/?level=3&ent=dog")
    '''

    try:
        #time.sleep(1)
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
                if is_participle(def_):
                    full_def = ''.join(tr.find("td", attrs={'class': 'data'}).find_all(text=True, recursive=True))
                    m = re.search(r" of (?:<strong>)?(?:\")?(\w+)(?:\")?(?:</strong>)?", full_def)
                    original_word = m.group(1)
                    if original_word[-1].isnumeric():
                        m = re.match('([A-Za-z]+)([0-9]+)', original_word)
                        original_word = m.group(1)
                        num = m.group(2)
                        url = get_homonym_url(original_word, num)
                    else:
                        url = "https://www.wordsmyth.net/?level=3&ent={}".format(original_word.replace(" ", "_"))
                    defs_ = definitions(url, pos=True)
                    if not defs_:
                        defs_ = {}
                        derived, urls = homonym_urls(original_word)
                        for url in urls:
                            defs_.update(definitions(url, pos=True))
                    for k in defs_.keys():
                        if 'verb' not in k:
                            del defs_[k]
                    defs.update(defs_)
                else: 
                    # update bag with words from definition
                    defs[cur_pos].append(' '.join([t.lower() for t in tokenizer.tokenize(def_)]))

    # remove stopwords
    # bag -= STOPWORDS
    # stem words
    # bag = set([stem(w) for w in bag])

    # remove pos's with empty definition (due to being replaced with participle)
    for pos in defs.keys():
        if not defs[pos]:
            del defs[pos]

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
    #'''
    out1 = open('/u/sasa/sasa/HOMONOMY_POLYSEMY/WORDSMITH2/homonyms.{}.7.txt'.format(letter), 'w')
    out2 = open('/u/sasa/sasa/HOMONOMY_POLYSEMY/WORDSMITH2/non_homonyms.{}.7.txt'.format(letter), 'w')
    out3 = open('/u/sasa/sasa/HOMONOMY_POLYSEMY/WORDSMITH2/derived.{}.7.txt'.format(letter), 'w')
    out4 = open('/u/sasa/sasa/HOMONOMY_POLYSEMY/WORDSMITH2/derived.meta.{}.7.txt'.format(letter), 'w')
    #'''
    #wordlist = sorted(wordlist, reverse=True)
    n = float(len(wordlist))

    for i,word in enumerate(wordlist):

        while word[-1].isdigit():# and len(word) >= 2 and word[-2] == '.':
            word = word[:-1]

        print(word)

        #suffix or prefix
        if word[0] == '-' or word[-1] == '-':

            urls = suffix_urls(word)
            if not urls:
                url_ = "https://www.wordsmyth.net/?level=3&ent={}".format(word)
                try:
                    urls = [definitions(url_, pos=True)]
                except AttributeError:
                    print("Error: ", url)
                    continue

            for url in urls:
                try:
                    defs = definitions(url, pos=True)
                except AttributeError:
                    print("Error: ", url)
                    continue
                if not defs:
                    print("no def [3]: ", word)
                    continue
                out2.write('#{}'.format(word) + '\n') 
                #print('#{}'.format(word)) 
                for pos in defs.keys():
                    for d in defs[pos]:
                        sentence = '{}\t{}\n'.format(pos, d)
                        out2.write(sentence)
                        #print(sentence)
            continue


        if int(round(i / n, 5) * 100000) % 10 == 0:
            print("{}\t{}".format(letter, round(i / n, 2)))
    
        #print(word)         

        '''
        if i < 2774:
            continue
        '''
        '''
        m = re.match('.*([0-9]*)', word)
        if not m:
            continue
        word = m.group(1)
        '''


        result = urls2(word)
        if result:
            # derived form
            #out3.write('\t'.join(w for w in result) + '\n')
            for w,url,reason in result:
                # 1. write to regular file
                #url = "https://www.wordsmyth.net/?level=3&ent={}".format(w)
                defs = definitions(url, pos=True)
                if not defs:
                    print("no def [1]: ", word)
                    continue
                
                out3.write('#{}'.format(w) + '\n') 
                #print('#{}'.format(word)) 
                for pos in defs.keys():
                    for d in defs[pos]:
                        sentence = '{}\t{}\n'.format(pos, d)
                        out3.write(sentence)
                        #print(sentence)

                # 2. (TODO) write to meta file        
                indices = ["participle", "period", "capitalization", "unknown"]
                i = indices.index(reason)
                l = [0, 0, 0, 0]
                l[i] = 1
                out4.write("{}\t{}\t{}\t{}\t{}\n".format(w, *l))
            continue
 
        derived, urls = homonym_urls(word)
        #print(derived, urls)
        if not derived and len(urls) > 1:
            # word is a homonym
            for i,url in enumerate(urls, start=1):
                out1.write('#{}{}'.format(word, i) + '\n')
                #print('#{}.{}'.format(word, i))
                defs = definitions(url, pos=True)
                for pos in defs.keys():
                    for d in defs[pos]:
                        out1.write('{}\t{}\n'.format(pos, d))
                        #print('{}\t{}\n'.format(pos, d))
            continue
        # at this point, only non-homonym, non-derived forms remaining
        url = "https://www.wordsmyth.net/?level=3&ent={}".format(word.replace(" ", "_"))
        defs = definitions(url, pos=True)
        if not defs:
            print("no def [2]: ", word)
            continue
        out2.write('#{}'.format(word) + '\n') 
        #print('#{}'.format(word)) 
        for pos in defs.keys():
            for d in defs[pos]:
                sentence = '{}\t{}\n'.format(pos, d)
                out2.write(sentence)
                #print(sentence)



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

def is_participle(def_string):
    strings = [
        "past tense of",
        "present tense of",
        "past participle of",
        "part participle of",
        "present participle of"
    ]
    for s in strings:
        if s in def_string:
            return True
    return False


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

    #'''
    master_wordlist = open('/u/sasa/sasa/HOMONOMY_POLYSEMY/WORDSMYTH/remaining_words.3.txt').readlines()
    master_wordlist = [w.strip() for w in master_wordlist]
    #get_all_definitions('/u/sasa/sasa/HOMONOMY_POLYSEMY/WORDSMYTH/all_wordsmyth_words.txt')

    alphabet = collections.defaultdict(list)
    for word in master_wordlist:
        alphabet[word[0].upper()].append(word)

    #TODO: remove
    #alphabet = {'A': ["propionic acid"]}
    #print(alphabet.keys())
   
    jobs = []
    '''
    k = 'xxx'
    l = [
        'stole', 'rung', 'wrung', 'cleft', 'flung',
        'undone', 'strapping', 'taxis', 'dove', 'shook',
        'affected', 'bent', 'boxing', 'stove', 'bore',
        'bore', 'fold', 'dug', 'gum', 'bound', 'wound',
        'boring', 'drove', 'rent', 'spoke', 'hiding',
        'tanner', 'strapping', 'smelt', 'peaked', 'slew',
        'rung', 'spat', 'rating', 'undone', 'mat', 'arch',
        'prop', 'sounding', 'flatter', 'lining', 'cottage',
        'stole', 'ground', 'lying', 'meter'
    ]
    '''
    #k = 'xxx'
    #l = ['break even']
    #url = "https://www.wordsmyth.net/?level=3&ent=mummification"
    #result = definitions(url, pos=True)
    #print(result)
    #urls = urls2("break even")
    #print(urls)    

    #print(definitions('-ar'))
    get_all_definitions(master_wordlist, 'XXXX')    
    '''
    for k,l in sorted(alphabet.items(), reverse=True):
        p = multiprocessing.Process(target=get_all_definitions, args=(l,k))
        jobs.append(p)
        p.start()
    #'''

