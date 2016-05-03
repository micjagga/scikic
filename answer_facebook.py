import pymc as pm
import numpy as np
import pandas as pd
import re
import xml.etree.ElementTree as ET
import urllib2
import sqlite3
import answer as ans
import json


import logging
import config
logging.basicConfig(filename=config.loggingFile,level=logging.DEBUG)


from StringIO import StringIO
from zipfile import ZipFile

class FacebookAnswer(ans.Answer):
    """Facebook answer: handles facebook reply"""
    dataset = 'facebook';

    @classmethod
    def init_db(cls):
        pass


    def __init__(self,name,dataitem,itemdetails,answer=None):
        """Constructor, instantiate an answer associated with seeing a movie.

        Args:
          name: The name of this feature
          dataitem: Can be 'name' or ...
          itemdetails: Details about the item
          answer (default None): Either a string if the item's the name or...
        """
        self.dataitem = dataitem
        self.itemdetails = itemdetails #not sure this is used yet
        self.featurename = name
        self.answer = answer
        
        if ((answer==None) or (len(answer)<2)):
            return
        try:
            self.data = json.loads(answer)
        except ValueError: #TODO: Somehow more than one facebook instance is created - one doesn't get its 'answer' populated, and this handles that situation.
            self.data = {} #we don't seem to have got the info from facebook

    def append_facts(self,facts,all_answers):
        if ((self.answer==None) or (len(self.answer)<2)):
            return #don't do anything

        """This adds facts to the facts dictionary in place:
        - name
        - dob
        - ...
        """
        fb_data = json.loads(self.data['reply'])
        if ('birthday' in fb_data):
            facts['dob'] = fb_data['birthday'] #TODO: Turn from string to meaningful date
    
        if ('first_name' in fb_data):
            facts['first_name'] = fb_data['first_name']

        if ('likes' in fb_data):
            facts['facebook_likes'] = fb_data['likes']


    @classmethod
    def metaData(cls):
        return {'citation':'The <a href="facebook.com">facebook</a> graph API'}

    @classmethod
    def pick_question(self,questions_asked,facts,target):
        return 'Skip', 'None'       #we don't want to ask questions to get this data
