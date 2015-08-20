from shapely.geometry import Point
from shapely.geometry import Polygon

import pymc as pm
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
import shapefile
import config

class WhereAnswer(ans.Answer):
    """Where answer: handles figuring out what Output Areas the person might be in"""
    
    dataset = 'where';
    _landmarks = None;
    _boundaries = None;

    @classmethod
    def setup(cls,pathToData):
        #Data for the Output area shapes is from: http://census.edina.ac.uk/ukborders/easy_download/prebuilt/shape/infuse_oa_lyr_2011_clipped.zip
        #although similar data can also be found at: http://www.ons.gov.uk/ons/guide-method/geography/products/census/spatial/2011/index.html

        #If we don't have the file, download it.
        if not os.path.isfile("/tmp/psych_oa.zip"):
            print "Downloading census output area boundary shape data, this can take a long time..."
            url = 'http://census.edina.ac.uk/ukborders/easy_download/prebuilt/shape/infuse_oa_lyr_2011_clipped.zip'
            urllib.urlretrieve(url, "/tmp/psych_oa.zip")
        oa_zipfile = "/tmp/psych_oa.zip"

        #If it's not unzipped, unzip it.
        if not os.path.exists(pathToData+"/OA_shapes"):
            print "Unzipping"
            os.makedirs(pathToData+"/OA_shapes")
            zf = zipfile.ZipFile(oa_zipfile)
            for f in zf.infolist():
                zf.extract(f.filename,pathToData+"/OA_shapes")

        #If the boundaries are not yet in the database, put them there.
        if not os.path.isfile(pathToData + 'oa_boundaries.db'):  
            print "Adding boundaries to database, this can take a long time..."
            sf = shapefile.Reader(pathToData + "OA_shapes/infuse_oa_lyr_2011_clipped.shp")
            con = lite.connect(pathToData + 'oa_boundaries.db') 
            cur = con.cursor()
            cur.execute('DROP TABLE IF EXISTS boundaries')
            cur.execute('CREATE TABLE IF NOT EXISTS boundaries (id INTEGER PRIMARY KEY AUTOINCREMENT, bbox0 DECIMAL(9,6), bbox1 DECIMAL(9,6), bbox2 DECIMAL(9,6), bbox3 DECIMAL(9,6), shape VARCHAR(50000), record VARCHAR(50000));')
            cur.execute('CREATE INDEX bbox0 ON boundaries (bbox0);')
            cur.execute('CREATE INDEX bbox1 ON boundaries (bbox1);')
            cur.execute('CREATE INDEX bbox2 ON boundaries (bbox2);')
            cur.execute('CREATE INDEX bbox3 ON boundaries (bbox3);')

            cur.close()
            con.commit()
            a = []
            cur = con.cursor()

            for i in range(sf.numRecords):
                if ((i % 1000)==0):
                    print "%d of %d complete" % (i,sf.numRecords)
                    cur.close()
                    con.commit()
                    cur = con.cursor()
                shp = sf.shape(i)
                rec = sf.record(i)
                bbox= shp.bbox

                shpstring = json.dumps([[p[0],p[1]] for p in shp.points])
                recstring = json.dumps(rec)
                cur.execute('INSERT INTO boundaries (bbox0, bbox1, bbox2, bbox3, shape, record) VALUES (?,?,?,?,?,?)',(bbox[0],bbox[1],bbox[2],bbox[3],shpstring,recstring));
            cur.close()
            con.commit()
            con.close()

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

        if cls._boundaries is None:
            cls._boundaries = lite.connect(config.pathToData+'oa_boundaries.db')

    def __init__(self,name,dataitem,detail,answer=None):
        """Constructor, instantiate an answer associated with the distance from a landmark.
        We can later combine these using the facts dictionary to pass things between these classes...

        Args:
          name: The name of this feature
          dataitem: Can be either 'know' or 'distance' or 'where'
          landmark: The id of the landmark (for ids see the separate sql database TODO!)
          answer (default None): Either bool (if dataitem is 'know') or floating point (if dataitem is 'distance')
        """
        WhereAnswer.init_db()
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

    def question_to_text(self):
        if (self.dataitem=='landmark'):
            return {'question':"Do you know %s?" % WhereAnswer.get_place(self.detail)[0],'type':'select','options':['yes','no']}
        if (self.dataitem=='landmarkdist'):
            return {'question':"How far from your home is %s? (in kilometres, e.g. 2.3)" %  WhereAnswer.get_place(self.detail)[0],'type':'text'}

    def append_facts(self,facts,all_answers):
        items = [];
        for a in all_answers:
            if a.dataset=='where':
                if a.dataitem == 'landmarkdist':
                    placename, lat, lon, east, north = WhereAnswer.get_place(a.detail)
                    try:
                        dist = float(a.answer)
                    except ValueError:
                        continue
                    item = {'placename':placename, 'lat':lat, 'lon':lon, 'east':east, 'north':north, 'dist':dist*1000.} #distance was given in km - need in m
                    items.append(item)
        bbox = [0,0,0,0];
        if len(items)>0:    ####TODO TODO TODO HANDLE WHAT HAPPENS IF NO ITEMS
            bbox[0] = min([it['east'] for it in items]);
            bbox[1] = min([it['north'] for it in items]);
            bbox[2] = max([it['east'] for it in items]);
            bbox[3] = max([it['north'] for it in items]);
            margin = (bbox[3]+bbox[2]-bbox[1]-bbox[0])/4.
            bbox[0] -= margin
            bbox[1] -= margin
            bbox[2] += margin
            bbox[3] += margin
     
        cur = WhereAnswer._boundaries.cursor()
        results = cur.execute("SELECT record, shape FROM boundaries WHERE bbox2>? AND bbox0<? AND bbox3>? AND bbox1<?",(bbox[0],bbox[2],bbox[1],bbox[3]))
        shps = []
        recs = []
        for res in results:
            shp_points = json.loads(res[1])
            rec = json.loads(res[0])
            shps.append(Polygon(shp_points))
            recs.append(rec)
        cur.close()
        ps = []
        for shp in shps:
            prob = 0
            count = 0
            for e in np.arange(shp.bounds[0],shp.bounds[2],(shp.bounds[2]-shp.bounds[0])/5.):
                for n in np.arange(shp.bounds[1],shp.bounds[3],(shp.bounds[3]-shp.bounds[1])/5.):
                    pnt = Point(e,n)
                    if pnt.within(shp):
                        p = 1
                        for it in items:
                        #we want p(distance_to_each_landmark|location)
                        #if we find the average of these inside the OA, we'll have p(distance|OA) = SUM[ p(dist|loc)p(loc|OA) ]
                        #p(loc|OA) is either 1/number_of_locs_in_OA or 0.
                            dist = ((e - it['east'])**2 + (n - it['north'])**2)**.5                            
                            p *= norm.pdf(dist,it['dist'],it['dist']*0.1)
                            count += 1
                            #if (p>0.0001):
                            #    print "%0.0f %0.0f: %0.0f %0.0f, %0.2f-%0.2f (%0.5f)" % (e,n,it.east,it.north,dist,it.dist,p)
                        prob += p
            ps.append(prob/count)
       
        ps = np.array(ps)
        recs = np.array(recs)

        thresh = 0.0001
        if (np.sum(ps>thresh)>10) or (np.sum(ps>thresh)<1):
            temp = ps[:]
            if (len(temp)>10):
                temp.sort()
                thresh = temp[-10]
            else:
                thresh = 0 #include all of the OAs

        recs = recs[ps>thresh]
        rs = [r[0] for r in recs]
        ps = ps[ps>thresh]
    
        if len(ps)>0:
            facts['where'] = {'probabilities':ps, 'OAs':rs}
        else:
            facts['where'] = {'probabilities':np.array([1]), 'OAs':['K04000001']}


    def append_features(self,features,facts): 
        #this class doesn't directly create features. For example the census class will do this.
        pass

    @classmethod
    def process_answer(cls, dataitem, detail, old_answer):
        #this function may alter an answer to provide additional information, or reformat it into a standard format.
        pass
        
    @classmethod
    def pick_question(cls,questions_asked,facts,target):
    #Picks a question to ask, using previous questions asked.
        
        #TODO Check if lat/long is known
        if True:
            return 'None','None'
                
        city_details = {}
        city_details['latitude'] = 53.383611
        city_details['longitude'] = -1.466944

        outstanding_landmarks = []      #List of landmarks we know they know, but we don't know how far they are.           
        landmarks_done_already = [];    #List of landmarks we know the distance to already
        known_landmarks = [];           #similar to landmarks_done_already but only includes ones we have answers for
        known_distances = [];           #the distances to the landmarks (in the same order)

        for qa in questions_asked:
            if qa['dataset']=='where':          #if it is a landmark->where question
                if qa['dataitem'] == 'landmark':
                    if qa['answer']=='yes':
                        outstanding_landmarks.append(int(qa['detail']));
                    landmarks_done_already.append(int(qa['detail']));
                if qa['dataitem'] == 'landmarkdist':
                    outstanding_landmarks.remove(int(qa['detail']));
                    known_distances.append(float(qa['answer']));
                    known_landmarks.append(int(qa['detail']));
        
        if (len(outstanding_landmarks)==0):
            #pick a new landmark to ask about...
            items = cls.overpass_query(city_details['latitude'],city_details['longitude'],0.4,'tourism', 'museum')            
            new_item = None
            import trilateration
            items,p,entropy = trilateration.sortLandmarks(items,known_landmarks,known_distances,landmarks_done_already)
            if (len(items)>0):
                new_item = items[0]
            if new_item == None:
                #no more places to ask about
                return 'None', ''
            return 'landmark',new_item.id
        else:
            return 'landmarkdist',outstanding_landmarks[0]
            
