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

from StringIO import StringIO
from zipfile import ZipFile


import urllib2, json
from threading import Thread
from nltk.corpus import words
from nltk.stem import WordNetLemmatizer
import shapefile

from integrate_location import add_location

import zipfile,os.path,os

class LikeLocationsAnswer(ans.Answer):
    """Takes in likes and looks for geographical terms in the likes"""
    dataset = 'like_locations';

    #connects place names with regions
    placelist = [['Brazil', 'BRA', 'Latin America'],
 ['Norway', 'NOR', 'Europe'],
 ['Ukraine', 'UKR', 'Europe'],
 ['Croatia', 'HRV', 'Europe'],
 ['Cuba', 'CUB', 'Caribbean'],
 ['Eritrea', 'ERI', 'Sub Saharan Africa'],
 ['Estonia', 'EST', 'Europe'],
 ['Ethiopia', 'ETH', 'Sub Saharan Africa'],
 ['Falkland Islands (Islas Malvinas)', 'FLK', 'Latin America'],
 ['Finland', 'FIN', 'Europe'],
 ['India', 'IND', 'Asia'],
 ['Andorra', 'AND', 'Europe'],
 ['Argentina', 'ARG', 'Latin America'],
 ['Australia', 'AUS', 'Australia'],
 ['Bangladesh', 'BGD', 'Asia'],
 ['Bulgaria', 'BGR', 'Europe'],
 ['Egypt', 'EGY', 'NorthAfrica'],
 ['Iraq-Saudi Arabia Neutral Zone', '   ', 'Asia'],
 ['Isle of Man', 'XIM', 'Europe'],
 ['United Kingdom', 'GBR', 'Europe'],
 ['United States', 'USA', 'North America'],
 ['Uzbekistan', 'UZB', 'Asia'],
 ['Singapore', 'SGP', 'Pacific'],
 ['Slovakia', 'SVK', 'Europe'],
 ['Iran', 'IRN', 'Asia'],
 ['Korea, Republic of', 'KOR', 'Asia'],
 ['Madagascar', 'MDG', 'Sub Saharan Africa'],
 ['Malaysia', 'MYS', 'Asia'],
 ['Maldives', 'MDV', 'Pacific'],
 ['Mongolia', 'MNG', 'Asia'],
 ['Myanmar (Burma)', 'MMR', 'Asia'],
 ['Solomon Islands', 'SLB', 'Asia'],
 ['Bolivia', 'BOL', 'Latin America'],
 ['Byelarus', 'BLR', 'Europe'],
 ['Greenland', 'GRL', 'North America'],
 ['Guinea', 'GIN', 'Sub Saharan Africa'],
 ['Iceland', 'ISL', 'Europe'],
 ['Turkey', 'TUR', 'Asia'],
 ['Afghanistan', 'AFG', 'Asia'],
 ['Angola', 'AGO', 'Sub Saharan Africa'],
 ['Antarctica', 'ATA', 'Antarctica'],
 ['Antigua and Barbuda', 'ATG', 'Caribbean'],
 ['Cameroon', 'CMR', 'Sub Saharan Africa'],
 ['Canada', 'CAN', 'North America'],
 ['Congo', 'COG', 'Sub Saharan Africa'],
 ['Czech Republic', 'CZE', 'Europe'],
 ['Denmark', 'DNK', 'Europe'],
 ['Yugoslavia', 'YUG', 'Europe'],
 ['St. Lucia', 'LCA', 'Caribbean'],
 ['St. Vincent and the Grenadines', 'VCT', 'Caribbean'],
 ['Sudan', 'SDN', 'Sub Saharan Africa'],
 ['Sweden', 'SWE', 'Europe'],
 ['Azerbaijan', 'AZE', 'Asia'],
 ['Bahrain', 'BHR', 'Asia'],
 ['Bermuda', 'BMU', 'North America'],
 ['El Salvador', 'SLV', 'Latin America'],
 ['Guinea-Bissau', 'GNB', 'Sub Saharan Africa'],
 ['Ivory Coast', 'CIV', 'Sub Saharan Africa'],
 ['Jan Mayen', 'SJM', 'Europe'],
 ['Lebanon', 'LBN', 'Asia'],
 ['Martinique', 'MTQ', 'Caribbean'],
 ['Venezuela', 'VEN', 'Latin America'],
 ['Vietnam', 'VNM', 'Asia'],
 ['Dominica', 'DMA', 'Caribbean'],
 ['Ecuador', 'ECU', 'Latin America'],
 ['Gabon', 'GAB', 'Sub Saharan Africa'],
 ['Gaza Strip', 'ISR', 'Asia'],
 ['Ireland', 'IRL', 'Europe'],
 ['Italy', 'ITA', 'Europe'],
 ['Japan', 'JPN', 'Asia'],
 ['Reunion', 'REU', 'Sub Saharan Africa'],
 ['Germany', 'DEU', 'Europe'],
 ['Greece', 'GRC', 'Europe'],
 ['New Zealand', 'NZL', 'Australia'],
 ['Nigeria', 'NGA', 'Sub Saharan Africa'],
 ['Pakistan', 'PAK', 'Asia'],
 ['Russia', 'RUS', 'Europe'],
 ['Turkmenistan', 'TKM', 'Asia'],
 ['France', 'FRA', 'Europe'],
 ['Zaire', 'ZAR', 'Sub Saharan Africa'],
 ['Zambia', 'ZMB', 'Sub Saharan Africa'],
 ['Indonesia', 'IDN', 'Asia'],
 ['Kazakhstan', 'KAZ', 'Asia'],
 ['Korea, Peoples Republic of', 'PRK', 'Asia'],
 ['Mexico', 'MEX', 'Latin America'],
 ['Poland', 'POL', 'Europe'],
 ['Belgium', 'BEL', 'Europe'],
 ['Liberia', 'LBR', 'Sub Saharan Africa'],
 ['Puerto Rico', 'PRI', 'Caribbean'],
 ['Sao Tome and Principe', 'STP', 'Sub Saharan Africa'],
 ['Togo', 'TGO', 'Sub Saharan Africa'],
 ['Saudi Arabia', 'SAU', 'Asia'],
 ['Senegal', 'SEN', 'Sub Saharan Africa'],
 ['Svalbard', 'SJM', 'Europe'],
 ['Algeria', 'DZA', 'NorthAfrica'],
 ['Central African Republic', 'CAF', 'Sub Saharan Africa'],
 ['Chile', 'CHL', 'Latin America'],
 ['China', 'CHN', 'Asia'],
 ['Colombia', 'COL', 'Latin America'],
 ['Georgia', 'GEO', 'Asia'],
 ['Iraq', 'IRQ', 'Asia'],
 ['Kyrgyzstan', 'KGZ', 'Asia'],
 ['Laos', 'LAO', 'Asia'],
 ['Mali', 'MLI', 'Sub Saharan Africa'],
 ['Mozambique', 'MOZ', 'Sub Saharan Africa'],
 ['Netherlands', 'NLD', 'Europe'],
 ['Oman', 'OMN', 'Asia'],
 ['St. Christopher-Nevis', '   ', 'Caribbean'],
 ['Belize', 'BLZ', 'Latin America'],
 ['Burundi', 'BDI', 'Sub Saharan Africa'],
 ['Equatorial Guinea', 'GNQ', 'Sub Saharan Africa'],
 ['French Polynesia', 'PYF', 'Pacific'],
 ['Guadeloupe', 'GLP', 'Caribbean'],
 ['Hong Kong', '   ', 'Asia'],
 ['Hungary', 'HUN', 'Europe'],
 ['Northern Mariana Islands', 'MNP', 'Pacific'],
 ['Panama', 'PAN', 'Latin America'],
 ['Papua New Guinea', 'PNG', 'Asia'],
 ['Peru', 'PER', 'Latin America'],
 ['Philippines', 'PHL', 'Asia'],
 ['South Africa', 'ZAF', 'Sub Saharan Africa'],
 ['Spain', 'ESP', 'Europe'],
 ['Swaziland', 'SWZ', 'Sub Saharan Africa'],
 ['Tajikistan', 'TJK', 'Asia'],
 ['Tanzania, United Republic of', 'TZA', 'Sub Saharan Africa'],
 ['Thailand', 'THA', 'Asia'],
 ['Tonga', 'TON', 'Pacific'],
 ['Trinidad and Tobago', 'TTO', 'Caribbean'],
 ['Albania', 'ALB', 'Europe'],
 ['Armenia', 'ARM', 'Asia'],
 ['Austria', 'AUT', 'Europe'],
 ['Bahamas, The', 'BHS', 'Caribbean'],
 ['Barbados', 'BRB', 'Caribbean'],
 ['Benin', 'BEN', 'Sub Saharan Africa'],
 ['Bhutan', 'BTN', 'Asia'],
 ['Bosnia and Herzegovina', 'BIH', 'Europe'],
 ['Botswana', 'BWA', 'Sub Saharan Africa'],
 ['Brunei', 'BRN', 'Asia'],
 ['Burkina Faso', 'BFA', 'Sub Saharan Africa'],
 ['Cambodia', 'KHM', 'Asia'],
 ['Cape Verde', 'CPV', 'Sub Saharan Africa'],
 ['Chad', 'TCD', 'Sub Saharan Africa'],
 ['Comoros', 'COM', 'Sub Saharan Africa'],
 ['Costa Rica', 'CRI', 'Latin America'],
 ['Cyprus', 'CYP', 'Asia'],
 ['Djibouti', 'DJI', 'Sub Saharan Africa'],
 ['Dominican Republic', 'DOM', 'Caribbean'],
 ['Faroe Islands', 'FRO', 'Europe'],
 ['Fiji', 'FJI', 'Asia'],
 ['French Guiana', 'GUF', 'Latin America'],
 ['Gambia, The', 'GMB', 'Sub Saharan Africa'],
 ['Ghana', 'GHA', 'Sub Saharan Africa'],
 ['Grenada', 'GRD', 'Caribbean'],
 ['Guatemala', 'GTM', 'Latin America'],
 ['Guyana', 'GUY', 'Latin America'],
 ['Haiti', 'HTI', 'Caribbean'],
 ['Honduras', 'HND', 'Latin America'],
 ['Israel', 'ISR', 'Asia'],
 ['Jamaica', 'JAM', 'Caribbean'],
 ['Jordan', 'JOR', 'Asia'],
 ['Kenya', 'KEN', 'Sub Saharan Africa'],
 ['Kerguelen', '   ', 'Antarctica'],
 ['Kiribati', 'KIR', 'Asia'],
 ['Kuwait', 'KWT', 'Asia'],
 ['Latvia', 'LVA', 'Europe'],
 ['Lesotho', 'LSO', 'Sub Saharan Africa'],
 ['Libya', 'LBY', 'NorthAfrica'],
 ['Liechtenstein', 'LIE', 'Europe'],
 ['Lithuania', 'LTU', 'Europe'],
 ['Luxembourg', 'LUX', 'Europe'],
 ['Macau', 'MAC', 'Asia'],
 ['Macedonia', 'MKD', 'Europe'],
 ['Malawi', 'MWI', 'Sub Saharan Africa'],
 ['Malta', 'MLT', 'Pacific'],
 ['Mauritania', 'MRT', 'Sub Saharan Africa'],
 ['Mauritius', 'MUS', 'Sub Saharan Africa'],
 ['Moldova', 'MDA', 'Europe'],
 ['Monaco', 'MCO', 'Europe'],
 ['Morocco', 'MAR', 'NorthAfrica'],
 ['Namibia', 'NAM', 'Sub Saharan Africa'],
 ['Nepal', 'NPL', 'Asia'],
 ['New Caledonia', 'NCL', 'Asia'],
 ['Nicaragua', 'NIC', 'Latin America'],
 ['Niger', 'NER', 'Sub Saharan Africa'],
 ['Paraguay', 'PRY', 'Latin America'],
 ['Portugal', 'PRT', 'Europe'],
 ['Qatar', 'QAT', 'Asia'],
 ['Romania', 'ROM', 'Europe'],
 ['Rwanda', 'RWA', 'Sub Saharan Africa'],
 ['San Marino', 'SMR', 'Europe'],
 ['Seychelles', 'SYC', 'Sub Saharan Africa'],
 ['Sierra Leone', 'SLE', 'Sub Saharan Africa'],
 ['Slovenia', 'SVN', 'Europe'],
 ['Somalia', 'SOM', 'Sub Saharan Africa'],
 ['Sri Lanka', 'LKA', 'Asia'],
 ['Suriname', 'SUR', 'Latin America'],
 ['Switzerland', 'CHE', 'Europe'],
 ['Syria', 'SYR', 'Asia'],
 ['Taiwan', 'TWN', 'Asia'],
 ['Tunisia', 'TUN', 'NorthAfrica'],
 ['Turks and Caicos Islands', 'TCA', 'Caribbean'],
 ['Uganda', 'UGA', 'Sub Saharan Africa'],
 ['United Arab Emirates', 'ARE', 'Asia'],
 ['Uruguay', 'URY', 'Latin America'],
 ['Vanuatu', 'VUT', 'Asia'],
 ['Western Sahara', 'ESH', 'NorthAfrica'],
 ['Western Samoa', 'WSM', 'Pacific'],
 ['Yemen', 'YEM', 'Asia'],
 ['Zimbabwe', 'ZWE', 'Sub Saharan Africa']];
 
    @classmethod
    def init_db(cls):
        pass

    @classmethod
    def setup(cls,pathToData):
        """Creates files, downloads data, and populates the datafiles"""
        import nltk
        nltk.data.path = [config.pathToData + 'nltk_data']
        os.environ["NLTK_DATA"] = config.pathToData + 'nltk_data'
        #os.makedirs(pathToData+"nltk_data")
        print "Downloading nltk wordnet package"
        nltk.download('words',download_dir=pathToData+"nltk_data")
        nltk.download('wordnet',download_dir=pathToData+"nltk_data")
        print "Downloading country boundaries"
        
        #If we don't have the file, download it.
        if not os.path.isfile("/tmp/psych_countryboundaries.zip"):
            #print "Downloading www.diva-gis.org/Data country boundary shape data..."
            print "Downloading http://www.naturalearthdata.com/http//www.naturalearthdata.com/download/110m/cultural/ne_110m_admin_0_countries.zip country boundaries..."
            url = 'http://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip'            
            urllib.urlretrieve(url, "/tmp/psych_countryboundaries.zip")
        cb_zipfile = "/tmp/psych_countryboundaries.zip"

        #If it's not unzipped, unzip it.
        if not os.path.exists(pathToData+"/countryboundaries"):
            print "Unzipping"
            os.makedirs(pathToData+"/countryboundaries")
            zf = zipfile.ZipFile(cb_zipfile)
            for f in zf.infolist():
                zf.extract(f.filename,pathToData+"/countryboundaries")
 

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
            #print tempP
        node = np.argmax(p)
        route = []
        for step in path[::-1]:
            route.insert(0,int(node))
            node = step[node]
        return route


    def geonames_api_query(self,place):
        name = place['word']
        from urllib import urlencode
        name = name.encode('utf8')
        #url = 'http://api.geonames.org/searchJSON?name_equals=%s&featureCode=PPLA2&featureCode=PPLX&featureCode=PPLA3&featureCode=PPLA4&featureCode=PPLA&featureCode=PPLC&maxRows=10&username=lionfish' % name
        url = 'http://api.geonames.org/searchJSON?name_equals=%s&featureCode=ADM1&featureCode=PCLI&featureCode=PPLX&featureCode=PPLA2&featureCode=ADM2&featureCode=ADM3&featureCode=ADM4&featureCode=PPLA3&featureCode=PPLA4&featureCode=PPLA&featureCode=PPLC&maxRows=10&username=lionfish' % name
        #http://api.geonames.org/searchJSON?name_equals=burma&maxRows=10&username=lionfish
        raw_json = urllib2.urlopen(url).readline() 
        data = json.loads(raw_json)
        if 'geonames' not in data:
            place['found'] = False
            return
        
        place['found'] = False
        lastpop = -1
        for placedata in data['geonames']:
            if placedata['name'].lower()==name.lower():
                if placedata['population']>lastpop: #go with the biggest
                    lastpop = placedata['population']
                    place['lat'] = placedata['lat']
                    place['lng'] = placedata['lng']
                    place['raw'] = placedata                
                    place['found'] = True

    def get_places(self,data):
        import nltk
        nltk.data.path = [config.pathToData + 'nltk_data']
        os.environ["NLTK_DATA"] = config.pathToData + 'nltk_data'
        s = WordNetLemmatizer()
        places = []
        for like in data['data']:
            datetime = like['created_time']
            for fullword in like['name'].split(' '):
                word = s.lemmatize(fullword.lower()) #strips -s etc from end of word

                import sys
              #  print >>sys.stderr, "checking if %s is a word" % word

                if word in words.words():
                    continue 

               # print >>sys.stderr, "word %s appended" % word

                places.append({'word':word,'datetime':datetime})
       
        threads = []
        for place in places:
            t = Thread(target = self.geonames_api_query, args=(place,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

      #  print >>sys.stderr, "PLACES"
      #  print >>sys.stderr, places
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
                if recI[2]==recJ[2]: #if in same region of world
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
        #returns a list of insights:
        # - inference_result: probability distributions of the features
        # - facts: a dictionary of 'facts' provided by the Answer classes
        # return [self.get_places(facts['facebook_likes'])]
                   

        if 'where_history' not in facts:
            return []

        wh = facts['where_history']
        if 'error' in wh:
            if wh['error']=='no_fb_likes':
                return ["I can't tell which country you're in, just looking at your facebook likes, as I can't see your facebook likes!"]
            if wh['error']=='no_fb_countries':
                return ["I can't tell which country you're in, just looking at your facebook likes."]
        countries = wh['list']
        if len(countries)==1:
            con = countries[0]          
            msg = "Since at least %d you've lived in %s" % (con[1][0],con[0][0])
        else:
            con = countries[0]
            msg = "Since at least %d you've mainly lived in %s" % (con[1][0],con[0][0])
            con = countries[1]
            msg += " but have also lived in %s, around %d" % (con[0][0], con[1][0])
            for i,con in enumerate(countries[2:-1]):
                msg +=", %s" % (con[0][0])
            if len(countries)>2:
                msg += " and %s" % countries[-1][0][0]

        return [msg]

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
        points = []
        for p in places:
            if p['found']:
                points.append((float(p['lng']),float(p['lat']),p))
        placenames = [p[0] for p in LikeLocationsAnswer.placelist]
        res = []
        for p in points:            
            res.append(placenames.index(p[2]['raw']['countryName']))
        guesses = self.get_guess(res)
        import collections
        counts = collections.Counter(guesses)
        c = counts.items()
        newlist = sorted(c, key=lambda k: -k[1]) 

        pl = LikeLocationsAnswer.placelist

        import time
        countries = []
        for item in newlist:
            idx = (len(guesses) - 1) - guesses[::-1].index(item[0])
            datetime = points[idx][2]['datetime']
            t = time.strptime(datetime, '%Y-%m-%dT%H:%M:%S+0000')
            countries.append((pl[item[0]],t))
        add_location(facts,countries=[pl[guesses[-1]]]) #add last country from the process as our guess #TODO We can do better (probabilistic)
        if len(countries)==0:
            facts['where_history']['error'] = 'no_fb_countries';    
        facts['where_history']['countrylist'] = countries
    

    def append_features(self,features,facts): 
        pass
