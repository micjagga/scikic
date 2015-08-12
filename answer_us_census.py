import pymc as pm
import numpy as np
import pandas as pd
import re
import json
import urllib
import urllib2
import answer as ans
import os
import zipfile
import sqlite3 as lite
import shapefile
from StringIO import StringIO
from zipfile import ZipFile
import csv
from threading import Thread

#Some helpful functions
def hasNumbers(strings):
    '''Returns true if any of the strings in the 'strings' array have a digit in them.'''
    for s in strings:
        if any(char.isdigit() for char in s):
            return True
    return False

def dict_to_array(data):
    '''Turns a hierarchy of dictionaries into a numpy array
    returns:
        - the numpy array
        - a list of lists of labels (each list records the labels on that dimension)
    example:
        res, labs = dict_to_array({'aged 3-5':{'males':{'rabbits':3,'dogs':4,'cats':1},'females':{'rabbits':3,'dogs':0,'cats':2}},'aged 0-2':{'males':{'rabbits':4,'dogs':2,'cats':1},'females':{'rabbits':1,'dogs':0,'cats':4}}})
        
        res   array([[[1, 4, 2],[4, 1, 0]],[[1, 3, 4],[2, 3, 0]]])
        labs  [['aged 0-2', 'aged 3-5'], ['males', 'females'], ['cats', 'rabbits', 'dogs']]
    '''
    
    res = []
    if not isinstance(data,dict):
        return data, []
    labels = []
    for e in data:        
        if 'Total' not in e:
            lower_dict, lower_labels = dict_to_array(data[e])
            res.append(lower_dict)
            labels.append(e)
    if hasNumbers(labels): #automatically sorts labels containing numbers by the numerical value of the first number.
        numbers = []
        for lab in labels:
            numbers.append(re.search(r'\d+', lab).group())
        numbers, labels, res = (list(t) for t in zip(*sorted(zip(numbers, labels, res))))  
    lower_labels.insert(0,labels)
    return np.array(res), lower_labels



class USCensusAnswer(ans.Answer):
    dataset = 'uscensus';
    _age_range = np.array([4,9,14,17,19,20,21,24,29,34,39,44,49,54,59,61,64,66,69,74,79,84])+1 #added one as the numbers here are the end of each range, not the start of each.
    _states = ['Mo29','Al01','Ak02','Az04','Ar05','Ca06','Co08','Ct09','De10','Dc11','Fl12','Ga13','Hi15','Id16','Il17','In18','Ia19','Ks20','Ky21','La22','Me23','Md24','Ma25','Mi26','Mn27','Ms28','Mt30','Ne31','Nv32','Nh33','Nj34','Nm35','Ny36','Nc37','Nd38','Oh39','Ok40','Or41','Pa42','Ri44','Sc45','Sd46','Tn47','Tx48','Ut49','Vt50','Va51','Wa53','Wv54','Wi55','Wy56']
    def insights(self,inference_result,facts):
        return []

    @classmethod
    def USCensusApiQuery(cls,geoloc,variables):
        """Performs an API query to the US Census database, for the given location and variable 
        (pass state,county,tract and blockgroups as strings and lists, in a list as geoloc)
        (where the last one known should be a list, e.g.):
    - get total population of tracts 000101 and 000102 in county 170, in state 02
        USCensusApiQuery(['02','170',['000101','000102'],None],['B00001_001E'])
    - get total population in state 02
        USCensusApiQuery([['02'],None,None,None],['B00001_001E'])
    - get total population of blockgroup 1 in tract 000101, in county 170, in state 02
        USCensusApiQuery(['02','170','000101',['1']],['B00001_001E']) 
    - get total population of all counties in state 04
        USCensusApiQuery(['04',[],None,None],['B00001_001E']) 
    - get total population of all states
        USCensusApiQuery([[],None,None,None],['B00001_001E']) 
    - get total population and population of males in the US
        USCensusApiQuery([None,None,None,None],['B01001_001E','B01001_002E'])

        pass the list of queries in the second item
        
        #if the last not-none item in the geoloc is an empty list, then we'll return all the items...
        
        #!lengths of strings matter:
         state = 2 chars
         county = 3 chars
         tract = 6 chars
         blockgroup = 1 chars
         TODO Pad with zeros automatically
        """

        pathToServer = 'http://api.census.gov/data/2011';
        apiKey = 'd7814c2f2b9373aea29d9e118cb484f6099dc570';        
        geographicalHierarchy = '2011STATH';
        varlist = ','.join(variables)

        hierarchy = ['us','state', 'county', 'tract', 'block+group']
        hier = -1
        for i,h in enumerate(geoloc):
            if h!=None:
                hier = i
        if hier>3:
            hier = 3
            
        #if:  state,county,tract,blockgroup : hier
        #       x     x      x       x         3
        #       x     x      x      none       3
        #       x     x     none    none       2
        #       x    none   none    none       1
        #     none   none   none    none       0

        
        foritem = hierarchy[hier+1] #the item we put in the 'for' section is the first with a none in (or blockgroup if none have none in).

        inlist = []
        for h in range(hier):
            inlist.append(hierarchy[h+1]+':'+geoloc[h])
        inliststr = '+'.join(inlist)
        if len(inlist)>0:
            inliststr = '&in='+inliststr
        url = '%s/acs5?get=%s&for=%s:*%s&key=%s' % (pathToServer,varlist,foritem,inliststr,apiKey) 
        response = urllib2.urlopen(url);
        json_data = json.loads(response.read())
        data = []
        geos = []
        for place in json_data[1:]: #first item is the table headers
            vals = place[0:len(variables)]
            geo=place[len(variables):]
            if geoloc[hier]==None or (geo[hier] in geoloc[hier]) or geoloc[hier]==[]:
                data.append([int(v) for v in vals])
                geos.append(geo)
        return data,geos

    @classmethod
    def getAgeDist(cls,geoloc,returnList):
        """Gets the age distribution given a particular geographical area"""
        male = ['B01001_003E','B01001_004E','B01001_005E','B01001_006E','B01001_007E','B01001_008E','B01001_009E','B01001_010E','B01001_011E','B01001_012E','B01001_013E','B01001_014E','B01001_015E','B01001_016E','B01001_017E','B01001_018E','B01001_019E','B01001_020E','B01001_021E','B01001_022E','B01001_023E','B01001_024E','B01001_025E']
        female = ['B01001_027E','B01001_028E','B01001_029E','B01001_030E','B01001_031E','B01001_032E','B01001_033E','B01001_034E','B01001_035E','B01001_036E','B01001_037E','B01001_038E','B01001_039E','B01001_040E','B01001_041E','B01001_042E','B01001_043E','B01001_044E','B01001_045E','B01001_046E','B01001_047E','B01001_048E','B01001_049E']
        variables = male[:]
        variables.extend(female)       
        results, geolocs = cls.USCensusApiQuery(geoloc,variables)
        res = []
        for place_result in results:
            res.append(np.vstack([place_result[0:len(male)],place_result[len(male):]]))
        returnList[0] = res

    def __init__(self,name,dataitem,itemdetails,answer=None):
        self.dataitem = dataitem
        self.itemdetails = itemdetails 
        self.featurename = name
        self.answer = answer

    def question_to_text(self):
        return "No questions"
        
    def get_list_of_bgs(self,facts):
        bgs = [[None,None,None,None]] #TODO Confirm this works - should use the whole of the US as the 'bg'
        if 'where' in facts:
            if 'uscensus' in facts['where']:
                bgs = [it['item'] for it in facts['where']['uscensus']] #get the list of OA values
        return bgs

    def get_list_of_bg_probs(self,facts):
        probs = np.array([1.0]) #if we don't know just reply with one.
        if 'where' in facts:
            if 'uscensus' in facts['where']:
                probs = np.array([it['probability'] for it in facts['where']['uscensus']]) #get the list of OA values
        probs = probs/probs.sum() #shouldn't be necessary
        return probs

    def calc_probs_age(self,facts):
        bgs = self.get_list_of_bgs(facts)
        threadData = []
        threads = []
        bgs.append([None,None,None,None]) #Last BG is whole of US
        for bg in bgs:
            data = [0]
            threadData.append(data)
           # bg_geo = bg['item']
            t = Thread(target=USCensusAnswer.getAgeDist,args=(bg,data))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()
        localAgeDists = np.array([td[0] for td in threadData[:-1]])
        nationalAgeDist = np.array(threadData[-1][0])
       

        #we want p(postcode|age), which we assume is equal to p(output area|age)
        #if n = number of people in output area
        #   N = number of people
        #   na = number of people of age a in output area
        #   Na = number of people of age a
        #
        #p(output area|age) = p(age|output area) x p(output area) / p(age)
        #
        #we can write the three terms on the right as:
        #
        #p(age|output area) = na/n
        #p(output area) = n/N
        #p(age) = Na/N
        #
        #substituting in... na/n x n/N / (Na/N) = (na/N) / (Na/N) = na/Na
        #so localAgeDist/nationalAgeDist

        self.age_probs = np.zeros([101,len(localAgeDists),2])


        for i,dist in enumerate(localAgeDists):
            p = (0.0001+dist)/nationalAgeDist
            p = np.sum(p[0],0)
            p = ans.distribute_probs(p,USCensusAnswer._age_range) #spread over our standard age distribution
            self.age_probs[:,i,0] = 1-p
            self.age_probs[:,i,1] = p
            temp = p/np.sum(p)
       
    def get_pymc_function_age(self,features):
        """Returns a function for use with the pyMC module:
        Args:
          features (dictionary): Dictionary of pyMC probability distributions.
        Returns:
          function (@pm.deterministic): outputs probability given the parameters.
        """
        probs = self.age_probs
        @pm.deterministic    
        def givenAge(age=features['factor_age'],bg=features['bg']):
            pAge = probs
            return pAge[age,bg]
        return givenAge
    
    def prob_in_us(self,facts):
        if 'where' in facts:
            if 'country' in facts['where']:
                for con in facts['where']['country']:
                    if con['item'] == 'us':
                        return con['probability']
        return 0 #if it's not been found

    def append_features(self,features,facts): 
        """Alters the features dictionary in place, adds:
         - age
         - gender
         - this instance's feature
         
        Args:
          features (dictionary): Dictionary of pyMC probability distributions.
        
        Raises:
          DuplicateFeatureException: If an identically named feature already exists that clashes with this instance
        """
         #if we're not in the us then we just skip
        if self.prob_in_us(facts)<0.01:
            return

        self.calc_probs_age(facts)
        if not 'factor_age' in features:
            p = np.ones(101) #flat prior, will be unflattened by US stats (TODO confirm)
            p = p/p.sum()
            features['factor_age'] = pm.Categorical('factor_age',p);
        if not 'bg' in features:
            p = self.get_list_of_bg_probs(facts)
            features['bg'] = pm.Categorical('bg',p);
            
        if self.featurename+"_age" in features:
            raise DuplicateFeatureException('The "%s" feature is already in the feature list.' % self.featurename+"_age");
        
        features[self.featurename+"_age"]=pm.Categorical(self.featurename+"_age", self.get_pymc_function_age(features), value=True, observed=True)

    @classmethod
    def pick_question(self,questions_asked,facts,target):
	    return 'None','agegender'

