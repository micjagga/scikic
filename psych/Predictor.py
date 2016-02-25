
from nltk import *
from happierfuntokenizing_p2 import *
from sklearn import linear_model
from sklearn.externals import joblib
from sklearn import preprocessing
from sklearn.decomposition import PCA
from sklearn.preprocessing import Imputer
from sklearn import svm
import numpy as np


model_path = """.\model\ """



class Predictor(object):
    """
    Predictor class
    
    Attributes:
        model: the trained regression/classification model
        imp_X: the imputation transformer object for completing missing values in predictor (X) features
        imp_y: the imputation transformer object for completing missing values in target (y) features
        min_max_scaler_X: the scale transformer object used to scale predictor (X) features to a range
        min_max_scaler_y: the scale transformer object used to scale target (y) features to a range
        pca: the Principal component analysis (PCA) object used to reduce the dimension of predictor features 
        type: the model type: big5 scores or gender or age
    """
    
    def __init__(self, type):
        """Inits the predictor class """
        self.imp_X = Imputer(missing_values='NaN', strategy='mean', axis=0)
        self.imp_y = Imputer(missing_values='NaN', strategy='mean', axis=0)
        self.min_max_scaler_X = preprocessing.MinMaxScaler()
        self.min_max_scaler_y = preprocessing.MinMaxScaler()
        self.pca = None
        self.type = type
        if type in ['ope','con','ext','agr','neu']:
            self.model = linear_model.RidgeCV()
            self.scoreRange = (1,5)
        if type == 'age':
            self.model = linear_model.RidgeCV()
            self.scoreRange = (1,100)
        if type == 'gender':
            self.model = svm.LinearSVC()
            self.scoreRange = (0,1)
        
         
         
    def train(self, X, y, save=True, model_name=""):
        """ Train a predictor
        
        Args:
            X: observations, a N(number of samples)*M(number of features) matrix
            y: targets, a N*1 vector
            save: true: saving the model for future use; false: not saving
            model_name: saving name 
            
        Returns:
            self.model: a trained model 
        """
        # pre-processing X
        if X.ndim == 1:         # Reshape data either: X.reshape(-1, 1)- single feature or X.reshape(1, -1)-single sample.
            X = X.reshape(-1,1)
        # replace NaN (missing value) 
        self.imp_X.fit(X)
        X = self.imp_X.transform(X)
        
        # Scaling features to range: 0-1       
        self.min_max_scaler_X.fit(X)
        X = self.min_max_scaler_X.transform(X)

       
        pca_dim = min(round(float(len(X[0]))/2), round(float(len(X))/2))
        self.pca = PCA(n_components=pca_dim)
        self.pca.fit(X)
        X = self.pca.transform(X)
        
        # pre-processing y, do not perform pca
        if y.ndim == 1:
            y = y.reshape(-1,1)
            
        self.imp_y.fit(y)
        y = self.imp_y.transform(y)  
         
        self.min_max_scaler_y.fit(y) 
        y = self.min_max_scaler_y.transform(y)
        
        # fit regression/classification object
        if y.shape[1] == 1:
            y = np.squeeze(y)
        self.model.fit(X, y)
        
        # save 
        if save is True:
            if model_name == "":
                model_name = """Predictor_"""+self.type+""".pkl"""
            joblib.dump(self, model_path+model_name, compress=3) 
        
        return self
        
    def test(self, X):
        """ test a trained predictor model
        
        Args: 
            X: observations, a N(number of samples)*M(number of features) matrix
            
        Returns:
            y_pred: predicted targets 
        
        """

        if X.ndim == 1:
            X = X.reshape(1, -1)
            
        # replace NaN (missing value) transform matrix by training 
        X = self.imp_X.transform(X)
        # Scaling features to range: 0-1 using the transform matrix by training 
        X = self.min_max_scaler_X.transform(X)
        # Dimension reduction:pca
        X = self.pca.transform(X)
    
        # prediction
        y_pred = self.model.predict(X)
        
        # inverse transfer to the original range
        if y_pred.ndim == 1:
            y_pred = y_pred.reshape(-1, 1)
        y_pred = self.min_max_scaler_y.inverse_transform(y_pred)
        
        # check if the predicted value is not in the normal range
        for i in range(y_pred.size):
            if y_pred[i] < self.scoreRange[0]:
                y_pred[i] = self.scoreRange[0]
            if y_pred[i] > self.scoreRange[1]: 
                y_pred[i] = self.scoreRange[1]
            
        # Round the predicted value to the given number of decimals. 
        if self.type == 'age': y_pred = np.round(y_pred)
        if self.type in ['ope','con','ext','agr','neu']: y_pred = np.round(y_pred, 2)
        
        y_pred = y_pred.flatten().tolist()
        
        return y_pred