
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
import sys
import time
import logging
import pymc3 as pm
import theano
import theano.tensor as t
import scipy as sp


from StringIO import StringIO
from zipfile import ZipFile


class MovieAnswer(ans.Answer):
    """Movielens answer: handles seen, ratings, etc associated with movie rankings"""
    #class database connections for movielens
    _movielens = None
    dataset = 'movielens';


    @classmethod
    def setup(cls,pathToData):
        """Creates databases and files, downloads data, and populates the datafiles"""
        url = 'http://files.grouplens.org/datasets/movielens/ml-1m.zip'

        if not os.path.isfile("/tmp/psych_movielens/ml-1m.zip"):
            print "Downloading "+url
            if not os.path.exists('/tmp/psych_movielens'):
                os.makedirs('/tmp/psych_movielens')
            urllib.urlretrieve(url, "/tmp/psych_movielens/ml-1m.zip")
            movielens_zipfile = "/tmp/psych_movielens/ml-1m.zip"
            print "Opening movielens zip file"
            zf = zipfile.ZipFile(movielens_zipfile)
            for f in zf.infolist():
                zf.extractall("/tmp/psych_movielens/")

        if not os.path.isfile(pathToData+'movielens.db'):
            print "Saving movielens data to movielens.db"
            ratings = pd.read_table('/tmp/psych_movielens/ml-1m/ratings.dat',sep='::',names=['user','movie','rating','time'],encoding='utf-8');
            users = pd.read_table('/tmp/psych_movielens/ml-1m/users.dat',sep='::',names=['user','gender','age','occupation','zip'],encoding='utf-8');
            movies = pd.read_table('/tmp/psych_movielens/ml-1m/movies.dat',sep='::',names=['movie','title','genre'],encoding='utf-8');
            db = sa.create_engine('sqlite:///'+pathToData+'movielens.db');
            con = db.raw_connection(); #need raw connect to allow access to rollback, see: http://stackoverflow.com/questions/20401392/read-frame-with-sqlalchemy-mysql-and-pandas
            con.connection.text_factory = str;
            ratings.to_sql('ratings',con,index=False,if_exists='replace');
            users.to_sql('users',con,index=False,if_exists='replace');
            movies.to_sql('movies',con,index=False,if_exists='replace');
            con.close();    
            con = sqlite3.connect(config.pathToData+'movielens.db')
            cur = con.cursor()
            cur.execute('CREATE INDEX user_ratings ON ratings (user);');
            cur.execute('CREATE INDEX user_users ON users(user);');
            cur.execute('CREATE INDEX movie ON ratings(movie);');
            cur.execute('CREATE INDEX age ON users(age);');

    @classmethod
    def init_db(cls):
        """Connect to movielens database

        Note:
          Only intended to be called by the constructor of an instance
        """
        if cls._movielens is None:
            conn = sqlite3.connect(config.pathToData+'movielens.db')
            cls._movielens = conn.cursor()

    def get_movie_name(self,movie):
        """Returns the name of the movie with id passed
        """ 
        c_moviename = MovieAnswer._movielens.execute("SELECT title FROM movies WHERE movie=?;",(movie,));
        for r in c_moviename:
            return r[0]
        return "[name unknown]";
    
    def __init__(self,name,dataitem,movie,answer=None):
        """Constructor, instantiate an answer associated with seeing a movie.

        Args:
          name: The name of this feature
          dataitem: Can be either 'seen' or 'rated'
          movie: The id of the movie (for ids see movielens database)
          answer (default None): Either bool (if dataitem is 'seen') or integer (if dataitem is 'rated')
        """
        MovieAnswer.init_db()
        self.dataitem = dataitem
        self.movie = movie
        self.answer = answer
        self.featurename = str('movie_'+dataitem+'_'+self.get_movie_name(movie))
        
    def question_to_text(self):
        m = self.get_movie_name(self.movie)
    	if (self.dataitem=='seen'):
            return {'question':"Have you seen %s? (yes or no)" % m,'type':'select','options':['yes','no']};
        if (self.dataitem=='rate'):
            return {'question':"Rate %s on a scale of 1 to 5" % m,'type':'select','option':['5','4','3','2','1']};
        return "Some sort of movie question..."
        
    def calc_probs(self):
        self.probs = np.zeros([101,2,2]) #age, gender, seen or not seen

        ages = {};
        c_ages = MovieAnswer._movielens.execute("SELECT DISTINCT(age) FROM users;") #Maybe could do all this with some outer joins, but couldn't get them working.    
        ages_list = []
        for i,r in enumerate(c_ages):
            ages[r[0]]=i
            ages_list.append(r[0])

        for genderi,gender in enumerate(['M','F']):
            nSeen = np.zeros(len(ages))
            nTotal = np.zeros(len(ages))

            c_movie = MovieAnswer._movielens.execute("SELECT users.age,count(*) FROM users JOIN ratings ON users.user=ratings.user WHERE ratings.movie=? AND users.gender=? GROUP BY users.age ORDER BY users.age;",(self.movie,gender));
            for r in c_movie:
                nSeen[ages[r[0]]] = r[1]  #find p(seen,age,gender)
            c_all = MovieAnswer._movielens.execute("SELECT users.age,count(*) FROM users WHERE users.gender=? GROUP BY users.age ORDER BY users.age;",(gender));
            for r in c_all:
                nTotal[ages[r[0]]] = r[1] #find p(age,gender)
            pSeen = 1. * nSeen / nTotal #p(s|age,gender) = p(s,age,gender)/p(age,gender)
            pNotSeen = 1. * (nTotal-nSeen) / nTotal #p(not s|age,gender) = [p(age,gender)-p(s,age,gender)]/p(age,gender)

            ages_list = np.array(ages_list)
#the movielens timestamps are between
# 26 Apr 2000 # and 28 Feb 2003.
# average: 27 Sep 2001, 
            from datetime import datetime
            currentYear = datetime.now().year
            ageDiff = (currentYear-2001) #the people are now older by this age difference
            ages_list = ages_list + ageDiff
         #   print ages_list
            dSeen = ans.distribute_probs(pSeen,ages_list[1:])
            dNotSeen = ans.distribute_probs(pNotSeen,ages_list[1:])
            self.probs[:,genderi,0] = dNotSeen
            self.probs[:,genderi,1] = dSeen

    def get_pymc_function(self,features):
        """Returns a function for use with the pyMC module, either:
          - p(seen|age,gender)
          - p(rating|age,gender)

        Args:
          features (dictionary): Dictionary of pyMC probability distributions.
        
        Returns:
          function (@pm.deterministic): outputs probability given the parameters.
        """
        self.calc_probs() #calculates probs and puts them in self.probs
        probs = self.probs
        @pm.deterministic    
        def seenGivenAgeGender(age=features['factor_age'],gender=features['factor_gender']):
            pSeen_AgeGender = probs
            return pSeen_AgeGender[age][gender]
        return seenGivenAgeGender
    
    def append_features(self,features,facts,relationships,descriptions):
        """Alters the features dictionary in place, adds:
         - age
         - gender
         - this instance's feature
         
        Args:
          features (dictionary): Dictionary of pyMC probability distributions.
        
        Raises:
          DuplicateFeatureException: If an identically named feature already exists that clashes with this instance
        """
        #age: 0-100
        if not 'factor_age' in features:
            p = np.ones(101) #flat prior
            p = p/p.sum()
            features['factor_age'] = pm.Categorical('factor_age',p);
        #gender: male or female
        if not 'factor_gender' in features:
            #flat prior
            features['factor_gender'] = pm.Categorical('factor_gender',np.array([0.5,0.5]));
        if self.featurename in features:
            raise DuplicateFeatureException('The "%s" feature is already in the feature list.' % self.featurename);
        seen = hf.true_string(self.answer);
        features[self.featurename]=pm.Categorical(self.featurename, self.get_pymc_function(features), value=seen, observed=True)
        relationships.append({'parent':'factor_gender', 'child':self.featurename})
        relationships.append({'parent':'factor_age', 'child':self.featurename})
        
        descriptions["factor_gender"] = {'desc':'Your gender'}
        descriptions["factor_age"] = {'desc':'Your age'}        
        descriptions[self.featurename] = {'desc':'Probability of being in this blockgroup given other features'}                
        
    @classmethod
    def pick_question(self,questions_asked,facts,target):
        #temporary list of films I'VE seen!
        films = [(2541, 'Cruel Intentions (1999)'),
         (969, 'African Queen, The (1951)'),
         (1200, 'Aliens (1986)'),
         (1704, 'Good Will Hunting (1997)'),
         (3006, 'Insider, The (1999)'),
         (2470, 'Crocodile Dundee (1986)'),
         (3704, 'Mad Max Beyond Thunderdome (1985)')];
        filmn = random.randint(0,len(films)-1);
        movie_index = films[filmn][0];
        movie_name = films[filmn][1];
        return 'seen',movie_index

    @classmethod
    def metaData(cls):
        return {'citation':'The <a href="http://files.grouplens.org/datasets/movielens">movielens</a> database'}

    def ReadMovieLens():
        """
        """
        logging.info('reading data')
        data_set = np.zeros([np.max(data.user),np.max(data.movie)])
        w = np.zeros([np.max(data.user),np.max(data.movie)])
        for d in data.values:
            data_set[d[0]-1,d[1]-1]=d[2]
            w[d[0]-1,d[1]-1]=1
       
        subsetSizeUsers = 200
        subsetSizeMovies = 100
        smalldata = data_set[0:subsetSizeUsers,0:subsetSizeMovies]
        smallw = w[0:subsetSizeUsers,0:subsetSizeMovies]
        
    #     try:
    #         data = pd.read_csv(fname)
    #     except IOError as err:
    #         print str(err)
    #         url = 'https://gist.github.com/macks22/b40ac9c685e920ad3ca2'
    #         print 'download from: %s' % url
    #         sys.exit(DATA_NOT_FOUND)

    #     # Calculate split sizes.
    #     logging.info('splitting train/test sets')
    #     n, m = data_set.shape           # # users, # movies
    #     N = n * m                   # # cells in matrix
    #     test_size = N / 100          # use 10% of data as test set
    #     train_size = N - test_size  # and remainder for training

    #     # Prepare train/test ndarrays.
    #     train = data_set.copy()
    #     test = np.ones(data_set.shape) * np.nan

    #     # Draw random sample of training data to use for testing.
    #     tosample = np.where(~np.isnan(train))        # only sample non-missing values
    #     idx_pairs = zip(tosample[0], tosample[1])    # zip row/col indices
    #     indices = np.arange(len(idx_pairs))          # indices of row/col index pairs
    #     sample = np.random.choice(indices, replace=False, size=test_size)  # draw sample

    #     # Transfer random sample from train set to test set.
    #     for idx in sample:
    #         idx_pair = idx_pairs[idx]         # retrieve sampled index pair
    #         test[idx_pair] = train[idx_pair]  # transfer to test set
    #         train[idx_pair] = np.nan          # remove from train set

    #     # Verify everything worked properly
    #     assert(np.isnan(train).sum() == test_size)
    #     assert(np.isnan(test).sum() == train_size)

    #     # Return the two numpy ndarrays
        return smalldata, smallw


    def build_pmf_model(train, alpha=2, dim=10, std=0.01):
        """Construct the Probabilistic Matrix Factorization model using pymc3.
        Note that the `testval` param for U and V initialize the model away from
        0 using a small amount of Gaussian noise.
        :param np.ndarray train: Training data (observed) to learn the model on.
        :param int alpha: Fixed precision to use for the rating likelihood function.
        :param int dim: Dimensionality of the model; rank of low-rank approximation.
        :param float std: Standard deviation for Gaussian noise in model initialization.
        """
        # Mean value imputation on training data.
        train = train.copy()
        nan_mask = np.isnan(train)
        train[nan_mask] = train[~nan_mask].mean()

        # Low precision reflects uncertainty; prevents overfitting.
        # We use point estimates from the data to intialize.
        # Set to mean variance across users and items.
        alpha_u = 1 / train.var(axis=1).mean()
        alpha_v = 1 / train.var(axis=0).mean()

        logging.info('building the PMF model')
        n, m = train.shape
        with pm.Model() as pmf:
            U = pm.MvNormal(
                'U', mu=0, tau=alpha_u * np.eye(dim),
                shape=(n, dim), testval=np.random.randn(n, dim) * std)
            V = pm.MvNormal(
                'V', mu=0, tau=alpha_v * np.eye(dim),
                shape=(m, dim), testval=np.random.randn(m, dim) * std)
            R = pm.Normal(
                'R', mu=t.dot(U, V.T), tau=alpha * np.ones(train.shape),
                observed=train)

        logging.info('done building PMF model')
        return pmf


