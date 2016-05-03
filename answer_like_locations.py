import pymc as pm
import numpy as np
import pandas as pd
import re
import xml.etree.ElementTree as ET
import urllib2
import urllib
import sqlite3
import answer as ans
import pickle
import answer as ans
import config
from integrate_location import parseCountry
from StringIO import StringIO
from zipfile import ZipFile
import urllib2, json
from threading import Thread
import shapefile
from integrate_location import add_location
import zipfile,os.path,os
import csv

import logging
logging.basicConfig(filename=config.loggingFile,level=logging.DEBUG)



class LikeLocationsAnswer(ans.Answer):
    """Takes in likes. No longer looks for geographical terms in the likes. Instead accesses the geolocations of the likes using the facebook API"""
    dataset = 'like_locations';
    placelist = None

    def __init__(self,name,dataitem,itemdetails,answer=None):
        """Constructor

        Args:
          name: The name of this feature
          dataitem: Not used
          itemdetails: Not used
          answer (default None): Not used
        """
        self.dataitem = None #dataitem
        self.itemdetails = None #itemdetails
        self.featurename = None
        self.answer = None
        LikeLocationsAnswer.init_db()

    @classmethod
    def init_db(cls):
        if cls.placelist is None:
            cls.placelist = []
            import xml.etree.ElementTree as ET
            tree = ET.parse('world_iso_map.xml')
            root = tree.getroot()
            for con in root:
                id2 = con.find("code[@id='ISO 2']")
                id3 = con.find("code[@id='ISO 3']")
                name = con.find("name[@id='NAME_1']")
                region = con.find("parent")
                if id2!=None and id3!=None and name!=None and region!=None:
                    cls.placelist.append([name.text, id2.text, id3.text, region.text])


    def HMM_viterbi(self,a,e,p,ys):
        #a=transition matrix, e=emission matrix, p=initial state, ys=observations
        Nstates = a.shape[0]
        path = np.zeros((len(ys),Nstates))
        for i,y in enumerate(ys):
            tempP = np.zeros((Nstates,Nstates))
            if (i==0):
                transition_probs = np.eye(Nstates) #no transitions the first iteration
            else:
                transition_probs = a
            for s in range(Nstates):
                for t in range(Nstates):
                    tempP[s,t] = transition_probs[s,t]*e[t,y]*p[s]
            p = np.max(tempP,axis=0)
            idx = np.argmax(p)    
            p = p / np.sum(p)
            path[i,:] = np.argmax(tempP,axis=0)        
        node = np.argmax(p)
        route = []
        for step in path[::-1]:
            route.insert(0,int(node))
            node = step[node]
        return route

    def add_locations_to_likes(self,likes):
        ids = []
        for like in likes:
            ids.append(like['id'])
        query = {}              
        query['access_token'] = '380462442159554|HQ4dVToLLzinNirZ_K3aw8Mju0Y' #TODO may need to be generated dynamically
        batches = []
        batch = []
        n = 0
        for pageid in ids:
            batch.append({'method':'GET', 'relative_url':str(pageid)})
            n += 1
            if n>48:
                batches.append(batch)
                batch = []
                n = 0
        batches.append(batch)
        results = []
        for batch in batches:
            query['batch'] = json.dumps(batch)
            url = 'https://graph.facebook.com'
            data = urllib.urlencode(query) #queries are not concurrent as facebook probably limits by app.            
            req = urllib2.Request(url, data)
            response = urllib2.urlopen(req)
            the_page = response.read()
            results.extend(json.loads(the_page))

        for i,result in enumerate(results):
            likes[i]['found'] = False
            innerdata = json.loads(result['body'])
            if 'location' in innerdata:
                loc = innerdata['location']
                if 'country' in loc:
                    likes[i]['country'] = loc['country']
                    likes[i]['found'] = True

    def get_places(self,data):
        places = []
        self.add_locations_to_likes(data['data'])
        for like in data['data']:
            cat = like['category']
            if cat not in ['Restaurant/Cafe','Sports/Recreation/Activities','Shopping/Retail','Health/Wellness Website','Company','Non-Profit Organization','Concert Venue','Patio/Garden','Bar','University','Organization','Cause','Education Website','Society/Culture Website','Local Business','Community']:
                continue
            places.append(like)
        return places

    def get_guess(self,res):
        #generates a list of countries user lived in at each like (currently ignores time aspect of likes)
        #probability of staying in the same country for each like
        pStay = 0.9 #0.8
        #the following probabilities get spread across...
         #...the countries in the region
        pMoveInRegion = 0.4 #0.1
         #...all countries
        pMove = 0.1
        pEmitRightCountry = 4./14. #only calculated approximately; 4/14 from my own facebook.

        pl = LikeLocationsAnswer.placelist

        N = len(pl)
        a = np.zeros((N,N))
        for i,recI in enumerate(pl):
            for j,recJ in enumerate(pl):
                if recI[3]==recJ[3]: #if in same region of world
                    a[i,j] = 1
        a = pMoveInRegion*(a/np.tile(np.sum(a,axis=0),(N,1)))
        a[range(N),range(N)] = np.ones(N)*pStay
        a = a + pMove/N

        #calculation was a bit rough, so normalising
        a = a/np.tile(np.sum(a,axis=0),(N,1))
        #probability of 'emitting' that you are in your current country or not
        e = (1-pEmitRightCountry) * np.ones((N,N))/(N)
        e = e + np.eye(N)*pEmitRightCountry
        p = np.ones(N)/N

        guess = self.HMM_viterbi(a,e,p,res)
        return guess


    def insights(self,inference_result,facts):
        #returns a dictionary of insights:
        # - inference_result: probability distributions of the features
        # - facts: a dictionary of 'facts' provided by the Answer classes
        # return [self.get_places(facts['facebook_likes'])]
                   

        if 'where_history' not in facts:
            return {'like_locations_debug':"Note: FB where history missing from facts dictionary"}

        wh = facts['where_history']
        if 'error' in wh:
            if wh['error']=='no_fb_likes':
                return {'like_locations_debug':"Note: I can't see your facebook likes."}
            if wh['error']=='no_fb_countries':
                return {'like_locations_debug':"Note: Your facebook likes don't reveal where you are very clearly."}
        if 'countrylist' not in wh:
                return {'like_locations_debug':"Note: I had an unexpected problem when looking at your facebook likes."}
        countries = wh['countrylist']

        if len(countries)==1:
            con = countries[0]          
            msg = "Since at least %d you've lived in %s" % (con[1],con[0])
        else:
            con = countries[0]
            msg = "Since at least %d you've mainly lived in %s" % (con[1],con[0])
            con = countries[1]
            msg += " but have also lived in %s, around %d" % (con[0], con[1])
            for i,con in enumerate(countries[2:-1]):
                msg +=", %s" % (con[0])
            if len(countries)>2:
                msg += " and %s" % countries[-1][0]
        return {'like_locations_lived':msg}

    def question_to_text(self):
        return "Doesn't need to ask questions."

    @classmethod
    def pick_question(self,questions_asked,facts,target):
    	#return 'name', '' #could return None,None in future, depending on if we get name from facebook
        return 'None', 'None' #None string used to help database

    def calc_probs(self):
       pass

    def get_pymc_function(self,features):
        pass
    
    def append_facts(self,facts,all_answers):
        facts['where_history'] = {}
        if 'facebook_likes' not in facts:
            facts['where_history'] = {'error':'no_fb_likes'}
            return
        places = self.get_places(facts['facebook_likes'])    
        res = []
        placenames = [p[0] for p in LikeLocationsAnswer.placelist]
        import time
        placetimes = []
        year = 0
        for p in places:
            if 'created_time' in p:
                year = time.strptime(p['created_time'],'%Y-%m-%dT%H:%M:%S+0000')[0]
            placetimes.append(year) #if it doesn't have the created_time item then it should use the year from the previous item. Not ideal TODO Fix this so it does something more sane.
        restime = []
        for p,t in zip(places,placetimes):
            if 'country' in p:
                res.append(placenames.index(p['country']))
                restime.append(t)
        guesses = self.get_guess(res)
        import collections
        counts = collections.Counter(guesses)
        c = counts.items()
        newlist = sorted(c, key=lambda k: -k[1]) 
        countries = []

        
        for item in newlist:
            idx = (len(guesses) - 1) - guesses[::-1].index(item[0])            
            datetime = restime[idx]
            countries.append((placenames[res[idx]],datetime))

        if len(guesses)>0:
            if ('where' not in facts) or ('country' not in facts['where']):
                add_location(facts,countries=countries[-1][0]) #add last country from the process as our guess #TODO We can do better (probabilistic)
        if len(countries)==0:
            facts['where_history']['error'] = 'no_fb_countries';
        facts['where_history']['countrylist'] = []
        for con in countries:  
             facts['where_history']['countrylist'].append(con)
    
