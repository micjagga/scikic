import numpy as np
import answer as ans
import config
import urllib2
import json

class GeoLocAnswer(ans.Answer):
    """Geoloc answer: figures out where you are from IP and asking for city/country"""
    
    dataset = 'geoloc';
    _landmarks = None;
    _boundaries = None;
   
    def __init__(self,name,dataitem,detail,answer=None):
        #dataitem = nearcity
        # self.detail = name of the city
        #dataitem = city
        #dataitem = country

        self.dataitem = dataitem
        try: #try parsing json
            self.detail = json.loads(detail)
        except ValueError:
            self.detail = detail
        self.answer = answer
        self.featurename = name
        
    def question_to_text(self):
    	if (self.dataitem=='nearcity'):
            return {'question':"Is your home in or near %s, %s? (yes or no)" % (self.detail['city'], self.detail['country']),'type':'select','options':['yes','no']} 
        if (self.dataitem=='city'):
            return {'question':"Which city or town are you in or near?", 'type':'text'}
        if (self.dataitem=='country'):
            return {'question':"Which country are you in?",'type':'select','options':['us','uk','germany','other']} 

    def append_facts(self,facts,all_answers):
        if 'where' not in facts:
            facts['where'] = {}
        if 'guess_loc' not in facts:
            facts['guess_loc'] = {}
        if 'country' not in facts['where']:
            facts['where']['country'] = []
        if 'city' not in facts['where']:
            facts['where']['city'] = []

        if self.dataitem=='country':
            facts['where']['country'] = [{'item':self.answer, 'probability':1.0}]
        if self.dataitem=='city':
            facts['where']['city'] = [{'item':(self.answer, facts['where']['country']), 'probability':1.0}]
        if self.dataitem=='nearcity':
            if self.answer=='yes':
                facts['where']['city'] = [{'item':(self.detail['city'], self.detail['country']), 'probability':1.0}]
                facts['where']['country'] = [{'item':(self.detail['country']), 'probability':1.0}]
                facts['guess_loc']['ip_wrong'] = False
            if self.answer=='no':
                facts['guess_loc']['ip_wrong'] = True


    def append_features(self,features,facts): 
        #this class doesn't directly create features. For example the census class will do this.
        pass

    @classmethod
    def pick_question(cls,questions_asked,facts,target):       
    #Picks a question to ask, using previous questions asked.
        if 'guess_loc' not in facts:
            facts['guess_loc'] = {}        
        if 'ip_wrong' in facts['guess_loc']:
            ipwrong = facts['guess_loc']['ip_wrong'] #whether guessing using their ip address got the right answer.

        if 'ip_wrong' not in facts['guess_loc']: #means we've not tried to work out where they are yet using their ip address
            url = 'https://freegeoip.net/json/'; #todo use local freegeo
            try:
                raw_json = urllib2.urlopen(url,timeout=3).readline() #this bit might throw an exception

                data = {}
                json_loc = json.loads(raw_json)
                #TODO: CACHE IN DB
                return 'nearcity',json.dumps({'city':json_loc['city'],'country':json_loc['country_name']})
            except urllib2.HTTPError:
                ipwrong = True #effectively it's wrong as we can't find out where they are.
            except urllib2.URLError:#time out?
                ipwrong = True #effectively it's wrong as we can't find out where they are. 
           
        if ipwrong:
            #ask where they are country then city
            if 'country' not in facts['where'] or len(facts['where']['country'])!=1:
                return 'country','{}'
            else:
                if 'city' not in facts['where'] or len(facts['where']['city'])!=1:
                    return 'city','{}'
        return 'None','None'
     #   city_details = {}
     #   city_details['latitude'] = 53.383611
     #   city_details['longitude'] = -1.466944

    
            
