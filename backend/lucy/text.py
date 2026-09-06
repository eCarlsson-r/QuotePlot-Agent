import re
import operator
import urllib
import math

_step2list = {
              "ational": "ate",
              "tional": "tion",
              "enci": "ence",
              "anci": "ance",
              "izer": "ize",
              "bli": "ble",
              "alli": "al",
              "entli": "ent",
              "eli": "e",
              "ousli": "ous",
              "ization": "ize",
              "ation": "ate",
              "ator": "ate",
              "alism": "al",
              "iveness": "ive",
              "fulness": "ful",
              "ousness": "ous",
              "aliti": "al",
              "iviti": "ive",
              "biliti": "ble",
              "logi": "log",
              }

_step3list = {
              "icate": "ic",
              "ative": "",
              "alize": "al",
              "iciti": "ic",
              "ical": "ic",
              "ful": "",
              "ness": "",
              }

_cons = "[^aeiou]"
_vowel = "[aeiouy]"
_cons_seq = "[^aeiouy]+"
_vowel_seq = "[aeiou]+"

# m > 0
_mgr0 = re.compile("^(" + _cons_seq + ")?" + _vowel_seq + _cons_seq)
# m == 0
_meq1 = re.compile("^(" + _cons_seq + ")?" + _vowel_seq + _cons_seq + "(" + _vowel_seq + ")?$")
# m > 1
_mgr1 = re.compile("^(" + _cons_seq + ")?" + _vowel_seq + _cons_seq + _vowel_seq + _cons_seq)
# vowel in stem
_s_v = re.compile("^(" + _cons_seq + ")?" + _vowel)
# ???
_c_v = re.compile("^" + _cons_seq + _vowel + "[^aeiouwxy]$")

# Patterns used in the rules

_ed_ing = re.compile("^(.*)(ed|ing)$")
_at_bl_iz = re.compile("(at|bl|iz)$")
_step1b = re.compile("([^aeiouylsz])\\1$")
_step2 = re.compile("^(.+?)(ational|tional|enci|anci|izer|bli|alli|entli|eli|ousli|ization|ation|ator|alism|iveness|fulness|ousness|aliti|iviti|biliti|logi)$")
_step3 = re.compile("^(.+?)(icate|ative|alize|iciti|ical|ful|ness)$")
_step4_1 = re.compile("^(.+?)(al|ance|ence|er|ic|able|ible|ant|ement|ment|ent|ou|ism|ate|iti|ous|ive|ize)$")
_step4_2 = re.compile("^(.+?)(s|t)(ion)$")
_step5 = re.compile("^(.+?)e$")

# Stemming function

def stem(w):
    """Uses the Porter stemming algorithm to remove suffixes from English
    words.

    >>> stem("fundamentally")
    "fundament"
    """

    if len(w) < 3: return w

    first_is_y = w[0] == "y"
    if first_is_y:
        w = "Y" + w[1:]

    # Step 1a
    if w.endswith("s"):
        if w.endswith("sses"):
            w = w[:-2]
        elif w.endswith("ies"):
            w = w[:-2]
        elif w[-2] != "s":
            w = w[:-1]

    # Step 1b

    if w.endswith("eed"):
        s = w[:-3]
        if _mgr0.match(s):
            w = w[:-1]
    else:
        m = _ed_ing.match(w)
        if m:
            stem = m.group(1)
            if _s_v.match(stem):
                w = stem
                if _at_bl_iz.match(w):
                    w += "e"
                elif _step1b.match(w):
                    w = w[:-1]
                elif _c_v.match(w):
                    w += "e"

    # Step 1c

    if w.endswith("y"):
        stem = w[:-1]
        if _s_v.match(stem):
            w = stem + "i"

    # Step 2

    m = _step2.match(w)
    if m:
        stem = m.group(1)
        suffix = m.group(2)
        if _mgr0.match(stem):
            w = stem + _step2list[suffix]

    # Step 3

    m = _step3.match(w)
    if m:
        stem = m.group(1)
        suffix = m.group(2)
        if _mgr0.match(stem):
            w = stem + _step3list[suffix]

    # Step 4

    m = _step4_1.match(w)
    if m:
        stem = m.group(1)
        if _mgr1.match(stem):
            w = stem
    else:
        m = _step4_2.match(w)
        if m:
            stem = m.group(1) + m.group(2)
            if _mgr1.match(stem):
                w = stem

    # Step 5

    m = _step5.match(w)
    if m:
        stem = m.group(1)
        if _mgr1.match(stem) or (_meq1.match(stem) and not _c_v.match(stem)):
            w = stem

    if w.endswith("ll") and _mgr1.match(w):
        w = w[:-1]

    if first_is_y:
        w = "y" + w[1:]

    return w

def cleantext(string):
    string = re.sub('[^a-zA-Z]', ' ', string)

    #Remove @, # and https:// from tweets
    new_string = ''
    for i in string.split():
        s, n, p, pa, q, f = urllib.parse.urlparse(i)
        if s and n:
            pass
        elif i[:1] == '@':
            pass
        elif i[:1] == '.':
            pass
        elif len(i) <= 1:
            pass
        elif i[:1] == '!':
            new_string = new_string.strip() + ' ' + i[1:]
        else:
            new_string = new_string.strip() + ' ' + i
    return new_string

def genvocabFromStringList(stringlist, dfthreshould = 3, stopword = []):
    # stopword
    #sword = []; # ['instagram', 'rt', 'but', 'up', 'their', 'if', 'no', 'not', 'see', 'some', 'make', 'don', 'williemonroejr', 'avaknightbox', 'ha', 'who', 'hi', 'got', 'back', 'who', 'or', 'come', 'think', 're', 'man', 'never', 'callumtheon', 'done', 'much', 'would', 'off', 'big', 'them', 'wait', 'after', 'still', 'keep', 'their', 'down', 'should', 'even',  'there', 'thing', 'if' 'get', 'on', 'get', 'like', 'more',  'this', 'that', 'thank', 'about',  'what', 'have', 'ar', 'we', 'via', 'and', 'do', 'us', 'so', 'great', 'all', 'just', 'look', 'not', 'now', 'how', 'good', 'go', 'not', 'an', 'here',   'in', 'can', 'for', 'our', 'out', 'thi', 'it', 'my', 'to', 'you', 'me', 'http','com','the','at','of', 'instagram', 'him', 'her', 'co', 'RT', 'is', 'with', 'your', 'from', 'by', 'be', 'new', 'with', 'on']

    vocab = dict()
    vocab_df = dict()
    for text in stringlist:
        text = text.lower()
        text = cleantext(text)

        #segment words
        wordlist = re.split(' |,.',text)
        ddf = dict()
        for word in wordlist:
            word = word.strip()

            # stem words using porter stemmer #Skip for now
            word = stem(word)

            if len(word) == 0 or word in stopword:
                continue

            # add each word to vocabulary dictionary incrementing the counter
            ddf[word] = 1
            if word in vocab:
                vocab[word] += 1
            else:
                vocab[word] = 1

        # increment df
        for k,v in ddf.iteritems():
            if k in vocab_df:
                vocab_df[k] += 1
            else:
                vocab_df[k]=1

    # Sort vocabulary, and remove words
    vocab = sorted(vocab.items(), key=operator.itemgetter(1)) # vocab is an array [[key,freq],....]

    # Remove word under df treshold
    vocab2 = []  # terms
    vocab2f = [] # total frequency
    vocab2idf = [] # idf
    N = len(stringlist) # total number of documents in the corpus
    for i in range(len(vocab)): #item in vocab: # item is [key,freq]
        word = vocab[i][0]
        tf = vocab[i][1]
        df = vocab_df[word]
        if df >= dfthreshould:
            vocab2.append(word)
            vocab2f.append(tf)  # total frequency
            vocab2idf.append(N/(1+df))  # idf

    return [vocab2, vocab2f, vocab2idf]

def saveVocab(fileName, vocab2, vocab2f, vocab2idf):
    # save vocabulary
    ffile = open(fileName, "w")
    for i in range(len(vocab2)):
        word = vocab2[i]
        f = vocab2f[i]
        idf = vocab2idf[i]
        ffile.write(word+','+str(f)+','+str(idf)+'\n')
    ffile.close()

def genvocabFromFileList(filelistFileName, df = 3, stopword = []):
    # Read file list
    flist = open(filelistFileName, "r")

    # For each file
    filename = flist.readline()
    filename = filename.strip()

    stringlist = []
    while filename:
        print(filename)

        ftext = open(filename, "r")
        text = ftext.read().lower()

        stringlist.append(text)

        filename = flist.readline()
        filename = filename.strip()
    flist.close()

    return genvocabFromStringList(stringlist, df, stopword)

def readvocab(vocabFileName):
    # read vocab
    vfile = open(vocabFileName, "r")

    vocab = []
    vocabf = []
    vocabidf = []

    vword = vfile.readline()
    vword = vword.strip()
    while vword:
        vword = vword.split(',')
        vocab.append(vword[0])
        vocabf.append(int(vword[1]))
        vocabidf.append(int(vword[2]))
        vword = vfile.readline()
        vword = vword.strip()
    return [vocab, vocabf, vocabidf]  # list

def genfeatureVectorFromString(text, vocab, vocabidf):
    text = cleantext(text) # get the third field and clean

    #segment text into words
    wordlist = re.split(' |,',text)

    #add the words to the tf counter
    feature = dict()
    for word in wordlist:
        # stem word using porter stemmer #Skip for now
        word = stem(word)

        # if the word is in vocab, increment counter
        if word in vocab:
            if word in feature:
                feature[word] = feature[word] + 1
            else:
                feature[word] = 1

    fv = []
    for i in range(len(vocab)):
        word = vocab[i]
        if word in feature:
            v = feature[word]
        else:
            v = 0

        v = v * math.log10(vocabidf[i])  # Using tf x log(N/(1+d))
        fv.append(v)
    return fv # list

def genfeaturesFromList(stringlist, vocab, vocabidf):
    features = []
    for text in stringlist:
        fv = genfeatureVectorFromString(text, vocab, vocabidf)
        features.append(fv)

    return features # list of list

def saveFeatures(featureFileName, vocab, features, y):
    #print feature

    # save feature as csv file
    ffile = open(featureFileName, "w")

    # write the heading
    n = 0
    if y is not None:
        ffile.write("class")
        n += 1
    for item in vocab:
        if n == 0:
            ffile.write(str(item))
        else:
            ffile.write("," + str(item))
        n += 1
    ffile.write("\n")

    fn = 0
    for feature in features:
        n = 0
        if y is not None:
            ffile.write(str(y[fn]))
            n += 1
        for f in feature:
            if n == 0:
                ffile.write(str(f))
            else:
                ffile.write("," + str(f))
            n += 1
        ffile.write("\n")
        fn += 1
    ffile.close()

def saveWordleFile(featureFileName, vocab, features):
    wfile = open(featureFileName, "w")

    for feature in features:
        tn = 0
        for f in feature:
            if f > 0:
                for i in range(f):
                    wfile.write(str(vocab[tn])+",")
            tn += 1
    wfile.close()

def genfeaturesFromFileList(fileListFileName, vocab, vocabidf):

    # Read file list
    flist = open(fileListFileName, "r")

    # For each file
    filename = flist.readline()
    filename = filename.strip()

    stringlist = []
    while filename:
        #read a file for a user
        ftext = open(filename, "r")
        text = ftext.read()
        stringlist.append(text)

        filename = flist.readline()
        filename = filename.strip()

    flist.close()

    return genfeaturesFromList(stringlist, vocab, vocabidf)

def readLabelledTextLines(fileName):
    tlist = open(fileName, "r")

    # For each file
    line = tlist.readline()
    line = line.strip()

    stringlist = []
    y = []
    while line:
        y.append(line[:1])
        stringlist.append(line[2:])

        line = tlist.readline()
        line = line.strip()

    tlist.close()
    return [stringlist, y]
#--------------------------------------------
