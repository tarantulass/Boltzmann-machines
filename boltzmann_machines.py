# -*- coding: utf-8 -*-
"""Boltzmann_machines.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1tV7-JuX3S2twJjGIKDbfBe71ew1A6ZgA
"""

from google.colab import drive
drive.mount('/content/drive')

import pandas as pd
import numpy as  np
import torch
import torch.nn as nn
import torch.nn.parallel
import torch.optim as optim
import torch.utils.data
from torch.autograd import Variable

movies = pd.read_csv('/content/drive/MyDrive/ml-1m/movies.dat',sep='::',header=None,engine='python',encoding='latin-1')
user = pd.read_csv('/content/drive/MyDrive/ml-1m/users.dat',sep='::',header=None,engine='python',encoding='latin-1')
ratings = pd.read_csv('/content/drive/MyDrive/ml-1m/ratings.dat',sep='::',header=None,engine='python',encoding='latin-1')

movies.head()
#movie id , #movie name , #genre
#movie id will be fed for training instead of whole movie name since we are not producing a NLP model.

ratings.head()
#user no. , #movie id , # ratings, #timestamp(don't care->to be removed)

#base ->train and test ->test dataset
#always remember we have data in csv but we perform calculation after converting them into numpy arrays.
training_set = pd.read_csv('/content/drive/MyDrive/ml-100k/u1.base',delimiter='\t',header=None)
#delimiter tab should not be replaced by sep delimeter is best to be used here.

training_set.head()
#the same scheme followed user no., movie id, movie rating, timestamp

#train test split ratio can be determined via
len(training_set)
#this clearly portrays that out of 100k entries  80k are for training i.e 4:1 train:test

training_set = np.array(training_set,dtype='int')

testing_set = pd.read_csv('/content/drive/MyDrive/ml-100k/u1.test',delimiter='\t',header=None)

testing_set = np.array(testing_set,dtype='int')

""" Making 2 matrices for training and testing and we get the rating of  amovie form the user id.
 i.e user id as row index and movie  id as columns and the corresponding rating as data (split is random).
"""

#since the spit is random hence it may happen that the last user may be in test
user_count = max(max(training_set[:,0]),max(testing_set[:,0]))
movie_count = max(max(testing_set[:,1]),max(training_set[:,1]))
print(user_count, movie_count)

#Now we create a more comprehensive matrix representation of the datatset.
#since we have to develop a recommender system based on ratings hence movie rating should be the features, target to be predicted is rating.
#creating a function is the best method to tackle the situation where we have to convert multiple instances of data into tensors.
def convert(dataset):
  entry = []
#instead of making 2 D tensor it is easier to get a list(for appending entries)->numpy(for managing the ratings based on movies indexes)->tensor!!
  for i in range(1,user_count+1):
    movie_rating = np.zeros(movie_count)
    movie_id = dataset[:,1][dataset[:,0]==i]
    rating = dataset[:,2][dataset[:,0]==i]
    movie_rating[movie_id - 1] = rating
    entry.append(list(movie_rating))
  return entry
  #the user id 1 has index 0 in this list of lists

training_set = convert(training_set)
testing_set = convert(testing_set)

#we can build the arrays by numpy arrays also but pytorch tensors(there are tnsorflow tensors also!!) provide extra features and enhanced performance.
training_set = torch.FloatTensor(training_set)
#now this provides us a tensor i.e a multidimensional array of same dtype and tensor requires list of list as an argument not numpy arrays.
testing_set = torch.FloatTensor(testing_set)
#point to be noted the thing we are creating is a recommender system and the best recommender system in action is in googlecolab u find that code are already recommended !!!

#since we will use a binary encoding scheme for producing a recommender system hence for the movies which were not seen by a user i.e 0 rated have to be assigned another value so that it does not interfere with the model
training_set[training_set==0] = -1#here just like pandas it has this feature since the entire matrix has same dtype
training_set[training_set==1] = 0
training_set[training_set==2] = 0
training_set[training_set==3] = 1
training_set[training_set==4] = 1
training_set[training_set==5] = 1
#the movie rating scheme followed is 1 for >=3

testing_set[testing_set==0] = -1
testing_set[testing_set==1] = 0
testing_set[testing_set==2] = 0
testing_set[testing_set==3] = 1
testing_set[testing_set==4] = 1
testing_set[testing_set==5] = 1

"""Our objective is to create a recommender system using restricted boltzmann machine for rating the movies which were not rated. Here we cannot take genre as features instead rating are features with their movie ids since there will be no way to remap the genre to the original movie."""

# The parameters involved in RBM are hidden nodes, visible nodes, weights, Bias for probability given hidden node
class RBM():  # keep first letter capital convention
    def __init__(self, visible, hidden):  # it defines the argument we feed in a constructor of the class
        self.W = torch.randn(hidden, visible)  # weights
        self.h_bias = torch.randn(1, hidden)  # tensor needs 2 dimensions necessarily hence written like this.
        self.v_bias = torch.randn(1, visible)

    # probability that a hidden node is activated given the data in visible nodes.
    def sample_hidden(self, v):
        v_dotW = torch.mm(v, self.W.T)
        activation = v_dotW + self.h_bias.expand_as(v_dotW)
        prob_vtoh = torch.sigmoid(activation)
        return prob_vtoh, torch.bernoulli(prob_vtoh)

    # we are constructing a Bernoulli RBM hence the second thing that is returned contains all the activated hidden nodes.
    def sample_visible(self, h):
        h_dotW = torch.mm(h, self.W)  # no transpose
        prob_htov = h_dotW + self.v_bias.expand_as(h_dotW)
        return torch.sigmoid(prob_htov), torch.bernoulli(torch.sigmoid(prob_htov))

    # Now contrastive divergence
    def train(self, v0, vk, ph0, phk):
        self.W += torch.mm(ph0,v0) - torch.mm(phk,vk)
        self.v_bias += torch.sum((v0 - vk), 0)
        self.h_bias += torch.sum((ph0 - phk), 0)

visible = len(training_set[0])#number of movies i.e features
hidden = 100#completely chosen at will since it is based on the hidden patterns it draws from the data.
#number of hidden nodes corresponds to number of features we want to detect!!
batch_size = 100#here the total number of batches is again a hyper-parameter, total 943 examples so 943/64 batch in an epoch
rbm = RBM(visible,hidden)

# training of model
# no gradient descent hence no learning rate used
epochs = 10
s = 0.
for epoch in range(1, epochs + 1):
    training_loss = 0
    for id in range(0, user_count - batch_size, batch_size):
        vk = training_set[id:id + batch_size]
        v0 = training_set[id:id + batch_size]
        ph0, _ = rbm.sample_hidden(v0)
        # this is for getting only the first returning value of the function.
        # this is the gibbs sampling here visible nodes are reconstructed i.e first first hidden then visible
        for k in range(10):
            _, hk = rbm.sample_hidden(vk)
            _, vk = rbm.sample_visible(hk)

        # now update the weights after epoch
            vk[v0 < 0] = v0[v0 < 0]  # this is added so that the training is only done on the rated movies
        phk, _ = rbm.sample_hidden(vk)
        rbm.train(v0, vk, ph0, phk)
        training_loss += torch.mean(torch.abs(v0[v0 > 0] - vk[v0 > 0]))  # this is for rated movies only
        s += 1.
    print(f'train loss is {training_loss / s} for epoch {epoch}')

# testing of model
# no gradient descent hence no learning rate used
s = 0.
testing_loss = 0
for id in range(user_count):
  vk = training_set[id:id + 1]
  v0 = testing_set[id:id + 1]
  # this is for getting only the first returning value of the function.
  # this is the gibbs sampling here visible nodes are reconstructed i.e first first hidden then visible
  if len(v0[v0>=0])>0:
    _, hk = rbm.sample_hidden(vk)
    _, vk = rbm.sample_visible(hk)
          #k can be removed since it is only 1 step no kstep process!!
          # now update the weights after epoch
  #phk,vk are weigths which were updated previously now no training hence not required!!
    testing_loss += torch.mean(torch.abs(v0[v0 > 0] - vk[v0 > 0]))  # this is for rated movies only
    s += 1.
print(f'testing loss is {testing_loss / s}')

