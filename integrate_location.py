#Method to add a location to the facts dictionary:
#
# Although lots of potential ways exist to record our location, the facts{'where'} dictionary is restricted to:
# cities
# countries
# OAs
# LSOAs
# tracts
# blocks
#
#
#Examples:
#add_location(countries=['UK'])
#add_location(cities=[('Reading','UK'),('Sheffield','UK')],[0.2,0.8])
#add_location(blocks=[1012434552,1012434553,1012434554,1012434555])
#add_location(oas=['A123124','E2323452'],probabilities=[0.4,0.6])
#add_location(tracts=[101243,101244],probabilities=[0.1,0.9])
#add_location(lsoas=['A345234','E265452'],probabilities=[0.4,0.6]) #these are larger than OAs
#
#Currently unsupported:
#add_location(postcodes=['EH1 2FV']) 
#add_location(zipcodes=['MN12002'])
#add_location(latlongs=[(51.231,-1.23,0.1)] -- lat,long,standard-deviation
#
#Only set one item at once.
import numpy as np
def add_location(facts, countries=None, cities=None, blocks=None, tracts=None, latlongs=None, oas=None, lsoas=None, probabilities=None):
    if 'where' not in facts:
        facts['where'] = {}

    if countries!=None:
        #if we're just setting the country, then we can't set anything else with any meaning (maybe latlongs?)
        if 'country' not in facts:
            facts['where']['country'] = []
        if probabilities==None:
            probabilities = 1.0*np.ones(len(countries))/len(countries)
        for con,prob in zip(countries,probabilities):
            facts['where']['country'].append({'item':parseCountry(con),'probability':prob})
        #TODO Set lat/long
        #TODO INTEGRATE WITH WHAT'S ALREADY SET!

    if cities!=None:
        if 'country' not in facts:
            facts['where']['country'] = []
        if 'city' not in facts:
            facts['where']['city'] = []
        if probabilities==None:
            probabilities = 1.0*np.ones(len(cities))/len(cities)
        countries = []
        for cit,prob in zip(cities,probabilities):
            facts['where']['city'].append({'item':cit,'probability':prob})
            countries.append(cit[1])
        cons = {}
        for con in countries:
            if con in cons:
                cons[con]+=1./len(cities)
            else:
                cons[con] = 0
        for con in cons:
            facts['where']['country'].append({'item':con,'probability':cons[con]})
        #TODO Set lat/long
        #TODO INTEGRATE WITH WHAT'S ALREADY SET!

def parseCountry(text): #turns arbitrary strings of country names to country codes #TODO
    #could use from nltk.metrics.distance import edit_distance
    #edit_distance('united kingdom','UNITED KINGDOM')
    country = text; #'EARTH' #don't know!

    #strings are ISO 3166 CODES
    strings = {'gb':['united kingdom','uk','u.k.','g.b.','gb','great britain','gbr','england','scotland','wales','northern ireland','britain','united kingdom of great britain and northern ireland','united kingdom of great britain'], 'us':['united states','us','usa','united states of america','america','the states','us of a','u.s.','u.s.a.'], 'de':['germany','de','deu','deutsch','deutschland','federal republic of germany']}
    for con in strings:
        if text.lower() in strings[con]:
            country = con
    return country #e.g. will return 'gb'

def displayCountry(code): #turns a country code back into a full name
    return code
