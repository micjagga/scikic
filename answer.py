import pymc as pm
import numpy as np
import pandas as pd
import re
import xml.etree.ElementTree as ET
import urllib2
import sqlite3

class DuplicateFeatureException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class Answer(object):
    """Base class for the possible types of data and answers given
    
    Important Note:
      The features need to be compatible between different class types and instances.
      Any new features need to have their structure documented to ensure compatibility.
      
    Important Note:
      Some features are factors and cannot be on the left of a conditional probability:
      p(A|B,C) #if A is a factor this is invalid.
      The features in this set are indicated by being prefixed with factor_.
      
      Maybe: a prior on that feature could be added to a FeaturePriorAnswers class?
      
    Some Feature Descriptions:
      factor_age - a categorical list of ages of 100 values, from 0 to 100.
         each value is that person's age, so 32 means their age is 32<=a<33.
         the last value means 100 or more.
      factor_gender - a categorical list of two values (male or female)
      seen - whether a film's been seen (true or false)
      rating - the integer rating given to a film (between 0 and 5).

    Fact Descriptions:
      where_history
        error - optional, equals a string identifying the problem (can be 'no_fb_likes', 'no_fb_countries', ..)
        countrylist - optional, a list of tuple-pairs of (country-name, date), where date is the date the person started living there
        citylist - not yet implemented, a list of tuple-pairs of ((city, country), date) where date is as above

      where
        city - a list of dictionaries:
          probability - the probability of being in this city
          item - the (city, country) pair
        country - a list of dictionaries: 
          probability - the probability of being in this country
          item - the country (whole name) TODO Might be better to use country codes or something similar
        uscensus - a list of dictionaries. Each dictionary consists of:
          probability - the probability of the person being in this blockgroup
          level - the geographical level that this item consists of (e.g. blockgroup is what I'm using at the moment)
          item - the id of the blockgroup (or other level)
        ukcensus - a list of dictionaries. Each dictionary consists of:
          probability - the probability of the person being in this Output Area
          level - the geographical level that this item consists of (e.g. oa - output area)
          item - the id of the OA
    """

    @classmethod
    def init_db(cls):
        """Initialises database connection, etc"""
        pass

    @classmethod
    def setup(cls,pathToData):
        """Creates databases and files, downloads data, and populates the datafiles"""
        pass

    def __init__(self,name,dataitem,detail,answer=None):
        """Constructor method for base class: does nothing."""
        pass
    
    dataset = 'None'; #override this property with the name of your dataset

    def question_to_text(self):
        return {"question":"Base class, no question.",'type':'none'}
#The first item is the string of the question, the second item describes what type of question (select, text)
    
    def get_pymc_function(self,features):
        """Returns a function for use with the pyMC module, using the
        features held in the 'features' dictionary.

        Note:
          Only features with relevant dependencies will actually be used.

        Args:
          features (dictionary): Dictionary of pyMC probability distributions.
        
        Returns:
          function (@pm.deterministic): outputs some probability given the parameters.
        """
        pass
    
    def append_facts(self,facts,all_answers):
        """Alters the facts dictionary in place, adding facts associated with
        this instance.

        Args:
          facts (dictionary): Dictionary of facts.
          all_answers: array of all the instantiated answers so far.
		THIS PARAMETER IS DEPRECATED AND WILL IN THE FUTURE BE REMOVED
        
        Returns:
          Nothing - the dictionary is altered inplace.
          
        Raises:
          DuplicateFeatureException: If an identically named fact already exists that clashes with this instance
        """
        pass
    
    def append_features(self,features,facts):
        """Alters the features dictionary in place, adding features associated with
        this instance.

        Note:
          Two types of features will be added;
           - parents: features that this distribution uses (i.e. on the right of the |)
           - this node: a feature describing the output of this node, for example whether
             they've seen a movie, have search for 'trains' on google, have a particular
             SNP, etc.

        Args:
          features (dictionary): Dictionary of pyMC probability distributions.
          facts (dictionary): should already be populated with facts

        Returns:
          Nothing - the dictionary is altered inplace.
          
        Raises:
          DuplicateFeatureException: If an identically named feature already exists that clashes with this instance
        """
        pass

    def insights(self,inference_result,facts):        
        #returns a dictionary of insight strings.
	#parameters:
        # - inference_result: probability distributions of the features
        # - facts: a dictionary of 'facts' provided by the Answer classes        
        return {}
    
    @classmethod
    def metaData(cls):
        #Returns a dictionary of metadata info and citations or references, for the sources of the data or questions, etc.
        return {}

    @classmethod
    def pick_question(cls,questions_asked,facts,target):
        return 'None', 'None'
#None = no question to ask the user, but we still want to call it before inference
#Skip = no question to ask user, and we want to skip it when calling inference: It gets called separately (e.g. when jquery gets facebook info, etc)
#Nones are not handled well when put into the database, using string instead.
#the second field is for the detail of the question (e.g. the id of the movie, etc).

#TODO: Not currently used - delete?
    @classmethod
    def process_answer(cls, dataitem, detail, answer):
    #TODO: DEPRECATED: This function is no longer needed
    #instead classes add details to the facts dictionary
    #
    #This function may alter an answer or the details of
    #the question to provide additional information, or
    #reformat it into a standard format.
        return answer, detail;

#helper functions

def distribute_probs(p,j,spread=False): 
    """Distributes age probabilities.
    
    Distributes discrete age probabilities over the "more" continuous
    range from 0 to 100.
    
    Args:
        p - numpy array of probabilities (doesn't need to be normalised)
        j - numpy array of where the boundaries are. It is assumed the first value is from 0
            for example j=np.array([16,25,50]) will have four probabilities associated:
            between 0-15, 16-24, 25-49, 50+
	spread - default False. In the case where you're spreading the values over
	    p(r|0<a<10) where a is the parameter, into, e.g. p(r=4|a) we can say that
	    p(r|a=4) = p(r|0<a<10) [set it to FALSE], unless we know something else.
          however...
	    if we're spreading p(0<a<10|r), then the probabilities will be divided
	    (assuming a uniform distribution) equally over the values of a in the range.
	    so p(a=4|r) = p(0<a<10|r)/10 [set it to TRUE]
        
    Returns:
        A numpy array of probabilities from 0 to 100.
        
    Example:
        distribute_probs(p,np.array([18,25,35,45,50,56]))
    """

    res = np.zeros(101)  
    jend = np.append(j,101)
    j = np.insert(j,0,0)
    for start,end,v in zip(j,jend,p):
        if (spread):
            res[start:end] = 1.0*v/(end-start)
        else:
            res[start:end] = 1.0*v
    return res



