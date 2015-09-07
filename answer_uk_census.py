import pymc as pm
import numpy as np
import pandas as pd
import re
import xml.etree.ElementTree as ET
import urllib2
import sqlite3
import answer as ans

from StringIO import StringIO
from zipfile import ZipFile
from threading import Thread

import logging
import config
logging.basicConfig(filename=config.loggingFile,level=logging.DEBUG)

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
            digits = re.search(r'\d+', lab)
            if digits!=None:
                digits = digits.group()
            numbers.append(digits)
        numbers, labels, res = (list(t) for t in zip(*sorted(zip(numbers, labels, res))))  
    lower_labels.insert(0,labels)
    return np.array(res), lower_labels








class UKCensusAnswer(ans.Answer):
    """Census answer: handles gender & age, etc"""

    dataset = 'ukcensus';
    religions = ['Christian','Buddhist','Hindu','Jewish','Muslim','Sikh','Other religion','No religion']
    religion_text = ['Christian','Buddhist','Hindu','Jewish','Muslim','Sikh','religious (but I do\'t know which)','of no religion']

    @classmethod
    def metaData(cls):
        data = {'religions':cls.religions,'religion_text':cls.religion_text,'citation':'The <a href="http://www.ons.gov.uk/ons/guide-method/census/2011/census-data/ons-data-explorer--beta-/index.html">UK office of national statistics</a>'}
        return data

    def insights(self,inference_result,facts):
        #returns a list of insights:
        # - inference_result: probability distributions of the features
        # - facts: a dictionary of 'facts' provided by the Answer classes      
        
        insightlist = []
        if 'factor_age' in inference_result:
            msg = 'You are aged between %d and %d.' % (inference_result['factor_age']['quartiles']['lower'],inference_result['factor_age']['quartiles']['upper'])
            insightlist.append(msg)

        if ('factor_gender' in inference_result):
            if (inference_result['factor_gender']['quartiles']['mean']>0.9):
                insightlist.append('You are female')
            elif (inference_result['factor_gender']['quartiles']['mean']<0.1):
                insightlist.append('You are male')
    
    
#0 One family only: Cohabiting couple: All children non-dependent
#1 One family only: Cohabiting couple: Dependent children
#2 One family only: Cohabiting couple: No children <20%
#3 One family only: Lone parent: All children non-dependent
#4 One family only: Lone parent: Dependent children
#5 One family only: Married or same-sex civil partnership couple: All children non-dependent
#6 One family only: Married or same-sex civil partnership couple: Dependent children<<<<<<<<
#7 One family only: Married or same-sex civil partnership couple: No children
#8 One person household: Other <21%
#9 Other household types: With dependent children
#10 One family only: All aged 65 and over
#11 One person household: Aged 65 and over
#12 Other household types: Other (including all full-time students and all aged 65 and over)

        if ('household' in inference_result):
            household = inference_result['household']['distribution']
            nochildren = household[2]+household[7]+household[8]+household[10]+household[11]+household[12]
            if nochildren>0.7:
                insightlist.append("You don't have children living at home")
            if nochildren<0.3:
                insightlist.append("You have children")
            alone = household[3]+household[4]+household[8]+household[11]+household[12]
            if alone<0.3:
                insightlist.append("You are in a relationship and living with your partner/spouse.")
        if ('religion' in inference_result):
            rel = inference_result['religion']['distribution']
            listOfReligions = []
            import numpy as np
            for ratio,name in zip(rel,UKCensusAnswer.religion_text):
                if (ratio>0.17):
                    listOfReligions.append(name)
            if (len(listOfReligions)>1):
                relmsg = ', '.join(listOfReligions[:-1]) + ' or ' + listOfReligions[-1]
            else:
                relmsg = listOfReligions[0]
            insightlist.append(" I think you are " + relmsg + ".")

        return insightlist

    @classmethod
    def ONSapiQuery(cls,geoArea, dataSet):
        """Performs an API query to the ONS database, for the given geo area and dataset
        The data is stored in 'data' and is also converted into an N-dimensional 'matrix' using a hierarchy of dictionaries."""
        pathToONS = 'http://data.ons.gov.uk/ons/api/data/dataset/';
        apiKey = 'cHkIiioOQX';
        geographicalHierarchy = '2011STATH';
        url = ('%s%s/dwn.csv?context=Census&geog=%s&dm/%s=%s&totals=false&apikey=%s' % 
        (pathToONS,dataSet,geographicalHierarchy,geographicalHierarchy,geoArea,apiKey))
        response = urllib2.urlopen(url);
        xml_data = response.read();
        root = ET.fromstring(xml_data);
        href = root[1][0][0].text #TODO: Need to get the path to the href using names not indices.
        url = urllib2.urlopen(href);
        zipfile = ZipFile(StringIO(url.read()))
        for filename in zipfile.namelist():
            if (filename[-3:]=='csv'):
                data = pd.read_csv(zipfile.open(filename),skiprows=np.array(range(8)),skipfooter=1,header=0)


        #Gets it into a N-dimensional hierarchy of dictionaries
        values = data.ix[0,:]
        matrix = {}
        for col,v in zip(data.columns,values):
            c = col.split('~')
            if (len(c)>1):
                temp = matrix
                for ix in range(len(c)):
                    if ('Total' in c[ix]):
                        break
                    if c[ix] in temp:
                        temp = temp[c[ix]]
                    else:
                        if ix==len(c)-1:
                            temp[c[ix]] = v
                        else:
                            temp[c[ix]] = {}
                            temp = temp[c[ix]]
        return data, matrix

    @classmethod
    def getAgeDist(cls,geoArea,returnList):
        """Gets the age distribution given the label of a particular geographical area"""
        data, matrix = cls.ONSapiQuery(geoArea,'QS103EW')        #QS103EW = age by year...
        data = data.T
        popages = data[0].values[3:]
        # return popages
        returnList[0] = popages #now return via the argument so this can be called as a thread

    @classmethod
    def getHouseholdDist(cls,geoArea,returnList):
        """Gets the Household composition by age by sex; given the label of a particular geographical area"""
        data, mat = cls.ONSapiQuery(geoArea,'LC1109EW')
        arr,labs = dict_to_array(mat) #Convert the dictionary hierarchy to a numpy array 
        #for dim in labs:
        #    for i,l in enumerate(dim):
        #        print i,l
        #todo sort...
        #order = [[i for i,l in enumerate(labs[2]) if l==r][0] for r in cls.???] #?
        arr = np.array(arr) #convert to numpy array
        #arr = arr[:,:,order] #put in correct order.
        arr = arr * 1.0
        for x in range(arr.shape[0]):
            for y in range(arr.shape[1]):
                arr[x,y,:] += 1.0
                arr[x,y,:] = 1.0*arr[x,y,:] / np.sum(1.0*arr[x,y,:])
        returnList[0] = arr #now return via the argument so this can be called as a thread

    @classmethod
    def getReligionDist(cls,geoArea,returnList):
        """Gets the religion distribution given the label of a particular geographical area"""
        data,mat = cls.ONSapiQuery(geoArea,'LC2107EW')        #LC2107EW = religion by age, gender, etc
        arr,labs = dict_to_array(mat) #Convert the dictionary hierarchy to a numpy array
        order = [[i for i,l in enumerate(labs[2]) if l==r][0] for r in cls.religions] #sort religion by the order we want it in.
        arr = np.array(arr) #convert to numpy array
        arr = arr[:,:,order] #put religions in correct order.
        arr = arr * 1.0
        for x in range(arr.shape[0]):
            for y in range(arr.shape[1]):
                arr[x,y,:] += 1.0
                arr[x,y,:] = 1.0*arr[x,y,:] / np.sum(1.0*arr[x,y,:])
        #gender is sorted by 'male', 'female', age by numerical-order and religion as specified in the cls.religions vector
        returnList[0] = arr #now return via the argument so this can be called as a thread
    
    def __init__(self,name,dataitem,itemdetails,answer=None):
        """Constructor, instantiate an answer...

        Args:
          name: The name of this feature
          dataitem: 'agegender'
          itemdetails: None
          answer=None
        """
        self.dataitem = dataitem
        self.itemdetails = itemdetails 
        self.featurename = name
        self.answer = answer

    def question_to_text(self):
        return "No questions"
        
    def get_list_of_oas(self,facts):
        oas = ['K04000001'] #if we don't know where we are, just use whole of England and Wales to get a prior.
        if 'where' in facts:
            if 'ukcensus' in facts['where']:
                oas = [it['item'] for it in facts['where']['ukcensus']] #get the list of OA values
        return oas

    def get_list_of_oa_probs(self,facts):
        probs = np.array([1.0]) #if we don't know just reply with one.
        if 'where' in facts:
            if 'ukcensus' in facts['where']:
                probs = np.array([it['probability'] for it in facts['where']['ukcensus']]) #get the list of OA values
        probs = probs/probs.sum() #shouldn't be necessary
        return probs

    def calc_probs_religion(self,facts):
        oas = self.get_list_of_oas(facts)
        threadData = []
        threads = []
        for oa in oas:
            data = [0]
            threadData.append(data)
            t = Thread(target=UKCensusAnswer.getReligionDist,args=(oa,data))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        localDists = [td[0] for td in threadData]

        shape = localDists[0].shape
        self.rel_probs = np.empty((len(localDists),shape[0],shape[1],shape[2]))
        for i,p in enumerate(localDists): 
            self.rel_probs[i,:,:,:] = p

    def calc_probs_household(self,facts):
        oas = self.get_list_of_oas(facts)
        threadData = []
        threads = []
        for oa in oas:
            data = [0]
            threadData.append(data)
            t = Thread(target=UKCensusAnswer.getHouseholdDist,args=(oa,data))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        localDists = [td[0] for td in threadData]

        shape = localDists[0].shape
        self.household_probs = np.empty((len(localDists),shape[0],shape[1],shape[2]))
        for i,p in enumerate(localDists): 
            self.household_probs[i,:,:,:] = p


    def calc_probs_age(self,facts):
        oas = self.get_list_of_oas(facts)
        logging.info('calc_probs_age')
        logging.info('  OAs:')
        for oa in oas:
            logging.info('      %s' % oa)
        threadData = []
        threads = []
        oas.append('K04000001') #last OA is whole of England+Wales
        for oa in oas:
            data = [0]
            threadData.append(data)
            t = Thread(target=UKCensusAnswer.getAgeDist,args=(oa,data))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        localAgeDists = [td[0] for td in threadData[:-1]]
        logging.info('  localAgeDists has %d items' % len(localAgeDists))
        nationalAgeDist = threadData[-1][0]

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

        self.age_probs = np.zeros([101,len(localAgeDists),2]) #age, in or not in the output area
        for i,dist in enumerate(localAgeDists):
            p = (0.0001+dist)/nationalAgeDist
            self.age_probs[:,i,0] = 1-p
            self.age_probs[:,i,1] = p

    def get_pymc_function_age(self,features):
        """Returns a function for use with the pyMC module:
        Args:
          features (dictionary): Dictionary of pyMC probability distributions.
        Returns:
          function (@pm.deterministic): outputs probability given the parameters.
        """
        probs = self.age_probs
        @pm.deterministic    
        def givenAgeGender(age=features['factor_age'],oa=features['oa']):
            pAgeGender = probs
            return pAgeGender[age,oa]
        return givenAgeGender

    def get_pymc_function_religion(self,features):
        probs = self.rel_probs
        @pm.deterministic    
        def givenReligion(age=features['factor_age'],oa=features['oa'],gender=features['factor_gender']):
            pReligion = probs
            #the religion dataset is only split into a few bins of age, so handling that here:
            if (age<16):
                age_p = 0
            elif (age<25):
                age_p = 1
            elif (age<35):
                age_p = 2
            elif (age<50):
                age_p = 3
            elif (age<65):
                age_p = 4
            elif (age<75):
                age_p = 5
            else:
                age_p = 6
            return pReligion[oa,gender,age_p]
        return givenReligion
    
    def get_pymc_function_household(self,features):
        probs = self.household_probs
        @pm.deterministic    
        def givenReligion(age=features['factor_age'],oa=features['oa'],gender=features['factor_gender']):
            pHousehold = probs
            #the household dataset is only split into a few bins of age, so handling that here:
            if (age<16):
                age_p = 0
            elif (age<25):
                age_p = 1
            elif (age<35):
                age_p = 2
            elif (age<50):
                age_p = 3
            else:
                age_p = 4
            return pHousehold[oa,gender,age_p]
        return givenReligion
    

    def prob_in_uk(self,facts):
        if 'where' in facts:
            if 'country' in facts['where']:
                for con in facts['where']['country']:
                    if con['item'] == 'gb':
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

        #if we're not in the uk then we just skip
        if self.prob_in_uk(facts)<0.01:
            logging.info('      probably not in the UK, skipping')
            return

        self.calc_probs_age(facts)
        self.calc_probs_religion(facts)
        self.calc_probs_household(facts)
        if not 'factor_age' in features:
            p = np.ones(101) #flat prior
            p = p/p.sum()
            features['factor_age'] = pm.Categorical('factor_age',p);
        if not 'factor_gender' in features:
            p = np.array([.5,.5]) #approx flat            
            features['factor_gender'] = pm.Categorical('factor_gender',p);
        if not 'oa' in features:
            probs = self.get_list_of_oa_probs(facts)
            features['oa'] = pm.Categorical('oa',probs); #if we don't have the ukcensus array then we just have a probability of one for one output area

        if self.featurename+"_age" in features:
            raise DuplicateFeatureException('The "%s" feature is already in the feature list.' % self.featurename+"_age");
        if "religion" in features:
            raise DuplicateFeatureException('The "%s" feature is already in the feature list.' % "religion");

        features[self.featurename+"_age"]=pm.Categorical(self.featurename+"_age", self.get_pymc_function_age(features), value=True, observed=True)
        features["religion"]=pm.Categorical("religion", self.get_pymc_function_religion(features)) #, value=True, observed=False)
        features["household"]=pm.Categorical("household", self.get_pymc_function_household(features)) #, value=True, observed=False)
 
    @classmethod
    def pick_question(cls,questions_asked,facts,target):
	    return 'None','agegender'



