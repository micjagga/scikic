import json
import numpy as np
from scipy import stats
import math

from sklearn.externals import joblib
from TextProcessing import TextProcessing
from collections import OrderedDict



fullList = ['ope','con','ext','agr','neu'] 
class jsonExtractor(object):
    """ Json object related processes 
    
     Attributes:
         self.typeList: contains the big5 trait list which need to be returned
                   default: return all big5 traits
                   full list: ['ope','con','ext','agr','neu']
    
    """
    

    
    
    def getScore(self, text, typeList=['ope','con','ext','agr','neu']):
        """ get the Json String according to the predicted data (predict model is determined by the typeList)
        Args: 
            text: a string of text used to predict big5 trait   
            typeList: contains the big5 trait list which need to be returned  
        Returns:
            jsonStr: a Json String, e.g., {"ope": 4.2, "neu": 2.31, "con": 3.09, "ext": 3.69, "agr": 3.08}  
        """
        
        model_path = """./model/"""
        data = OrderedDict()
        
        tp = TextProcessing()
        X = tp.extractFeature(text)
        X = np.array(X)
            
        for t in typeList:
            if t not in fullList:
                continue
            else:
                model_name = """Predictor_"""+t+""".pkl"""
                model = joblib.load(model_path+model_name)
                y_pred = model.test(X)  
                data[t] = y_pred[0]
        
        jsonStr = json.dumps(data)
        return jsonStr
    
    
    def getPercentile(self, jsonScore):
        """ get the percentile of the big5 scores in a score list of about 3.1M users
        Args:
            jsonScore: a json string which contains the big5 score
                     e.g., {"ope": 4.25, "con": 3.14, "ext": 3.58, "agr": 3.33, "neu": 2.22}
        Return: a Json string, e.g., {"ope": -100%, "con": 0%, "ext": 100%, "agr": 100%, "neu": 0%}
            80% means that the input score is higher than 80% of the scores of 3.1M users 

        """
        
        root_path = """./dic/"""
  
   
        data = OrderedDict() 
        score = json.loads(jsonScore)
        for k, v in score.items():
            dic_path = root_path+'percentile_'+k+'.csv'
            dic_data = self.loadData(dic_path, 1, 0)
            dic_key = dic_data[:, 0]
            dic_percent = dic_data[:, 1]
            ind = self.find_nearestInd(dic_key,v)
            data[k] = round(dic_percent[ind], 2)
            
        jsonStr = json.dumps(data)
        return jsonStr
            
            
    def loadData(self,dataPath, skiprow, startCol):
        '''
        load data from a csv file
        skiprow: 1: skip the first row
        startCol: first col: 0
        '''
        with open(dataPath) as f:
            f.readline()
            ncols = len(f.readline().split(','))
            
     
        data = np.loadtxt(dataPath, delimiter=',', skiprows=skiprow, usecols=range(startCol,ncols))
        return data      
        
       
    def isEnglish(self, s):
        '''check if the input text s is in English '''
        tp = TextProcessing()
        lan = tp.languageDetection(s)
        if lan == 'en': return True
        else: return False
    
    def find_nearestInd(self,array,value):
        '''find the index of the nearest element in a sorted array'''
        idx = np.searchsorted(array, value, side="left")
        if math.fabs(value - array[idx-1]) < math.fabs(value - array[idx]):
#             return array[idx-1]
            return idx-1
        else:
            return idx
#             return array[idx]