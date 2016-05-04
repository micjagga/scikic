import pymc as pm
import numpy as np
import pandas as pd
import re
import xml.etree.ElementTree as ET
import urllib2
import sqlite3
import answer as ans
import pickle
import answer as ans
import config
import requests
import json
import logging
logging.basicConfig(filename=config.loggingFile,level=logging.DEBUG)



from StringIO import StringIO
from zipfile import ZipFile

class BabyNamesAnswer(ans.Answer):
    """Babynames answer: produces a probability distribution based on the person's name"""
        #see: http://www.ons.gov.uk/ons/rel/vsob1/baby-names--england-and-wales/1904-1994/index.html for info
    dataset = 'babynames';

    @classmethod
    def init_db(cls):
        pass



    #function to remove duplicates in a list
    @classmethod
    def uniq(cls, seq, idfun=None): 
        # order preserving
        if idfun is None:
            def idfun(x): return x
        seen = {}
        result = []
        for item in seq:
            marker = idfun(item)
            if marker in seen: continue
            seen[marker] = 1
            result.append(item)
        return result

    @classmethod
    def getPriorAgeDist(cls,name,gender,ranks,top):
        temp = [0]


        totpop = 56100000 #Total pop of england+wales (APPROX TODO!)
        years = range(1914,2004,10)
        ps = np.zeros(len(years))
        for yeari,year in enumerate(years):
            r = ranks[gender]
            idxes = r[r[year]==name]
            p = 0
            if not idxes.empty:
                rk = r[r[year]==name].index[0]
                p = 1.*top[gender][rk-1]/(totpop/2) #roughly half of the same gender
            ps[yeari] = p+0.000000001
     #   ps = ps / sum(ps)
        return years,ps

    @classmethod
    def setup(cls,pathToData):
        """Creates files, downloads data, and populates the datafiles"""

        import os
        if (os.path.isfile(pathToData+"names.p")):
            print "File 'names.p' found (setup already complete)"
            return

        #There are three sets of data that are used
        #- historic ranks of the top 100 names for each decade
        #- recent counts of names for each year (since 1996)
        #- contractions of people's names (from wikipedia)

        #1. download historic data and put into a pandas dataframe
        print "Downloading historic dataset"
        url = 'http://www.ons.gov.uk/ons/rel/vsob1/baby-names--england-and-wales/1904-1994/top-100-baby-names-historical-data.xls'
        #REPLACING THE URLLIB2 CALL WITH REQUESTS, AS URLLIB2 DOESN'T SEEM TO BE ABLE TO DO REDIRECTS
        #socket = urllib2.urlopen(url)
        #xd = pd.ExcelFile(socket)
        r = requests.get(url,stream=True)
        handle = open('/tmp/top-100-baby-names-historical-data.xls', 'wb')
        for block in r.iter_content(1024):
            handle.write(block)
        handle.close()
        xd = pd.ExcelFile('/tmp/top-100-baby-names-historical-data.xls')

        ranks = {}
        ranks['boys'] = xd.parse(sheetname='Boys',header=0,skiprows=[0,1,2,4],skip_footer=2,index_col=0)
        ranks['girls'] = xd.parse(sheetname='Girls',header=0,skiprows=[0,1,2,4],skip_footer=2,index_col=0)
        #2. download recent data and put into pandas DF (requires construction of new headers)
        print "Downloading recent dataset"
        url = 'http://www.ons.gov.uk/ons/about-ons/business-transparency/freedom-of-information/what-can-i-request/published-ad-hoc-data/pop/august-2014/baby-names-1996-2013.xls'
        #socket = urllib2.urlopen(url)
        #xd = pd.ExcelFile(socket)
        r = requests.get(url,stream=True)
        handle = open('/tmp/baby-names-1996-2013.xls', 'wb')
        for block in r.iter_content(1024):
            handle.write(block)
        handle.close()
        xd = pd.ExcelFile('/tmp/baby-names-1996-2013.xls')



        sheet = {}
        sheet['boys'] = xd.parse(sheetname='Boys',skiprows=4, index_col=0,skip_footer=3,na_values=':')
        sheet['girls'] = xd.parse(sheetname='Girls',skiprows=4, index_col=0,skip_footer=3,na_values=':')

        print "(adjusting dataset)"
        for gender in sheet:
            sheet[gender] = sheet[gender].ix[1:]
            df = sheet[gender]
            year = 2013
            rankCol = True
            cols = []
            for i,c in enumerate(df.columns):
                if (rankCol):
                    cols.append("%dRank" % year)
                else:
                    cols.append("%dCount" % year)
                    year-=1
                rankCol = not rankCol
            df.columns = cols

        #3. Combine all this and put into a datastructure
        # we assume that the proportion of names at each rank are the same for all years prior to 1996
        print "Integrating datasets"
        top = {}
        q = {}
        for sid in sheet:
            print "(sorting %s)" % sid
            s = sheet[sid]
            q[sid]=s.sort('1996Rank')
            top[sid] = q[sid]['1996Count'][0:100]

        #get list of all names
        print "(calculating list of all names)"
        allnames = {}
        for gender in ranks:
            print "  (%s)" % gender
            allnames[gender] = []
            for year in ranks[gender]:
                r = ranks[gender][year]
                allnames[gender].extend(r.values)

        #4. get a list of all names, without duplicates
        print "Removing duplicates"
        allnames['boys'] = cls.uniq(allnames['boys'])
        allnames['girls'] = cls.uniq(allnames['girls'])

        #5. add results to 'results' structure
        results = {}
        for gender in ['boys','girls']:
            print "Adding %s to results" % gender
            results[gender] = {}
            for name in allnames[gender]:
                years,ps = cls.getPriorAgeDist(name,gender,ranks,top)
                results[gender][name] = ps

        #6. save results in names.p
        print "Saving results"
        results['years'] = years
        pickle.dump( results, open( pathToData+"names.p", "wb" ) )

        #7. We also need to know how people shorten their names
        #Download and scrape the wikipedia page of people's shortened names
        print "Querying wikipedia for name contractions"
        response = urllib2.urlopen('http://en.wiktionary.org/wiki/Appendix:English_given_names')
        html = response.read()

        p = re.compile('<li><a.*title.*>([A-Za-z]*)</a>[ -]*(([A-Za-z]+, )+)([A-Za-z]+)</li>')
        ms = p.findall(html)

        contractions = {}
        for m in ms:
            for name in m[1:]:
                for ns in name.split(','):
                    if len(ns)<2:
                        continue
                    if ns in contractions:
                        contractions[ns.upper()].append(m[0].upper())
                    else:
                        contractions[ns.upper()]=[m[0].upper()]

        #8. Save in contractions.p
        print "Saving contractions"
        pickle.dump( contractions, open(pathToData+"contractions.p", "wb"))

    def __init__(self,name,dataitem,itemdetails,answer=None):
        """Constructor, instantiate an answer associated with the name of the individual

        Args:
          name: The name of this feature
          dataitem: Can be name...but not really used.
          itemdetails: Details about the item, not really used.
          answer (default None): The name of the person
        """
        logging.info('Instantiating babynames')
        self.dataitem = dataitem
        self.itemdetails = itemdetails
        self.featurename = 'first_name' #overridden
        self.answer = answer

    def insights(self,inference_result,facts):
        #returns a dictionary of insights:
        # - inference_result: probability distributions of the features
        # - facts: a dictionary of 'facts' provided by the Answer classes
    #    female = self.probs[:,1,1]
    #    male = self.probs[:,1,1]
    #    male[:,1,1].argmax()
        if 'first_name' in facts:
            name = facts['first_name']
            insights = {} 
            insights['babynames_name'] = "You're called %s" % name
            ages = self.probs[:,0,1]+self.probs[:,1,1]
            cum_ps = np.cumsum(ages)/np.sum(ages)
            insights['babynames_age'] = 'People with your name are mostly aged between %d and %d' % (sum(cum_ps<0.1), sum(cum_ps<0.9))
            ps = ages/np.sum(ages)
            maxage = 2015-np.argmax(ps);
            insights['babynames_pop'] = 'Your name was most popular in about %d' % maxage
            return insights
        else:
            return {}
        

    def question_to_text(self):
        if (self.dataitem=='name'):
            return {'question':"What's your name?",'type':'text'} #"What's your name?"#TODO We don't need to ask a question, get it from Facts dictionary.
        return "No question."

    @classmethod
    def pick_question(self,questions_asked,facts,target):
    #return 'name', '' #could return None,None in future, depending on if we get name from facebook
        return 'None', 'None'#None string used to help database

    def calc_probs(self):
        self.probs = np.zeros([101,2,2]) #age, gender(M,F), for and not for the person's name
        nameps = pickle.load( open( config.pathToData+"names.p", "rb" ) )
        years = nameps['years']
        ages = [2015-y for y in years] #todo use current year
        if self.answer == None:
            ans_given = 'None' #this won't be found and the default prior will be used instead
        else:
            ans_given = self.answer
        contractions = pickle.load( open( config.pathToData + "contractions.p", "rb" ) )

#        ans_given = 'rachel'
        if ans_given.upper() in contractions:
            possible_name_list = contractions[ans_given.upper()];
        else:
            possible_name_list = [ans_given.upper()]

        nameused = possible_name_list[0]#in future could search/integrate over.
 #       print "(using name %s)" % nameused
        if (nameused in nameps['boys']):
            p_male = nameps['boys'][nameused]
        else:
            p_male = np.ones(len(years))*0.00000001 #todo: what if their name isn't in the list?
        if (nameused in nameps['girls']):
            p_female = nameps['girls'][nameused]
        else:
            p_female = np.ones(len(years))*0.00000001 #TODO

        p_male = p_male[-1:0:-1]
        p_female = p_female[-1:0:-1]
        ages = ages[-1:0:-1]
        p_male = np.hstack([p_male,p_male[-1]])
        p_female = np.hstack([p_female,p_female[-1]])
        ages.append(101) #add last boundary

        p_male = ans.distribute_probs(p_male,ages)
        p_female = ans.distribute_probs(p_female,ages)
        
        
        
        self.probs = np.zeros([101,2,2])
        self.probs[:,0,1] = p_male#*5000
        self.probs[:,0,0] = 1-p_male#*5000
        self.probs[:,1,1] = p_female#*5000
        self.probs[:,1,0] = 1-p_female#*5000
        
        logging.info('***************************************')
        logging.info(self.probs)
        logging.info('***************************************')
        
        
    def get_pymc_function(self,features):
        """Returns a function for use with the pyMC module:
          - p(name|age,gender)
          - ...
        Args:
          features (dictionary): Dictionary of pyMC probability distributions.
        Returns:
          function (@pm.deterministic): outputs probability given the parameters.
        """
        ##TODO HANDLE OF self.answer IS NONE
        self.calc_probs()
        probs = self.probs
        @pm.deterministic    
        def seenGivenAgeGender(age=features['factor_age'], gender=features['factor_gender']):
            p = probs
            return p[age][gender]
        return seenGivenAgeGender
    
    def append_features(self,features,facts,relationships,descriptions):
        """Alters the features dictionary in place, adds:
         - age
         - gender
         - this instance's feature
         
        Args:
          features (dictionary): Dictionary of pyMC probability distributions.
          facts (dictionary): should already be populated with facts
        
        Raises:
          DuplicateFeatureException: If an identically named feature already exists that clashes with this instance
        """
        #age: 0-100
        
        if 'first_name' not in facts: #we don't know their first name
            return
        logging.info('Appending babynames features')
        if 'first_name' in facts:
            self.answer = facts['first_name']
        else:
            self.answer = None
        if not 'factor_age' in features:
            p = np.ones(101) #flat prior
            p = p/p.sum()
            features['factor_age'] = pm.Categorical('factor_age',p);
        if not 'factor_gender' in features:
            #flat prior
            features['factor_gender'] = pm.Categorical('factor_gender',np.array([0.5,0.5]));
        if self.featurename in features:
            raise DuplicateFeatureException('The "%s" feature is already in the feature list.' % self.featurename);
        features[self.featurename]=pm.Categorical(self.featurename, self.get_pymc_function(features), value=True, observed=True)

        relationships.append({'parent':'factor_gender', 'child':'first_name'})
        relationships.append({'parent':'factor_age', 'child':'first_name'})

    @classmethod
    def metaData(cls):
        return {'citation':'The ONS provide statistics on the distribution of the names of baby\'s in the UK: <a href="http://www.ons.gov.uk/ons/about-ons/business-transparency/freedom-of-information/what-can-i-request/published-ad-hoc-data/pop/august-2014/baby-names-1996-2013.xls">1996-2013</a> and <a href="http://www.ons.gov.uk/ons/rel/vsob1/baby-names--england-and-wales/1904-1994/top-100-baby-names-historical-data.xls">1904-1994</a>.'}

