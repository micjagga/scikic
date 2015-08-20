import answer as ans
import config

class DirectAnswer(ans.Answer):
    """Direct answer: if we ask a direct question at the end of the experience (e.g. what's your age)"""
    
    dataset = 'direct';
   
    def __init__(self,name,dataitem,detail,answer=None):
        #dataitem = nearcity
        # self.detail = name of the city
        #dataitem = city
        #dataitem = country

        self.dataitem = dataitem
        self.detail = detail
        self.answer = answer
        self.featurename = name
        
    def question_to_text(self):
    	if (self.dataitem=='age'):
            return {'question':"I wonder if I was correct about your age. What is your actual age (if you don't mind me asking?)",'type':'text'} 
    	if (self.dataitem=='religion'):
            return {'question':"I wonder if I was correct about your religion. What religion (or none) do you identify as?",'type':'text'}
