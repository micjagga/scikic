import pymc as pm
import numpy as np
import answer as ans
import random
import helper_functions as hf
import config

class LifestyleAnswer(ans.Answer):
    """Asks lifestyle questions (cars driven, etc)"""

    dataset = 'lifestyle';
    
    @classmethod
    def setup(cls,pathToData):
        pass

    @classmethod
    def init_db(cls):
        pass

    def __init__(self,name,dataitem,detail,answer=None):
        LifestyleAnswer.init_db()
        self.dataitem = dataitem
        self.detail = detail
        self.answer = answer
        self.featurename = name
        
    def question_to_text(self):
        if (self.dataitem=='workplace'):
            return {'question':"Where do you work?",'type':'text'};
    	if (self.dataitem=='cats'):
            return {'question':"How many cats do you have?",'type':'text'};
    	if (self.dataitem=='guns'):
            return {'question':"How many guns do you own?",'type':'text'};
    	if (self.dataitem=='travel'):
            return {'question':"How do you travel to work?",'type':'select','options':['Not in employment','Work mainly from home','Train/Tram/underground','Bus','Car/van','Bicycle','On Foot','Other']};
        
    @classmethod
    def pick_question(self,questions_asked,facts,target):
        dataitem = random.choice(['cats','guns','travel','workplace'])
        return dataitem,''

