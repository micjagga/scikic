import pymc as pm
import numpy as np
import answer as ans
import random
import helper_functions as hf
import config

class DemographicAnswer(ans.Answer):
    """Asks demographic questions (age, gender, etc) useful with the census modules. Location is asked in the answer_postal module, as it's quite complicated."""
    dataset = 'demographic';
    
    @classmethod
    def setup(cls,pathToData):
        pass

    @classmethod
    def init_db(cls):
        pass

    def __init__(self,name,dataitem,detail,answer=None):
        DemographicAnswer.init_db()
        self.dataitem = dataitem
        self.detail = detail
        self.answer = answer
        self.featurename = name
        
    def question_to_text(self):
    	if (self.dataitem=='age'):
            return {'question':"What is your age?",'type':'text'};
    	if (self.dataitem=='gender'):
            return {'question':"What gender are you?",'type':'select','options':['Male','Female','Other']};
    
    def append_facts(self,facts,all_answers):        
        if (self.dataitem=='age'):
            try:
                facts['age'] = int(self.answer)
            except ValueError:
                pass
                #Handle the exception
                #silently skip.        
        if (self.dataitem=='gender'):
            facts['gender'] = self.answer

    
    def append_features(self,features,facts,relationships):
        #normally factor_age is a flat prior, but here we make it very non-flat, as we know the answer. Ideally we'd manipulate the other probability distributions to integrate out age, but that's quite tricky (programmatically).
        if ('age' in facts):
            if not 'factor_age' in features:    #TODO: We need to overwrite factor_age with this more certain distribution
                age = facts['age']
                if (age>=0):
                    if (age>99):
                        age = 100
                    p = np.zeros(101)
                    p[age] = 1 #certain
                    features['factor_age'] = pm.Categorical('factor_age',p);
        if ('gender' in facts):
            if not 'factor_gender' in features: #TODO: We need to overwrite factor_gender with this more certain distribution
                ratio = [0.5,0.5] #prior...
                if facts['gender']=='Male':
                    ratio = [1.0,0]
                if facts['gender']=='Female':
                    ratio = [0,1.0]               
                if facts['gender']=='Other':
                    ratio = [0.5,0.5] #don't know what to do, as the census etc doesn't have data for this situation.
                features['factor_gender'] = pm.Categorical('factor_gender',np.array(ratio)); #male, female...
      
    @classmethod
    def pick_question(self,questions_asked,facts,target):
        dataitem = random.choice(['age','gender'])
        return dataitem,''

