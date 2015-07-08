import pymc as pm
import numpy as np
import pandas as pd
import re
import xml.etree.ElementTree as ET
import urllib2,urllib
import sqlite3
import answer as ans
import random
import zipfile,os.path,os
import sqlalchemy as sa
import pandas as pd
import helper_functions as hf
import config

from StringIO import StringIO
from zipfile import ZipFile


class MusicAnswer(ans.Answer):
    """Movielens answer: handles seen, ratings, etc associated with movie rankings"""
    
    dataset = 'music';

    def insights(self,inference_result,facts):        
        #returns a list of insights:
        # - inference_result: probability distributions of the features
        # - facts: a dictionary of 'facts' provided by the Answer classes
        ##location = facts['city'] #for example?
        ##self.answer
        ##Do clever Felix code here...
        #Their favourite artist will be in self.answer (A string)
        #Their location will be in...
            #facts['city'] maybe???
            #facts['country'] maaaaaybe?
        insight_list = ["Why not check out Humbar who are playing in Sheffield next week!!","I think as you like Air, I think you'll like Royksopp.","More insights..."]
        return insight_list
        

    @classmethod
    def setup(cls,pathToData):
        pass
 
    def __init__(self,name,dataitem,detail,answer=None):
        """Constructor, instantiate an answer associated with a response from the user

        Args:
          name: The name of this feature
          dataitem: Unused
          detail: Unused
          answer (default None): Name of the artist
        """
        self.dataitem = None
        self.detail = None
        self.answer = answer
        self.featurename = name
        
    def question_to_text(self):        
        return "What's your favourite band or artist? (be honest!)" #TODO Rewrite
      
    def append_features(self,features,facts): 
        pass

    @classmethod
    def pick_question(self,questions_asked):
        return 'favourite_artist','';

