import pymc as pm
import numpy as np
import pandas as pd
import re
import xml.etree.ElementTree as ET
import urllib2
import sqlite3 as lite
import answer as ans
import urllib
import zipfile,os.path,os
import sqlalchemy as sa
import pandas as pd
import config
import csv
from StringIO import StringIO
from zipfile import ZipFile
import shutil
from integrate_location import parseCountry

class PostalAnswer(ans.Answer):
    """Postal answer: handles getting the postcode or zipcode, or equivalent"""

        #class 'static' holder for the geo database
    _geo = None
    _us_geo = None
    dataset = 'postal';

    _states=['Mo29','Al01','Ak02','Az04','Ar05','Ca06','Co08','Ct09','De10','Dc11','Fl12','Ga13','Hi15','Id16','Il17','In18','Ia19','Ks20','Ky21','La22','Me23','Md24','Ma25','Mi26','Mn27','Ms28','Mt30','Ne31','Nv32','Nh33','Nj34','Nm35','Ny36','Nc37','Nd38','Oh39','Ok40','Or41','Pa42','Ri44','Sc45','Sd46','Tn47','Tx48','Ut49','Vt50','Va51','Wa53','Wv54','Wi55','Wy56']


    @classmethod
    def setup(cls,pathToData):
        print "Setting up UK POSTCODE database"
        cls.setup_postcodes(pathToData)
        print "Setting up US ZIPCODE database"
        cls.setup_zipcodes(pathToData)

    @classmethod
    def setup_postcodes(cls,pathToData):
        """Creates databases and files, downloads data, and populates the datafiles"""
        #Sets up postcode->Outputarea data, from http://www.ons.gov.uk/ons/guide-method/geography/products/census/lookup/other/index.html
        url = 'https://geoportal.statistics.gov.uk/Docs/Lookups/Postcodes_(Enumeration)_(2011)_to_output_areas_(2011)_to_lower_layer_SOA_(2011)_to_middle_layer_SOA_(2011)_to_local_authority_districts_(2011)_E+W_lookup.zip'

        print "Creating postcode database in %s" % pathToData

        #New dataset (includes Scotland and Northern Ireland), from https://geoportal.statistics.gov.uk/geoportal/catalog/search/resource/details.page?uuid={A33B0569-97E2-4F44-836C-B656A6D082B6}    
        if os.path.isfile(pathToData+'geo.db'):
            print "geo.db exists, skipping"
            return

        url = 'https://geoportal.statistics.gov.uk/Docs/PostCodes/NSPL_MAY_2015_csv.zip'
        print "Downloading "+url
        if os.path.exists('/tmp/psych_postcodes'):
            shutil.rmtree('/tmp/psych_postcodes')
        os.makedirs('/tmp/psych_postcodes')
        urllib.urlretrieve(url, "/tmp/psych_postcodes/postcodes.zip")
        postcode_zipfile = "/tmp/psych_postcodes/postcodes.zip"

        print "Opening postcodes.zip"
        zf = zipfile.ZipFile(postcode_zipfile)
        for f in zf.infolist():       
            zf.extract(f.filename,"/tmp/psych_postcodes")

        print "Importing CSV file to sqlite"  #note:Switched from using pandas as it ran out of memory.
        

        csvfile = '/tmp/psych_postcodes/Data/NSPL_MAY_2015_UK.csv'
        csvReader = csv.reader(open(csvfile), delimiter=',', quotechar='"')
        conn = lite.connect(pathToData+'geo.db')

        conn.execute('CREATE TABLE IF NOT EXISTS geo (pcd TEXT, oa11 TEXT, lsoa11 TEXT, lat REAL, long REAL)')
        firstRow = True
        n = 0
        for row in csvReader:
            n+=1
            if (n%500000==0):
                print "     %d rows imported" % n                
            if firstRow:
                firstRow = False
                continue
            conn.execute('INSERT INTO geo (pcd, oa11, lsoa11, lat, long) values (?, ?, ?, ?, ?)', (row[0],row[9],row[24],row[32], row[33]))

        print "     Creating indices"        
        conn.execute('CREATE INDEX pcds ON geo(pcd)')
        conn.execute('CREATE INDEX oa11s ON geo(oa11)')

        csvfile = '/tmp/psych_postcodes/Documents/LSOA (2011) names and codes EW as at 12_12.txt'
        print "Importing names data to sqlite from %s" % csvfile
        csvReader = csv.reader(open(csvfile), delimiter='\t', quotechar='"')

        conn.execute('CREATE TABLE IF NOT EXISTS names (lsoa11 TEXT, name TEXT)')

        firstRow = True
        n = 0
        for row in csvReader:
            n+=1
            if (n%10000==0):
                print "     %d rows imported" % n           
            if firstRow:
                firstRow = False
                continue
            name = row[1]
            lsoa = row[0]
            name = ' '.join(name.split(' ')[0:-1])
            conn.execute('INSERT INTO names (lsoa11, name) values (?, ?)', (lsoa,name))

        print "     Creating indices"
        conn.execute('CREATE INDEX names_lsoa11s ON names(name)')
        conn.execute('CREATE INDEX names_names ON names(lsoa11)')
        conn.commit()
        conn.close()
        print "Database connection closed"

    @classmethod
    def setup_zipcodes(cls,pathToData):
        dbfile = pathToData + 'us_geo.db'
        if os.path.isfile(dbfile):
            print "%s exists, skipping" % dbfile
            return
        conn = lite.connect(dbfile)
        conn.execute('CREATE TABLE IF NOT EXISTS us_geo (zcta5 TEXT, state TEXT, county TEXT, tract TEXT, blockgroup TEXT, cntyname TEXT, zipname TEXT, pop10 INTEGER, afact FLOAT)')
        conn.text_factory = str
        for state in cls._states:
            stateid = state[2:4]
            print "State %s:" %state
            print "    Requesting processed CSV file"
            url = 'http://mcdc.missouri.edu/cgi-bin/broker?_PROGRAM=websas.geocorr12.sas&_SERVICE=bigtime&site=OSEDA%%2FMCDC%%2FUniv.+of+Missouri&state=%s&g1_=zcta5&g2_=bg&wtvar=pop10&nozerob=1&csvout=1&lstfmt=txt&namoptf=b&namoptr=b&title=s1&counties=&metros=&places=&distance=&y0lat=&x0long=&locname=&nrings=&r1=&r2=&r3=&r4=&r5=&r6=&r7=&r8=&r9=&r10=&lathi=&latlo=&longhi=&longlo=&_DEBUG=0' % (state)
            html = urllib2.urlopen(url).read()    
            csvfile = re.findall('href="([^"]*)"',html)[0]
            csvfile = 'http://mcdc.missouri.edu' + csvfile
            print "    Downloading CSV file (%s)" % csvfile
            urllib.urlretrieve(csvfile,filename='geocorr12.csv')
            print "    Adding to database"
            csvReader = csv.reader(open('geocorr12.csv'), delimiter=',', quotechar='"')
            for i,row in enumerate(csvReader):
                if i<2:
                    continue
                conn.execute('INSERT INTO us_geo (zcta5,state,county,tract,blockgroup,cntyname,zipname,pop10,afact) VALUES (?,?,?,?,?,?,?,?,?)', (row[0],stateid,row[1],row[2],row[3],row[4],row[5],row[6],row[7])) 
            print "    Committing to database"
            conn.commit()
        print "Complete"
        conn.close()

    @classmethod
    def init_db(cls):
        """Connects to the geo database.

        Note:
          Only intended to be called by the constructor of an instance
        """
 #       print "Loading geographical dataset";
        if cls._geo is None:
            conn = lite.connect(config.pathToData+'geo.db')
            cls._geo = conn.cursor()
        if cls._us_geo is None:
            conn = lite.connect(config.pathToData+'us_geo.db')
            cls._us_geo = conn.cursor()

     
    @classmethod
    def adjustcode(cls,postcode):
        """Formats postcode into 7 character format, so "a1 2cd" becomes "A1  2CD" or "Gl54 1AB" becomes "GL541AB"."""
        postcode = postcode.upper()
        res = re.search('([A-Z]{1,2}[0-9]{1,2}) *([0-9][A-Z]{2})',postcode);
        if (res==None):
            return postcode #TODO can't understand it, just send it back, need to do something better, throw an exception?
        groups = res.groups()
        if len(groups)==2:
            first = groups[0]
            last = groups[1]
            middle = " "*(7-(len(first)+len(last)))
            return first+middle+last
        return postcode #TODO can't understand it, just send it back, need to do something better, throw an exception?
    
    def __init__(self,name,dataitem,itemdetails,answer=None):
        """Constructor, instantiate an answer

        Args:
          name: The name of this feature
          dataitem: 'postcode' or 'zipcode'
          itemdetails: Details about the item
          answer (default None): Either a string if the item's the postcode or...
        """
        PostalAnswer.init_db()
        self.dataitem = dataitem
        self.itemdetails = itemdetails #not sure this is used yet
        self.featurename = name
        self.answer = answer

    def question_to_text(self):
        if (self.dataitem=='postcode'):
            return {'question':"What's your postcode?",'type':'text'}
        if (self.dataitem=='zipcode'):
            return {'question':"What's your zip code?",'type':'text'}
        
    def append_facts(self,facts,all_answers): #TODO Move all the census stuff into integrate_location maybe?
        if (self.answer==None):
            return #nothing to append
        if (self.dataitem=='postcode'):
            self.append_facts_postcode(facts)
        if (self.dataitem=='zipcode'):
            self.append_facts_zipcode(facts)
        if (self.dataitem=='country'):
            country = parseCountry(self.answer)
            if country!=None:
                if 'where' not in facts:
                    facts['where'] = {}
                facts['where']['country'] = [{'item':country,'probability':1.}]

    def append_facts_zipcode(self,facts):       
            zipcode = self.answer;
            c_blockgroups = PostalAnswer._us_geo.execute("SELECT blockgroup, tract, county, state, cntyname, zipname, pop10, afact FROM us_geo WHERE zcta5=? LIMIT 999;",(zipcode,));
            block = None;
            if 'where' not in facts:
                facts['where'] = {};            
            cities = {}
            for r in c_blockgroups:
                blockgroup = r[0]
                tract = r[1]
                tract = tract[0:4]+tract[5:] #the database has the decimal point in the tract. This puts it into the 6digit form: 1234.01 -> 123401
                county = r[2][2:] #the database holds the state concatenated with the county: 12+345 -> 12345. This strips the first two character -> 345
                state = r[3]
                cntyname = r[4]
                zipname = r[5]
                pop = r[6]
                afact = r[7]
                if zipname in cities:
                    cities[zipname] += 1
                else:
                    cities[zipname] = 1
                #geolabel = state+county+tract+blockgroup
                if 'uscensus' not in facts['where']:
                    facts['where']['uscensus'] = [];
                facts['where']['uscensus'].append({'probability':afact, 'level':'blockgroup', 'item':[state,county,tract,blockgroup]})
            
            if len(cities)>0:
                facts['where']['city'] = []
            for city in cities:
                p = 1.0*cities[city]/len(facts['where']['uscensus'])
                facts['where']['city'].append({'item':(city,'us'),'probability':p})
            facts['where']['country'] = [{'item':'us','probability':1.}]  #TODO Check what country names we should be using

    def append_facts_postcode(self,facts):       
            postcode = PostalAnswer.adjustcode(self.answer);

            c_oa = PostalAnswer._geo.execute("SELECT oa11, geo.lsoa11 as lsoa, name, lat, long FROM geo, names WHERE pcd=? AND names.lsoa11=geo.lsoa11;",(postcode,));
            oa = None;
            for r in c_oa:
                oa = r[0]
                lsoa = r[1]
                city = r[2]
            if 'where' not in facts:
                facts['where'] = {};
            if (oa != None):
                facts['where']['ukcensus'] = [{'probability':1., 'level':'oa', 'item':oa}]
                facts['where']['city'] = [{'item':(city,'uk'),'probability':1.}]
            facts['where']['country'] = [{'item':'gb','probability':1.}]

    @classmethod
    def pick_question(cls,questions_asked,facts,target):   
        maxp = 0
        country = ''
        if 'where' in facts:
            if 'country' in facts['where']:
                for con in facts['where']['country']:                    
                    if maxp<con['probability']:
                        maxp = con['probability']
                        country = con['item']       
        if parseCountry(country)=='gb':
            return 'postcode', ''
       
        import sys
        print >>sys.stderr, facts
        print >>sys.stderr, country
        print >>sys.stderr, parseCountry(country)
        if parseCountry(country)=='us':
            return 'zipcode', ''

        return 'None', 'None' #we can't ask this yet.
