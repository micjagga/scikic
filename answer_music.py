#Written by Felix, July 2015

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
import random

from StringIO import StringIO
from zipfile import ZipFile

#global event_names
#global event_datetimes
#global event_locations
#global event_listings
#event_listings = []
#event_names = []
#event_datetimes = []
#event_locations = []


class MusicAnswer(ans.Answer):
    """"MusicAnswer takes an input of an artist the user likes and returns a similar artist and a recommended local event based on the tase of the user."""
    dataset = 'music';

    def insights(self,inference_result,facts):  
        limit = 10      
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

        if 'where' not in facts:
            return []
        else:
            if 'city' not in facts['where']:
                return []
            if 'country' not in facts['where']:
                return []
        
        event_names = []  
        event_datetimes = []
        event_locations = []
        
        artist = self.answer
        artist = artist.replace(" ", "+")
        try: #Mike's change, to handle if a band doesn't exist
#http://ws.audioscrobbler.com/2.0/?method=artist.getsimilar&artist=Eels&limit=3&autocorrect=1&api_key=02c3301ab9e648c504edf4d7dc93c99b
            url_r = "http://ws.audioscrobbler.com/2.0/?method=artist.getsimilar&artist=%s&limit=%i&autocorrect=1&api_key=02c3301ab9e648c504edf4d7dc93c99b" %(artist, limit)
            page_r = urllib2.urlopen(url_r)
            contents_r = str(page_r.read())
            r_r = ET.fromstring(contents_r)
        except urllib2.HTTPError:
            return []

        global results_artist_name
        results_artist_name = []
        results_artist_url = []
        
        for artist in r_r.find('similarartists'):
            results_artist_name.append(artist.find('name').text)    
            results_artist_url.append(artist.find('url').text)

        event_listings = []
        new_events = []
        for artist in results_artist_name:
             if 'where' in facts:
                if 'city' in facts['where']:
                    if len(facts['where']['city'])>0:
                        city = facts['where']['city'][0]['item'][0]      #city is a tuple of (city,country)
                        country = facts['where']['city'][0]['item'][1]
                        new_events = self.find_local_events(self.answer, city, country)
             for event in new_events:
                 found = False
                 for e in event_listings:
                     if (e['title']==event['title']):
                         found = True
                         break
                 if found:
                     continue
     
                 event_listings.append(event)
   
        if len(event_listings) == 0:
            if len(results_artist_name)>0:
                x = random.randint(0,len(results_artist_name)-1)  
                return ["Unfortunately there are no local events I think you'd like but why not give " + results_artist_name[x] + " a listen ?"]
            else:
                return []
        else:
            return [self.output_events(event_listings, results_artist_name)]

    def find_local_events(self, artist, city, country):
        artist_formatted = artist.replace(" ", "%20")
        import urllib
        try:
            url_e = "http://api.bandsintown.com/artists/%s/events/recommended?format=xml&app_id=scikic&api_version=2.0&location=%s,%s&callback=showEvents" %(artist_formatted, city, country)
            page_e = urllib2.urlopen(url_e)
        except: # UnicodeEncodeError, urllib2.HTTPError: #TODO Handle this
            import sys
            print >>sys.stderr, "answer_music, URL failed to open: %s" % url_e
            return []
        contents_e = str(page_e.read())   
        r_e = ET.fromstring(contents_e)
        event_listings = []
        for event in r_e:
            title = event.find ('title').text
            title = title[:title.find(' in ')]
            datetime = event.find ('datetime').text
            formatted_datetime = event.find ('formatted_datetime').text
            location = event.find ('formatted_location').text
            event = ({  "location": location,"datetime": datetime,"formatted_datetime": formatted_datetime, "title": title})
            event_listings.append(event)
        return event_listings

    def output_events(self,event_listings, results_artist_name):
        insight_list = []
        limit = 5    
        event_listings = sorted(event_listings, key=lambda k: k['datetime'])
        for i,event in enumerate(event_listings):
            if i>=limit:
                break   
            x = random.randint(0,len(results_artist_name))      
            insight_list.append(str("There's a " + event_listings[i]["title"][:((event_listings[i]["title"]).find(" @ "))] + " concert at " + event_listings[i]["title"][(((event_listings[i]["title"]).find(" @ "))+3):] + " " + event_listings[i]["location"] + " on "+ event_listings[i]["formatted_datetime"] +". If you can't make it why not give " + results_artist_name[x] + " a listen ?"))
        return insight_list[0]
    

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
        return {'question':"What's your favourite band or artist? (be honest!)",'type':'text'} #TODO Rewrite
      
    def append_features(self,features,facts): 
        pass

    @classmethod
    def metaData(cls):
        return {'citation':'The <a href="bandsintown.com">bandsintown.com</a> API'}

    @classmethod
    def pick_question(self,questions_asked,facts,target):
        return 'favourite_artist','';

