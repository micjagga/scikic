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
      
      Maybe: a prior on that feature could be added to a FeaturePriorAnswers class
      
    Feature Descriptions:
      factor_age - a categorical list of ages of 100 values, from 0 to 100.
         each value is that person's age, so 32 means their age is 32<=a<33.
         the last value means 100 or more.
      factor_gender - a categorical list of two values (male or female)
      seen - whether a film's been seen (true or false)
      rating - the integer rating given to a film (between 0 and 5).
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
        return "Base class, no question."
    
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
          all_answers: array of all the instantiated answers
        
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
        #returns a list of insights:
        # - inference_result: probability distributions of the features
        # - facts: a dictionary of 'facts' provided by the Answer classes        
        return []
    
    @classmethod
    def metaData(cls):
        return {}

    @classmethod
    def pick_question(cls):
        return 'None', 'None' 
#None = no question to ask the user, but we still want to call it before inference
#Skip = no question to ask user, and we want to skip it when calling inference: It gets called separately (e.g. when jquery gets facebook info, etc)

#Nones are not handled well when put into the database, using string instead

#TODO: Not currently used - delete?
    @classmethod
    def process_answer(cls, dataitem, detail, answer):
        #this function may alter an answer or the details of the question to provide additional information, or reformat it into a standard format.
        return answer, detail;
