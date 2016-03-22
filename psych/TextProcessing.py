
import csv


from numpy import log2
from nltk import *
from happierfuntokenizing_p2 import *
from langdetect import detect



class TextProcessing(object):
    """
    Text related processing
    """
    
    def __init__(self):
        word_dic_path = """./dic/dic_word.csv"""
        topic_dic_path = """./dic/dic_topic.csv"""
        self.topic_num = 2000
        
        self.word_dic = self.loadDic(word_dic_path, 'word')
        self.topic_dic = self.loadDic(topic_dic_path, 'topic')


    def extractFeature(self, text, extractWord=True, extractTopic=True):
        """ extract words and topics frequency feature from text.
        Parameters
        ----------
        X: text needs to be processed. Can be a str or a list of str
        
        Returns
        -------
        fea : list
            Returns the words and topic frequency.
        """
        
        words = []
        bi_grams = []
        tri_grams = []
        tok = Tokenizer(preserve_case=False)
        
        if isinstance(text,str):
            text_temp = []
            text_temp.append(text)
            text = text_temp
        
        # text is a list of sentences, then process it sentence by sentence
        for s in text:
            sentence = self.removeNonAscii(s)
            sentence = self.shrinkSpace(sentence)
            w = list(tok.tokenize(sentence))  # single word 
            words = words + w      
            bi_grams = bi_grams + list(bigrams(w)) # two words
            tri_grams = tri_grams + list(trigrams(w)) # three words
            

        word_freqs =  FreqDist(words)
        N = word_freqs.N() # total number of words
        ngrams_freqs = FreqDist(bi_grams) + FreqDist(tri_grams) 
        all_freqs = {}
        for n in ngrams_freqs.keys():
            all_freqs[' '.join(n)] = ngrams_freqs[n]
        for n in word_freqs:
            all_freqs[n] = word_freqs[n]

        # words
        if extractWord is True:
            fea_word = []
            dic_freqs = OrderedDict()
            for d in self.word_dic:    
                if d in all_freqs.keys():
                    dic_freqs[d] = float(all_freqs[d]) / N
                else:
                    dic_freqs[d] = 0
            fea_word = list(dic_freqs.values())
            
        # topic
        if extractTopic is True:
            fea_topic = []
            for i in range(0, len(self.topic_dic)):
                p = 0
                for item in self.topic_dic[i]:
                    p = p + item[2] * (float(word_freqs[item[0]])/N)
                fea_topic.append(p)
            fea_topic = list(fea_topic)
        
        fea = fea_word + fea_topic
        return fea
    
    def loadDic(self, path, dicType):
        """ load the dictionary for feature extraction.
        Parameters
        ----------
        path: the path of the dictionary
        dicType: dictionary type: word, topic
        
        Returns
        -------
        dic : list
            Returns the dictionary.
        """
        dic = []
        if dicType == 'word':
            with open(path) as f:
                f_csv = csv.reader(f)
                for row in f_csv:   
                    dic.append(row[0])
            dic = sorted(dic)
            
        if dicType == 'topic':
            dic = [[] for i in range(self.topic_num)]
            with open(path) as f:
                f_csv = csv.reader(f)
                for row in f_csv:
                    dic[int(row[1])].append((row[0], int(row[1]), int(row[2])))
        return dic
    
 
    def languageDetection(self, s):
        """ detect the language in string s """
        lan = detect(s)
        return lan
        
        
    def removeNonAscii(self,s): 
        """ remove non-ascii characters from text"""
        
        newlines = re.compile(r'\s*\n\s*')
        newlines = re.compile(r'\s*\n\s*')
        s = newlines.sub(' <NEWLINE> ',s)
        if s:
            return "".join(i for i in s if (ord(i)<128 and ord(i)>20))
        return ''

    def shrinkSpace(self,s):
        """ reduce the blank space from text"""
        
        multSpace = re.compile(r'\s\s+')
        startSpace = re.compile(r'^\s+')
        endSpace = re.compile(r'\s+$')
        multDots = re.compile(r'\.\.\.\.\.+') #more than four periods
        newlines = re.compile(r'\s*\n\s*')
        """turns multipel spaces into 1"""
        s = multSpace.sub(' ',s)
        s = multDots.sub('....',s)
        s = endSpace.sub('',s)
        s = startSpace.sub('',s)
        s = newlines.sub(' <NEWLINE> ',s)
        return s
    
     
    
 