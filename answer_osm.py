import numpy as np
import answer as ans
import json
import urllib2
import urllib
import overpy
from operator import itemgetter, attrgetter, methodcaller
import pyproj
import zipfile,os.path,os
import sqlite3 as lite
from scipy.stats import norm
import socket
import config

class OSMAnswer(ans.Answer):
    """OSM answer: handles open street map"""
    
    dataset = 'osm';
    _landmarks = None;

    @classmethod
    def setup(cls,pathToData):
       pass
    @classmethod
    def init_db(cls):
        """Connects (and creates if necessary) database of landmarks

        Note:
          Only intended to be called by the constructor of an instance
        """
        if cls._landmarks is None:
            cls._landmarks = lite.connect(config.pathToData+'landmarks.db')
            lmcur = cls._landmarks.cursor()
            cls._landmarks.execute('CREATE TABLE IF NOT EXISTS landmarks (landmark_id INTEGER, name VARCHAR(255), lat DECIMAL(9,6), lon DECIMAL(9,6), east DECIMAL(9,6), north DECIMAL(9,6), querylat DECIMAL(9,6), PRIMARY KEY (landmark_id));')
            cls._landmarks.execute('CREATE TABLE IF NOT EXISTS landmark_queries (querylat DECIMAL(9,6));')
            lmcur.close()
            cls._landmarks.commit()

    def __init__(self,name,dataitem,detail,answer=None):
        """Constructor, instantiate an answer associated with the distance from a landmark.
        We can later combine these using the facts dictionary to pass things between these classes...

        Args:
          name: The name of this feature
          dataitem: Can be either 'know' or 'distance' or 'where'
          landmark: The id of the landmark (for ids see the separate sql database TODO!)
          answer (default None): Either bool (if dataitem is 'know') or floating point (if dataitem is 'distance')
        """
        OSMAnswer.init_db()
        self.dataitem = dataitem
        self.detail = detail #depends on what precise question we're asking.
        self.answer = answer
        self.featurename = name
        
    #ask for all OSM features near lat,lon (within an area degreesDist from lat,lon, with key and value as specified
    #e.g. items = overpass_query(latitude, longitude ,0.1 ,'tourism', 'museum')
    @classmethod
    def overpass_query(cls,lat,lon,degreesDist,key,value):
  #      print "Checking for cache hit..."
        lmcur = cls._landmarks.cursor()        
        lmcur.execute("SELECT COUNT(*) FROM landmark_queries WHERE querylat=?;",(lat,))
        data = lmcur.fetchone();
        lmcur.close()
        #if (data[0]>0):
        if (False):
#            print "Cache hit found"
            lmcur = cls._landmarks.cursor()
            results = lmcur.execute("SELECT landmark_id, name, lat, lon, east, north FROM landmarks WHERE querylat=?;", (lat,));
            items = []
            for data in results:
                item = overpy.Node(data[0],data[2],data[3]);
                item.east = data[4]
                item.north = data[5]
                item.tags = {'name':data[1]}
                items.append(item)
            lmcur.close()
        else:
   #         print "Cache missed"
   #         print "OVERPASS QUERY"
   #         print lat,lon,degreesDist,key,value
            api = overpy.Overpass()
            #To do adjust addition to take into account latitude
            s = lat-degreesDist
            n = lat+degreesDist
            e = lon+degreesDist
            w = lon-degreesDist #doesn't handle 180 point well, don't run near poles.
            
            query = """<osm-script>
              <union>
                <query type="node">
                  <has-kv k="%s" v="%s" />
                  <bbox-query e="%0.2f" n="%0.2f" s="%0.2f" w="%0.2f"/>
                </query>
                <query type="way">
                  <has-kv k="%s" v="%s" />
                  <bbox-query e="%0.2f" n="%0.2f" s="%0.2f" w="%0.2f"/>      
                </query>
              </union>
              <union>
                <item/>
                <recurse type="down"/>
              </union>
              <print/>
            </osm-script>""" % (key,value,e,n,s,w,key,value,e,n,s,w)
            result = api.query(query)
            items = [];
            for way in result.ways:
                if ('name' in way.tags):
                    way.nodes[0].tags = way.tags
            for node in result.nodes:
                if (key in node.tags) and ('name' in node.tags):
                    item = node;
                    items.append(item)
                    
            for item in items:
                item.distsqr = (float(item.lat) - lat)**2 + (float(item.lon) - lon)**2;

            items =sorted(items, key=attrgetter('distsqr'))
            osgb36=pyproj.Proj("+init=EPSG:27700");
            for item in items:
                [e,n] = osgb36(item.lon,item.lat)
                item.east = e
                item.north = n

            lmcur = cls._landmarks.cursor()        
            lmcur.execute("INSERT INTO landmark_queries (querylat) VALUES (?);",(lat,)) #Note that this has now been cached. Some queries might not have any rows created, hence why a second table is needed.
            for item in items:
                lmcur.execute("INSERT OR IGNORE INTO landmarks (landmark_id, name, lat, lon, east, north, querylat) VALUES (?,?,?,?,?,?,?);",(item.id,item.tags['name'],float(item.lat),float(item.lon),float(item.east),float(item.north),lat)) #TODO Speed up, combine into one query
            lmcur.close()
            cls._landmarks.commit()


      #  print "Done."
     #   for i in items:
     #       print i
        return items

    @classmethod
    def get_place(cls,lm_id):
    #Use the landmark id to get info of the landmark. This database was previously populated by the pick_question method
        lmcur = cls._landmarks.cursor()
        lmcur.execute("SELECT name, lat, lon, east, north FROM landmarks WHERE landmark_id=?",(lm_id,)) #TODO sanitise the source of self.detail?
        data = lmcur.fetchone();
        lmcur.close()
        if data==None:
            return "No idea where..."
        #TODO Handle if it doesn't manage a cache hit
        placename = data[0]
        lat = data[1]
        lon = data[2]
        east = data[3]
        north = data[4]
        return placename, lat, lon, east, north

    @classmethod
    def pick_question(cls,questions_asked,facts,target):
    #Picks a question to ask, using previous questions asked.
        return 'None','None'
        

    def insights(self,inference_result,facts):
        #returns a list of insights:
        # - inference_result: probability distributions of the features
        # - facts: a dictionary of 'facts' provided by the Answer classes      
        
        insightlist = []
        insightlist.append("OSM Answer system online")
        ##Generate comparative insights...
        if 'where' in facts:
            if 'latlong' in facts['where']:
                lat = facts['where']['latlong'][0]['item'][0]
                lon = facts['where']['latlong'][0]['item'][1]
                #insightlist.append([lat,lon])
                
                items = self.overpass_query(lat, lon ,0.1 ,'tourism', 'museum')
                insightlist.append("There are %d museums in your town or area." % len(items))
        return insightlist

