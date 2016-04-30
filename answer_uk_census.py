import pymc as pm
import numpy as np
import pandas as pd
import re
import xml.etree.ElementTree as ET
import urllib2
import sqlite3
import answer as ans
import config
from StringIO import StringIO
from zipfile import ZipFile
from threading import Thread

import json

import logging

logging.basicConfig(filename=config.loggingFile, level=logging.DEBUG)


# Some helpful functions
def hasNumbers(strings):
    '''Returns true if any of the strings in the 'strings' array have a digit in them.'''
    for s in strings:
        if any(char.isdigit() for char in s):
            return True
    return False


def dict_to_array(data):
    '''Turns a hierarchy of dictionaries into a numpy array
    returns:
        - the numpy array
        - a list of lists of labels (each list records the labels on that dimension)
    example:
        res, labs = dict_to_array({'aged 3-5':{'males':{'rabbits':3,'dogs':4,'cats':1},'females':{'rabbits':3,'dogs':0,'cats':2}},'aged 0-2':{'males':{'rabbits':4,'dogs':2,'cats':1},'females':{'rabbits':1,'dogs':0,'cats':4}}})
        
        res   array([[[1, 4, 2],[4, 1, 0]],[[1, 3, 4],[2, 3, 0]]])
        labs  [['aged 0-2', 'aged 3-5'], ['males', 'females'], ['cats', 'rabbits', 'dogs']]
    '''

    res = []
    if not isinstance(data, dict):
        return data, []
    labels = []
    for e in data:
        if 'Total' not in e:
            lower_dict, lower_labels = dict_to_array(data[e])
            res.append(lower_dict)
            labels.append(e)
    if hasNumbers(labels):  # automatically sorts labels containing numbers by the numerical value of the first number.
        numbers = []
        for lab in labels:
            digits = re.search(r'\d+', lab)
            if digits != None:
                digits = digits.group()
            numbers.append(digits)
        numbers, labels, res = (list(t) for t in zip(*sorted(zip(numbers, labels, res))))
    lower_labels.insert(0, labels)
    return np.array(res), lower_labels


class UKCensusAnswer(ans.Answer):
    """Census answer: handles gender & age, etc"""

    dataset = 'ukcensus';
    religions = ['Christian', 'Buddhist', 'Hindu', 'Jewish', 'Muslim', 'Sikh', 'Other religion', 'No religion']
    religion_text = ['Christian', 'Buddhist', 'Hindu', 'Jewish', 'Muslim', 'Sikh', 'religious (but I do\'t know which)',
                     'of no religion']

    countryofbirth_labels = ['England', 'Ireland', 'Northern Ireland', 'Other countries', 'Scotland',
                             'United Kingdom not otherwise specified', 'Wales',
                             'Other EU: Accession countries April 2001 to March 2011',
                             'Other EU: Member countries in March 2001']  # for some reason this ONS query outputs a bunch of percentages too.

    transport = ['Taxi', 'Bicycle', 'On foot', 'Not in employment', 'Work mainly at or from home',
                 'Motorcycle, scooter or moped', 'Bus, minibus or coach', 'Train',
                 'Underground, metro, light rail, tram', 'Passenger in a car or van', 'Driving a car or van',
                 'Other method of travel to work']
    transport_text = ['take a taxi to work', 'cycle to work', 'go to work on foot', 'not be in work',
                      'mainly work from home', 'use a motorcycle to get to work', 'take the bus to work',
                      'take the train to work', 'use an underground or tram to get to work',
                      'get a lift in a car to work', 'drive to work', 'use an unusual method of travel to get to work']

    languages = ['African Language: Afrikaans', 'African Language: Akan', 'African Language: Amharic',
                 'African Language: Igbo', 'African Language: Krio', 'African Language: Lingala',
                 'African Language: Luganda', 'African Language: Shona', 'African Language: Somali',
                 'African Language: Swahili/Kiswahili', 'African Language: Tigrinya', 'African Language: Yoruba',
                 'Arabic', 'Caribbean Creole: Caribbean Creole (English-based)',
                 'East Asian Language: Cantonese Chinese', 'East Asian Language: Japanese',
                 'East Asian Language: Korean', 'East Asian Language: Malay', 'East Asian Language: Mandarin Chinese',
                 'East Asian Language: Tagalog/Filipino', 'East Asian Language: Thai',
                 'East Asian Language: Vietnamese', 'English (English or Welsh if in Wales)', 'French',
                 'Other European Language (EU): Bulgarian', 'Other European Language (EU): Czech',
                 'Other European Language (EU): Danish', 'Other European Language (EU): Dutch',
                 'Other European Language (EU): Estonian', 'Other European Language (EU): Finnish',
                 'Other European Language (EU): German', 'Other European Language (EU): Greek',
                 'Other European Language (EU): Hungarian', 'Other European Language (EU): Italian',
                 'Other European Language (EU): Latvian', 'Other European Language (EU): Lithuanian',
                 'Other European Language (EU): Maltese', 'Other European Language (EU): Polish',
                 'Other European Language (EU): Romanian', 'Other European Language (EU): Slovak',
                 'Other European Language (EU): Slovenian', 'Other European Language (EU): Swedish',
                 'Other European Language (non EU): Albanian',
                 'Other European Language (non EU): Serbian/Croatian/Bosnian',
                 'Other European Language (non EU): Ukrainian', 'Other European Language (non-national): Yiddish',
                 'Other UK language: Cornish', 'Other UK language: Gaelic (Irish)',
                 'Other UK language: Gaelic (Not otherwise specified)', 'Other UK language: Gaelic (Scottish)',
                 'Other UK language: Scots', 'Portuguese', 'Russian', 'Sign Language: Any Sign Communication System',
                 'South Asian Language: Bengali (with Sylheti and Chatgaya)', 'South Asian Language: Gujarati',
                 'South Asian Language: Hindi', 'South Asian Language: Malayalam', 'South Asian Language: Marathi',
                 'South Asian Language: Nepalese', 'South Asian Language: Pakistani Pahari (with Mirpuri and Potwari)',
                 'South Asian Language: Panjabi', 'South Asian Language: Sinhala', 'South Asian Language: Tamil',
                 'South Asian Language: Telugu', 'South Asian Language: Urdu', 'Spanish', 'Turkish',
                 'Welsh/Cymraeg (in England only)', 'West/Central Asian Language: Hebrew',
                 'West/Central Asian Language: Kurdish', 'West/Central Asian Language: Pashto',
                 'West/Central Asian Language: Persian/Farsi']

    languages_text = ['Afrikaans', 'Akan', 'Amharic', 'Igbo', 'Krio', 'Lingala', 'Luganda', 'Shona', 'Somali',
                      'Swahili', 'Tigrinya', 'Yoruba', 'Arabic', 'Caribbean Creole', 'Cantonese Chinese', 'Japanese',
                      'Korean', 'Malay', 'Mandarin Chinese', 'Tagalog/Filipino', 'Thai', 'Vietnamese', 'English',
                      'French', 'Bulgarian', 'Czech', 'Danish', 'Dutch', 'Estonian', 'Finnish', 'German', 'Greek',
                      'Hungarian', 'Italian', 'Latvian', 'Lithuanian', 'Maltese', 'Polish', 'Romanian', 'Slovak',
                      'Slovenian', 'Swedish', 'Albanian', 'Serbian, Croatian or Bosnian', 'Ukrainian', 'Yiddish',
                      'Cornish', 'Irish Gaelic', 'Gaelic', 'Scottish Gaelic', 'Scots', 'Portuguese', 'Russian',
                      'Sign Language', 'Bengali', 'Gujarati', 'Hindi', 'Malayalam', 'Marathi', 'Nepalese',
                      'Pakistani Pahari', 'Punjabi', 'Sinhala', 'Tamil', 'Telugu', 'Urdu', 'Spanish', 'Turkish',
                      'Welsh', 'Hebrew', 'Kurdish', 'Pashto', 'Farsi']

    households_text = ['Cohabiting couple (children have left home)', 'Cohabiting couple with children',
                       'Cohabiting couple, without children', 'Single person (children have left home)', 'Lone parent',
                       'Married couple (children have left home)', 'Married couple with children',
                       'Married couple, without children', 'Single person', 'Other households, with children',
                       'Retired couple', 'Retired single person', 'Students and retired']

    households_census_labels = ['One family only: Cohabiting couple: All children non-dependent',
                                'One family only: Cohabiting couple: Dependent children',
                                'One family only: Cohabiting couple: No children',
                                'One family only: Lone parent: All children non-dependent',
                                'One family only: Lone parent: Dependent children',
                                'One family only: Married or same-sex civil partnership couple: All children non-dependent',
                                'One family only: Married or same-sex civil partnership couple: Dependent children',
                                'One family only: Married or same-sex civil partnership couple: No children',
                                'One person household: Other', 'Other household types: With dependent children',
                                'One family only: All aged 65 and over', 'One person household: Aged 65 and over',
                                'Other household types: Other (including all full-time students and all aged 65 and over)']
    ##todo find out hello in every langauge      
    languages_hello = ['hallo']

    bedrooms = ['No bedrooms', '1 bedroom', '2 bedrooms', '3 bedrooms', '4 bedrooms', '5 or more bedrooms']
    bedrooms_text = ['no bedrooms', '1 bedroom', '2 bedrooms', '3 bedrooms', '4 bedrooms', '5 or more bedrooms']

    @classmethod
    def metaData(cls):
        data = {'religions': cls.religions,
                'religion_text': cls.religion_text,
                'transport': cls.transport,
                'transport_text': cls.transport_text,
                'languages': cls.languages,
                'languages_text': cls.languages_text,
                'households_text': cls.households_text,
                'households_census_labels': cls.households_census_labels,
                'countryofbirth_labels': cls.countryofbirth_labels,
                'bedrooms':cls.bedrooms,
                'bedrooms_text':cls.bedrooms_text,
                'citation': 'The <a href="http://www.ons.gov.uk/ons/guide-method/census/2011/census-data/ons-data-explorer--beta-/index.html">UK office of national statistics</a>'}
        return data

    def insights(self, inference_result, facts):
        # returns a dictionary of insights:
        # - inference_result: probability distributions of the features
        # - facts: a dictionary of 'facts' provided by the Answer classes      
        if self.prob_in_uk(facts) < 0.01:
            return {}  # we're not in the uk

        insights = {}
        if 'factor_age' in inference_result:
            if 'age' not in facts:  # there's nothing impressive about us guessing their exact age if we've already been told it.
                lower = inference_result['factor_age']['quartiles']['lower']
                upper = inference_result['factor_age']['quartiles']['upper']
                if upper == lower:  # if it's exact
                    msg = 'You are %d years old.' % lower
                    # compare to local area...

                else:
                    msg = 'You are aged between %d and %d.' % (lower, upper)
                insights['ukcensus_ages'] = msg

        if ('factor_gender' in inference_result):
            if 'gender' not in facts:  # there's nothing impressive about reporting their gender if they've told us it already.
                if (inference_result['factor_gender']['quartiles']['mean'] > 0.9):
                    insights['ukcensus_gender'] = 'You are female'
                elif (inference_result['factor_gender']['quartiles']['mean'] < 0.1):
                    insights['ukcensus_gender'] = 'You are male'


                    # 0 One family only: Cohabiting couple: All children non-dependent
                    # 1 One family only: Cohabiting couple: Dependent children
                    # 2 One family only: Cohabiting couple: No children <20%
                    # 3 One family only: Lone parent: All children non-dependent
                    # 4 One family only: Lone parent: Dependent children
                    # 5 One family only: Married or same-sex civil partnership couple: All children non-dependent
                    # 6 One family only: Married or same-sex civil partnership couple: Dependent children<<<<<<<<
                    # 7 One family only: Married or same-sex civil partnership couple: No children
                    # 8 One person household: Other <21%
                    # 9 Other household types: With dependent children
                    # 10 One family only: All aged 65 and over
                    # 11 One person household: Aged 65 and over
                    # 12 Other household types: Other (including all full-time students and all aged 65 and over)

        if ('household' in inference_result):
            household = inference_result['household']['distribution']
            nochildren = household[2] + household[7] + household[8] + household[10] + household[11] + household[12]
            if nochildren > 0.7:
                insights['ukcensus_household'] = "You don't have children living at home"
            if nochildren < 0.3:
                insights['ukcensus_household'] = "You have children"
            alone = household[3] + household[4] + household[8] + household[11] + household[12]
            if alone < 0.3:
                insights['ukcensus_household'] = "You are in a relationship and living with your partner/spouse."
            # TODO Check if the calc_probs_household method is always called.

            insights['ukcensus_household_list'] = (np.sum(self.households[0], (0, 1)) / 10.0).tolist()
            logging.info(self.households)

        if ('religion' in inference_result):
            rel = inference_result['religion']['distribution']
            listOfReligions = []
            for ratio, name in zip(rel, UKCensusAnswer.religion_text):
                if (ratio > 0.17):
                    listOfReligions.append(name)
            if (len(listOfReligions) > 1):
                relmsg = ', '.join(listOfReligions[:-1]) + ' or ' + listOfReligions[-1]
            else:
                relmsg = listOfReligions[0]
            insights['ukcensus_religion'] = " I think you are " + relmsg + "."

        ##Generate comparative insights...
        popd = np.mean(self.popdensity) * 100  # per hectare -> per sqr km
        ratio = popd / 413.0
        if (ratio > 1.5):
            insights[
                'ukcensus_popdensity'] = "Your neighbourhood has a population density of %d people per square kilometre, %0.1f times the average for England." % (
                round(popd), ratio)
        if (ratio < 0.5):
            insights[
                'ukcensus_popdensity'] = "Your neighbourhood has a population density of %d people per square kilometre, 1/%0.0f the average for England." % (
                round(popd), 1.0 / ratio)
        # oas = self.get_list_of_oas(facts)
        # localAgeDists = self.getDist(oas,UKCensusAnswer.getAgeDist) #TODO: We've already called this once. Need to cache.
        localAgeDists = self.localAgeDists
        nationalAgeDist = self.nationalAgeDist

        oa_probs = [1.0] * len(localAgeDists)
        if 'where' in facts:
            if 'ukcensus' in facts['where']:
                oa_probs = [it['probability'] for it in facts['where']['ukcensus']]  # get the list of OA probabilities

        d = np.zeros(101)
        for prob, dist in zip(localAgeDists, oa_probs):
            d = d + (np.array(dist) * prob) / len(oa_probs)

        popage = None
        if ('age' in facts):  # if we know the person's age we'll give the stat in proportion to them...
            age = facts['age']
            prop_younger = 1.0 * np.sum(d[0:age]) / np.sum(d)
            if prop_younger > 0.5:
                popage = "%d%% of people in your area are younger than you." % round(prop_younger * 100)
            else:
                popage = "%d%% of people in your area are older than you." % round((1 - prop_younger) * 100)
        else:  # otherwise we'll give it wrt 'half'
            halfway = np.sum(np.cumsum(d) <= np.sum(d) / 2)
            if (halfway < 40):
                popage = 'Half the people in your neighbourhood are younger than %d years old.' % halfway
            else:
                popage = 'Half the people in your neighbourhood are older than %d years old.' % halfway
        if popage is not None:
            insights['ukcensus_popage'] = popage

        national_traveltowork_probs = np.array(
            [0.00335523, 0.01853632, 0.06921536, 0.35500678, 0.03459344, 0.00520941, 0.04740108, 0.03333676, 0.02501549,
             0.03300255, 0.37115993, 0.00416765]);  # TODO Get this from the API

        # we need to roughly handle the smoothing so that rare modes don't get over represented
        national_traveltowork_probs = national_traveltowork_probs + (1.0 / 200)
        national_traveltowork_probs = national_traveltowork_probs / np.sum(national_traveltowork_probs)

        localratios = self.traveltowork_probs / national_traveltowork_probs
        maxnum = np.max(localratios)
        trans_type = UKCensusAnswer.transport_text[np.argmax(localratios)]
        insights[
            'ukcensus_traveltowork'] = 'People in your area are %0.0f times more likely to %s than the national average.' % (
            maxnum, trans_type)

        logging.info('self.countryofbirth')
        insights[
            'ukcensus_note'] = 'The probabilities provided by the insights have had smoothing/regularisation done to them to avoid p=0 scenarios.'
        cob = self.countryofbirth[0]
        logging.info(cob)
        logging.info(self.traveltowork_probs)
        insights[
            'ukcensus_countryofbirth'] = '%d%% of the people who live in your area were born in England, %d%% in Wales, Scotland and Northern Ireland. %d%% were born elsewhere in the EU while %d%% were from outside the EU.' % (
            round(cob[0] * 100.0), round((cob[2] + cob[4] + cob[6]) * 100.0), round((cob[1] + cob[7] + cob[8]) * 100.0),
            round(cob[3] * 100))
        insights['ukcensus_countryofbirth_list'] = cob.tolist()

        #  countryofbirth_labels = ['England', 'Ireland', 'Northern Ireland', 'Other countries', 'Scotland', 'United Kingdom not otherwise specified', 'Wales', 'Other EU: Accession countries April 2001 to March 2011', 'Other EU: Member countries in March 2001'] #for some reason this ONS query outputs a bunch of percentages too.
        
        active_languages = [UKCensusAnswer.languages_text[i] for i in np.nonzero(np.array(self.languages))[1]]
        langaugestring = ', '.join(active_languages[0:-1])
        if (len(active_languages) > 1):
            langaugestring += ' and ' + active_languages[-1]
        insights['ukcensus_languages'] = "Languages spoken in your area include " + langaugestring
        logging.info(UKCensusAnswer.languages_text[np.argmax(self.languages)])
        insights['ukcensus_language_list'] = self.languages[0].tolist()
        
        
        household_bedroom_probs = np.array([0.00244898,  0.11526287,  0.27649496,  0.41621374,  0.14389724,
         0.04568222])
        household_bedroom_probs = (household_bedroom_probs + (1.0 / 200)) / np.sum(household_bedroom_probs)

        lrat = self.household_bedrooms_probs/ household_bedroom_probs
        # maxno = np.max(lrat)
        bedroom_type = UKCensusAnswer.bedrooms_text[np.argmax(lrat)]
        insights['ukcensus_household_bedrooms'] = 'The Houses in your area are more likely to have %s on average' %  ( bedroom_type)
        logging.info(self.household_bedrooms_probs)

        return insights

    @classmethod
    def ONSapiQuery(cls, geoArea, dataSet):
        """Performs an API query to the ONS database, for the given geo area and dataset
        The data is stored in 'data' and is also converted into an N-dimensional 'matrix' using a hierarchy of dictionaries."""
        pathToONS = 'http://data.ons.gov.uk/ons/api/data/dataset/';
        apiKey = 'cHkIiioOQX';
        geographicalHierarchy = '2011STATH';
        url = ('%s%s/dwn.csv?context=Census&geog=%s&dm/%s=%s&totals=false&apikey=%s' %
               (pathToONS, dataSet, geographicalHierarchy, geographicalHierarchy, geoArea, apiKey))
        logging.info('Opening URL: %s' % url)
        response = urllib2.urlopen(url);
        xml_data = response.read();
        root = ET.fromstring(xml_data);
        href = root[1][0][0].text  # TODO: Need to get the path to the href using names not indices.
        url = urllib2.urlopen(href);
        zipfile = ZipFile(StringIO(url.read()))
        for filename in zipfile.namelist():
            if (filename[-3:] == 'csv'):
                data = pd.read_csv(zipfile.open(filename), skiprows=np.array(range(8)), skipfooter=1, header=0)

        # Gets it into a N-dimensional hierarchy of dictionaries
        values = data.ix[0, :]
        matrix = {}
        for col, v in zip(data.columns, values):
            c = col.split('~')

            if (len(c) >= 1):
                if ('Geographic ID' in c[0]):
                    continue
                if ('Geographic Area' in c[0]):
                    continue
                temp = matrix
                for ix in range(len(c)):

                    if ('Total' in c[ix]):
                        break

                    if c[ix] in temp:
                        temp = temp[c[ix]]
                    else:
                        if ix == len(c) - 1:
                            temp[c[ix]] = v
                        else:
                            temp[c[ix]] = {}
                            temp = temp[c[ix]]

        return data, matrix

    @classmethod
    def getAgeDist(cls, geoArea, returnList):
        """Gets the age distribution given the label of a particular geographical area,"""
        data, matrix = cls.ONSapiQuery(geoArea, 'QS103EW')  # QS103EW = age by year...
        data = data.T
        popages = data[0].values[3:]
        # return popages
        returnList[0] = popages  # now return via the argument so this can be called as a thread

    @classmethod
    def getHouseholdDist(cls, geoArea, returnList):
        """Gets the Household composition by age by sex; given the label of a particular geographical area"""
        data, mat = cls.ONSapiQuery(geoArea, 'LC1109EW')
        arr, labs = dict_to_array(mat)  # Convert the dictionary hierarchy to a numpy array
        # todo sort...
        # order = [[i for i,l in enumerate(labs[2]) if l==r][0] for r in cls.???] #?
        arr = np.array(arr)  # convert to numpy array
        arr = arr * 1.0
        for x in range(arr.shape[
                           0]):  # this finds the probability of being a particular household type given their age and sex.
            for y in range(arr.shape[1]):
                arr[x, y, :] += 1.0
                arr[x, y, :] = 1.0 * arr[x, y, :] / np.sum(1.0 * arr[x, y, :])
        returnList[0] = arr  # now return via the argument so this can be called as a thread

    @classmethod
    def getTravelToWorkDist(cls, geoArea, returnList):
        """Gets the way people travel to work; given the label of a particular geographical area"""
        data, mat = cls.ONSapiQuery(geoArea, 'QS701EW')
        arr, labs = dict_to_array(mat)  # Convert the dictionary hierarchy to a numpy array
        order = [[i for i, l in enumerate(labs[0]) if l == r][0] for r in
                 cls.transport]  # sort by the order we want it in.
        arr = np.array(arr)  # convert to numpy array
        arr = arr[order]
        arr = arr * 1.0
        arr += 1.0
        arr = 1.0 * arr / np.sum(1.0 * arr)
        returnList[0] = arr  # now return via the argument so this can be called as a thread

    @classmethod
    def getCountryOfBirth(cls, geoArea, returnList):
        """Gets the country of birth for an Output Area"""
        data, mat = cls.ONSapiQuery(geoArea, 'KS204EW')
        arr, labs = dict_to_array(mat)  # Convert the dictionary hierarchy to a numpy array
        order = [[i for i, l in enumerate(labs[0]) if l == r][0] for r in
                 cls.countryofbirth_labels]  # sort by the order we want it in.
        arr = np.array(arr)  # convert to numpy array
        arr = arr[order]
        arr = arr * 1.0
        arr += 1.0
        arr = 1.0 * arr / np.sum(1.0 * arr)
        returnList[0] = arr  # now return via the argument so this can be called as a thread

    @classmethod
    def getReligionDist(cls, geoArea, returnList):
        """Gets the religion distribution given the label of a particular geographical area"""
        data, mat = cls.ONSapiQuery(geoArea, 'LC2107EW')  # LC2107EW = religion by age, gender, etc
        arr, labs = dict_to_array(mat)  # Convert the dictionary hierarchy to a numpy array
        order = [[i for i, l in enumerate(labs[2]) if l == r][0] for r in
                 cls.religions]  # sort religion by the order we want it in.
        arr = np.array(arr)  # convert to numpy array
        arr = arr[:, :, order]  # put religions in correct order.
        arr = arr * 1.0
        for x in range(arr.shape[0]):
            for y in range(arr.shape[1]):
                arr[x, y, :] += 1.0
                arr[x, y, :] = 1.0 * arr[x, y, :] / np.sum(1.0 * arr[x, y, :])
        # gender is sorted by 'male', 'female', age by numerical-order and religion as specified in the cls.religions vector
        returnList[0] = arr  # now return via the argument so this can be called as a thread

    @classmethod
    def getPopDensity(cls, geoArea, returnList):
        data, mat = cls.ONSapiQuery(geoArea, 'QS102EW')  # LC2107EW = religion by age, gender, etc
        returnList[0] = mat['Density (Persons per hectare)']

    @classmethod
    def getLanguages(cls, geoArea, returnList):
        data, mat = cls.ONSapiQuery(geoArea, 'QS204EW')
        arr, labs = dict_to_array(mat)
        order = [[i for i, l in enumerate(labs[0]) if l == r][0] for r in cls.languages]
        arr = np.array(arr)  # convert to numpy array
        arr = arr[order]  # put in correct order.
        arr = arr * 1.0
        returnList[0] = arr
        
   @classmethod
    def getHouseholdBedroomsDist(cls, geoArea, returnList):
        data, mat = cls.ONSapiQuery(geoArea, 'QS411EW')
        arr, labs = dict_to_array(mat)  # Convert the dictionary hierarchy to a numpy array
        order = [[i for i, l in enumerate(labs[0]) if l == r][0] for r in
                 cls.bedrooms]  # sort by the order we want it in.
        arr = np.array(arr)  # convert to numpy array
        arr = arr[order]
        arr = arr * 1.0
        arr += 1.0
        arr = 1.0 * arr / np.sum(1.0 * arr)
        returnList[0] = arr  # now return via the argument so this can be called as a thread

    def __init__(self, name, dataitem, itemdetails, answer=None):
        """Constructor, instantiate an answer...
        Args:
          name: The name of this feature
          dataitem: 'agegender'
          itemdetails: None
          answer=None
        """
        self.dataitem = dataitem
        self.itemdetails = itemdetails
        self.featurename = name
        self.answer = answer

    def question_to_text(self):
        return "No questions"

    def get_list_of_oas(self, facts):
        oas = ['K04000001']  # if we don't know where we are, just use whole of England and Wales to get a prior.
        if 'where' in facts:
            if 'ukcensus' in facts['where']:
                oas = [it['item'] for it in facts['where']['ukcensus']]  # get the list of OA values
        return oas

    def get_list_of_oa_probs(self, facts):
        probs = np.array([1.0])  # if we don't know just reply with one.
        if 'where' in facts:
            if 'ukcensus' in facts['where']:
                probs = np.array([it['probability'] for it in facts['where']['ukcensus']])  # get the list of OA values
        probs = probs / probs.sum()  # shouldn't be necessary
        return probs

    def getDist(self, oas, target):
        """Get the distribution of something (depending on target) across the output areas passed"""
        threadData = []
        threads = []
        for oa in oas:
            data = [0]
            threadData.append(data)
            t = Thread(target=target, args=(oa, data))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        return [td[0] for td in threadData]

    # this just gets any other census data we're interested in
    def get_other_distributions(self, facts):
        oas = self.get_list_of_oas(facts)
        self.popdensity = self.getDist(oas, UKCensusAnswer.getPopDensity)
        self.languages = self.getDist(oas, UKCensusAnswer.getLanguages)

    def calc_probs_religion(self, facts):
        # returns p(oa|religion)
        oas = self.get_list_of_oas(facts)
        localDists = self.getDist(oas, UKCensusAnswer.getReligionDist)

        shape = localDists[0].shape
        self.rel_probs = np.empty((len(localDists), shape[0], shape[1], shape[2]))
        for i, p in enumerate(localDists):
            self.rel_probs[i, :, :, :] = p

    def calc_probs_household(self, facts):
        # returns p(oa|household)
        oas = self.get_list_of_oas(facts)
        self.households = self.getDist(oas, UKCensusAnswer.getHouseholdDist)

        shape = self.households[0].shape
        self.household_probs = np.empty((len(self.households), shape[0], shape[1], shape[2]))
        for i, p in enumerate(self.households):
            self.household_probs[i, :, :, :] = p

    def calc_probs_travelToWork(self, facts):
        # returns p(oa|travelToWork)
        oas = self.get_list_of_oas(facts)
        localDists = self.getDist(oas, UKCensusAnswer.getTravelToWorkDist)

        shape = localDists[0].shape
        self.traveltowork_probs = np.empty((len(localDists), shape[0]))
        for i, p in enumerate(localDists):
            self.traveltowork_probs[i, :] = p

    def calc_probs_countryOfBirth(self, facts):  # not actually called as only used for insights... TODO Delete?
        # returns p(oa|countryOfBirth)
        oas = self.get_list_of_oas(facts)
        localDists = self.getDist(oas, UKCensusAnswer.getCountryOfBirth)

        shape = localDists[0].shape
        self.countryofbirth = np.empty((len(localDists), shape[0]))
        for i, p in enumerate(localDists):
            self.countryofbirth[i, :] = p

    def calc_probs_age(self, facts):
        oas = self.get_list_of_oas(facts)
        oas.append('K04000001')  # last OA is whole of England+Wales
        data = self.getDist(oas, UKCensusAnswer.getAgeDist)
        localAgeDists = data[:-1]
        nationalAgeDist = data[-1]

        self.localAgeDists = localAgeDists
        self.nationalAgeDist = nationalAgeDist

        # we want p(postcode|age), which we assume is equal to p(output area|age)
        # if n = number of people in output area
        #   N = number of people
        #   na = number of people of age a in output area
        #   Na = number of people of age a
        #
        # p(output area|age) = p(age|output area) x p(output area) / p(age)
        #
        # we can write the three terms on the right as:
        #
        # p(age|output area) = na/n
        # p(output area) = n/N
        # p(age) = Na/N
        #
        # substituting in... na/n x n/N / (Na/N) = (na/N) / (Na/N) = na/Na
        # so localAgeDist/nationalAgeDist

        self.age_probs = np.zeros([101, len(localAgeDists), 2])  # age, in or not in the output area
        for i, dist in enumerate(localAgeDists):
            p = (0.0001 + dist) / nationalAgeDist
            self.age_probs[:, i, 0] = 1 - p
            self.age_probs[:, i, 1] = p
    
    
    def calc_probs_household_bedrooms(self, facts):
        # returns p(oa|bedrooms)
        oas = self.get_list_of_oas(facts)
        localDists = self.getDist(oas, UKCensusAnswer.getHouseholdBedroomsDist)
        shape = localDists[0].shape
        self.household_bedrooms_probs = np.empty((len(localDists), shape[0]))
        for i, p in enumerate(localDists):
            self.household_bedrooms_probs[i, :] = p

    def get_pymc_function_age(self, features):
        """Returns a function for use with the pyMC module:
        Args:
          features (dictionary): Dictionary of pyMC probability distributions.
        Returns:
          function (@pm.deterministic): outputs probability given the parameters.
        """
        probs = self.age_probs

        @pm.deterministic
        def givenAgeGender(age=features['factor_age'], oa=features['outputarea']):
            pAgeGender = probs
            return pAgeGender[age, oa]  # P(oa|age)

        return givenAgeGender

    def get_pymc_function_religion(self, features):
        probs = self.rel_probs

        @pm.deterministic
        def givenReligion(age=features['factor_age'], oa=features['outputarea'], gender=features['factor_gender']):
            pReligion = probs
            # the religion dataset is only split into a few bins of age, so handling that here:
            if (age < 16):
                age_p = 0
            elif (age < 25):
                age_p = 1
            elif (age < 35):
                age_p = 2
            elif (age < 50):
                age_p = 3
            elif (age < 65):
                age_p = 4
            elif (age < 75):
                age_p = 5
            else:
                age_p = 6
            return pReligion[oa, gender, age_p]  # P(religion|oa,gender,age)

        return givenReligion

    def get_pymc_function_household(self, features):
        probs = self.household_probs

        @pm.deterministic
        def givenHousehold(age=features['factor_age'], oa=features['outputarea'], gender=features['factor_gender']):
            pHousehold = probs
            # the household dataset is only split into a few bins of age, so handling that here:
            if (age < 16):
                age_p = 0
            elif (age < 25):
                age_p = 1
            elif (age < 35):
                age_p = 2
            elif (age < 50):
                age_p = 3
            else:
                age_p = 4
            return pHousehold[oa, gender, age_p]  # P(household|gender,age)

        return givenHousehold

    def prob_in_uk(self, facts):
        if 'where' in facts:
            if 'country' in facts['where']:
                for con in facts['where']['country']:
                    if con['item'] == 'gb':
                        return con['probability']
        return 0  # if it's not been found

    def append_features(self, features, facts, relationships, descriptions):
        """Alters the features dictionary in place, adds:
         - age
         - gender
         - this instance's feature
         
        Args:
          features (dictionary): Dictionary of pyMC probability distributions.
        
        Raises:
          DuplicateFeatureException: If an identically named feature already exists that clashes with this instance
        """

        # if we're not in the uk then we just skip
        if self.prob_in_uk(facts) < 0.01:
            logging.info('      probably not in the UK, skipping')
            return

        self.calc_probs_age(facts)
        self.calc_probs_religion(facts)
        self.calc_probs_household(facts)
        self.calc_probs_travelToWork(facts)
        self.calc_probs_countryOfBirth(facts)
        self.get_other_distributions(
            facts)  # this isn't necessary here as these methods don't assist with the features.
        self.calc_probs_household_bedrooms(facts)

        if not 'factor_age' in features:
            p = np.ones(101)  # flat prior
            p = p / p.sum()
            features['factor_age'] = pm.Categorical('factor_age', p);
        if not 'factor_gender' in features:
            p = np.array([.5, .5])  # approx flat
            features['factor_gender'] = pm.Categorical('factor_gender', p);
        if not 'outputarea' in features:
            probs = self.get_list_of_oa_probs(facts)
            features['outputarea'] = pm.Categorical('outputarea',
                                                    probs);  # if we don't have the ukcensus array then we just have a probability of one for one output area

        if self.featurename + "_age" in features:
            raise ans.DuplicateFeatureException(
                'The "%s" feature is already in the feature list.' % self.featurename + "_age");
        if "religion" in features:
            raise ans.DuplicateFeatureException('The "%s" feature is already in the feature list.' % "religion");

        features[self.featurename + "_age"] = pm.Categorical(self.featurename + "_outputarea",
                                                             self.get_pymc_function_age(features), value=True,
                                                             observed=True)
        features["religion"] = pm.Categorical("religion", self.get_pymc_function_religion(
            features))  # , value=True, observed=False)
        features["household"] = pm.Categorical("household", self.get_pymc_function_household(
            features))  # , value=True, observed=False)

        relationships.append({'parent': 'factor_age', 'child': 'outputarea'})
        relationships.append({'parent': 'factor_gender', 'child': 'outputarea'})
        relationships.append({'parent': 'religion', 'child': 'outputarea'})
        relationships.append({'parent': 'household', 'child': 'outputarea'})

        descriptions['factor_age'] = {'desc': 'Your age'}
        descriptions['factor_gender'] = {'desc': 'Your gender'}
        descriptions['religion'] = {'desc': 'Your religion'}
        descriptions['household'] = {'desc': 'Your household composition'}
        descriptions['outputarea'] = {'desc': 'Your geographic location'}
        descriptions[self.featurename + "_outputarea"] = {
            'desc': 'Probability of being in this output area given your features'}  # TODO Figure this out

    @classmethod
    def pick_question(cls, questions_asked, facts, target):
        return 'None', 'agegender'
