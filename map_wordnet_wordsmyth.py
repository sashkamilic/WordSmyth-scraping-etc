import nltk
from lxml import html
import os
import xml.etree.ElementTree as ET
import urllib2
from bs4 import BeautifulSoup
from nltk.corpus import stopwords
import wget
import ssl
from nltk.tokenize import RegexpTokenizer
#from nltk.stemmer import PorterStemmer
from stemming.porter2 import stem
from nltk.corpus import wordnet as wn

ssl._create_default_https_context = ssl._create_unverified_context

tokenizer = RegexpTokenizer(r'\w+') # no punctuation

SEMCOR_DIR = '/p/cl/SemCor/semcor3.0/brown1/tagfiles'
OUTDIR = '~/homonymy_polysemy/semcor_convert'

STOPWORDS = frozenset(stopwords.words('english'))


def main():
    # create new directory
    #os.makedirs(OUTDIR)
    # csv fieldnames
    fieldnames = ['word', 'lemma', 'pos', 'is_homonym', 'wn_synset', 'ws_meaning', 'context', 'id']
    #writer.writerow({'first_name': 'Wonderful', 'last_name': 'Spam'})

    for filename in os.listdir(SEMCOR_DIR):
        #outfile = open(os.path.join(OUTDIR, filename + '.tsv'))
        #writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        #writer.writeheader()

        filename = os.path.join(SEMCOR_DIR, filename)
        parsed = html.fromstring(open(filename).read())
        for x in parsed.getiterator():
            '''
            if x.tag == 'p':
                p_curr = x.attrib['pnum']
            elif x.tag == 's':
                s_curr = x.attrib['snum']
            elif x.tag == 'wf' and pos in ['NN', 'VB']:
                row = {}
                row['word'] = x.text.lower()
                row['lemma'] = x.attrib['lemma']
                row['pos'] = x.attrib['pos']
                row['is_homonym'] = False #TODO
                row['wn_synset'] = False #TODO
                row['ws_meaning'] = False #TODO
                row['context'] = False 
 
            # append to curr_sentence
            if x.tag == 'wf':
                sent_curr = False #TODO
            '''
            print(x.tag, x.attrib, x.text, x.tail)

        outfile.close()

def chunk_sentences(f):
    """
    Generator to read SemCor file in sentence chunks.
    """
    # SemCor files have incorrect xml format >:(
    # therefore parsing with html parser
    
    while True:
        # skip lines before paragraph
        line = f.readline()
        while not line.startswith("<p pnum="):
            line = f.readline()
        #while line.strip() != "</s>"


    parsed = html.fromstring(f.read())
    for x in parsed.getiterator():
        if x.tag == 'p':
            p_curr = x.attrib['pnum']
        elif x.tag == 's':
            s_curr = x.attrib['snum']


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

def lexsn_to_synset(lexsn):
    '''
    Convert `lexsn` from SemCor to Synset name
    e.g. '5:00:00:gross:00' -> 'overall.s.02.overall'
    '''
    lemma = lexsn.split('%')[0]
    for ss in wn.synsets(lemma):
        for l in ss.lemmas():
            if l.key() == lexsn:
                return ss

def homonym_urls(word):
    '''
    Return urls of word definitions of a homonym.
    Return False if word is not a homonym.

    ***A word is considered a homonym if it has more than one definition on WordSmyth.
    '''
    url = "https://www.wordsmyth.net/?level=3&ent={}".format(word)
    filename = wget.download(url)
    page = open(filename).read()
    soup = BeautifulSoup(page, 'html.parser')
    os.remove(filename)
    if len(soup.find_all('div', class_ = "more")) == 0:
        return False
    results = []
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
    filename = wget.download(url)
    page = open(filename).read()
    soup = BeautifulSoup(page, 'html.parser')
    # delete file !!!
    os.remove(filename)
    
    bag = set()
    maintable = soup.tbody.find('table', class_="maintable")
    correct_pos = False
    for tr in maintable.tbody.findChildren():

        if tr.get("class") and tr.get("class")[0] == "postitle":
            pos_ = tr.find("td", class_ = "data").a.text
            if pos_ == pos:
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
    #get_wordsmyth_meaning("bank")
    #get_wordsmyth_meaning("dog")
    #print(test2('noun'))
    #print(homonym_urls("dog"))
    #print(homonym_urls("cat"))
    for x in ['charge%1:04:03::', 'election%1:04:01::']:
        print(lexsn_to_synset(x).definition())
        print(homonym_urls(x.split('%')[0]))
