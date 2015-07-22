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

from StringIO import StringIO
from zipfile import ZipFile


class MoviePersonality(ans.Answer):
    """Asks 10 questions to determine your personality
       based on http://www.sciencedirect.com/science/article/pii/S0092656603000461
       'A very brief measure of the Big-Five personality domains' Gosling, Rentfrow, and Swann (2003)"""

    dataset = 'personality';
    
    @classmethod
    def setup(cls,pathToData):
        pass

    @classmethod
    def init_db(cls):
        pass

    
    def __init__(self,name,dataitem,detail,answer=None):
        """Constructor, instantiate an answer associated with a personality question.

        Args:
          name: The name of this feature
          dataitem: Can be 1-10
          detail: not used
          answer: Can be 1-7          
        """
        self.dataitem = dataitem
        self.answer = answer
        self.featurename = name
        
    def question_to_text(self):
        question_text = ['extraverted and enthusiastic','critical and quarrelsome', 'dependable and self-disciplined', 'anxious and easily upset', 'open to new experiences and complex','reserved and quiet', 'sympathetic and warm', 'disorganized and careless','calm and emotionally stable', 'conventional and uncreative'];
        question_string = "You seem %s, do you agree somewhat with this?" % question_text[int(self.dataitem)]
        return {'question':question_string,'type':'select','options':['Disagree strongly','Disagree moderately','Disagree a little','Neither agree nor disagree','Agree a little','Agree moderately','Agree strongly']}

    def append_features(self,features,facts): 
        pass

    @classmethod
    def pick_question(self,questions_asked):
        available_questions = range(10);
        for q in questions_asked:
            if q['dataset']=='personality':
                available_questions.remove(int(q['dataitem']))
        question_number = available_questions[0]
        return question_number,'';

