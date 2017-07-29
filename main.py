#!/usr/bin/env python3.6
# TODO
from csv import DictReader
from itertools import islice

from typing import Dict

# sleep = []
# with open('2017.csv', 'r') as fo:
#     reader = DictReader(fo)
#     for line in islice(reader, 0, 10):
#         sleep
#         print(line)

import numpy as np
import matplotlib.pyplot as plt
from numpy import genfromtxt
import matplotlib.pylab as pylab

pylab.rcParams['figure.figsize'] = (32.0, 24.0)
pylab.rcParams['font.size'] = 10



dimensions = 3 # Number of dimensions to reduce to
jawboneDataFile = "/L/Dropbox/backups/jawbone/2017.csv" # Data File Path

jawboneDataFeatures = "Jawbone/features.csv" # Data File Path
featureDesc: Dict[str, str] = {}
for x in genfromtxt(jawboneDataFeatures, dtype='unicode', delimiter=','):
    featureDesc[x[0]] = x[1]

def filterData_Jawbone (data):
    #Removes null data (and corresponding features)
    data = data[0:,:]
    # for i in range(16):
    #     data = np.delete(data, 0, 1)
    # print(data)
    h, w = data.shape
    data = np.where((data == ''), 0, data)
    allZero = [np.all(np.delete([0 if col[i] == '' else col[i] for col in data], [0]).astype(float)
              == 0) for i in range(w)]
    allSame = [np.all(np.delete([0 if col[i] == '' else col[i] for col in data], [0]).astype(float)
              == np.delete([0 if col[i] == '' else col[i] for col in data], [0]).astype(float)[0]) for i in range(w)]
    empty = np.logical_or(allZero, allSame)
    n = [i for i in range(np.array(empty).size) if empty[i] == True]
    return np.delete(data, n, axis=1)

dataAll = filterData_Jawbone(genfromtxt(jawboneDataFile, dtype='unicode', delimiter=','))
features = dataAll[0]
features = [
    's_light', # 'light sleep' from app
    's_awake', # 'woke up' from app (how many times you were awake)
    's_deep' # 'sound sleep' from app
]
# TODO filter more carefully...


def getIndex (data, features):
    index = []
    for f in features:
        index.append(np.where((data[0] == f) == True)[0][0])
    return index

def getFeatures (data, features):
    h, w = data.shape
    index = getIndex(data, features)
    extracted = np.zeros(h-1)
    for i in index:
        temp = np.delete([0 if col[i] == '' else col[i] for col in data], [0]).astype(float)
        temp /= np.amax(temp)
        extracted = np.vstack((extracted, temp))
    extracted = np.delete(extracted, 0, 0)
    return extracted


# print(dataAll)
data = getFeatures(dataAll, features)


def remNull(x, y):
    nx = np.where(x == 0)
    ny = np.where(y == 0)
    nulli = np.concatenate((nx[0], ny[0]))
    x = np.delete(x, nulli, 0)
    y = np.delete(y, nulli, 0)
    return x, y

def calculateVar(x, y) -> float:
    x, y = remNull(x,y)
    if len(x) == 0:
        # TODO needs date?
        print("Warning")
        return 0.0 # TODO ???
    meanX = np.mean(x)
    meanY = np.mean(y)
    n = float(x.shape[0])
    print(n)
    return ((1/n)*(np.sum((x-meanX)*(y-meanY))))
    # return ((1/(n + 1))*(np.sum((x-meanX)*(y-meanY)))) # TODO fixme..

def calculateCov(data):
    h, w = data.shape
    cov = np.zeros([h, h])

    for i in range(h):
        for j in range(h):
            cov[i][j] = calculateVar(data[i], data[j])
    return cov


# In[119]:
# a = np.array([[1, 2, 3], [1, 2, 3]])
# print(a)
# print(calculateCov(a))
# print(np.cov(a))
# print("VAR")
# print(np.var(a[0]))

# print("DATA")
# print(data)

# print("NPCOV")
# print(np.cov(data))

# cov = calculateCov (data)
# print("COV")
# print(cov)
cov = np.cov(data) # TODO ??? 


# In[120]:


def plotFeatures (title, label1, label2, feature1, feature2):
    plt.scatter(feature1, feature2)
    
    plt.title(title)
    plt.xlabel(label1)
    plt.ylabel(label2)
    
    plt.xlim(0, 1)
    plt.ylim(0, 1)
    
    plt.show()
    
def plotMatrix(data):
    r, c = data.shape
    c=2
    fig = plt.figure()
    plotID = 1
    for i in range(c):
        for j in range(c):
            f1 = getFeature(data, data[0][i])
            f2 = getFeature(data, data[0][j])
            ax = fig.add_subplot( c, c, plotID )
            ax.scatter(f1, f2)
            ax.set_title(data[0][i] + ' vs ' + data[0][j])
            ax.axis('off')
            plotID += 1
    plt.show()
    
def plotMatrix1(features, data):
    for f in features:
        print(f"{f}: {featureDesc[f]}")
    r, c = data.shape
    fig = plt.figure()
    plotID = 1
    for i in range(r):
        for j in range(r):
            ax = fig.add_subplot( r, r, plotID )
            x,y = remNull(data[i], data[j])
            ax.scatter(x, y, s=2)
            ax.set_title(features[i] + ' vs ' + features[j], fontsize=15)
            ax.tick_params(axis='x', which='major', labelsize=8)
            ax.tick_params(axis='y', which='major', labelsize=8)
#             ax.set_xlim(0,1)
#             ax.set_ylim(0,1)
            plotID += 1
    plt.show()


# In[121]:


# plotMatrix1(features, data)


# In[ ]:


def rankF(features, cov):
    n = len(features)
    eigenV = np.linalg.eig(cov)
    eigVal = np.matrix(eigenV[0])
    eigVec = np.matrix(eigenV[1])
    order  = (n-1) - np.argsort(eigVal)
    
    rankFeatures = np.empty(n, dtype='<U30') # TODO
    # print(rankFeatures.shape)
    for i in range(n):
        rankFeatures[i] = features[(np.where(order == i)[1][0])]
    
    return rankFeatures, eigVal, eigVec

# print(features)
# rankFeatures, eigVal, eigVec = rankF(features, cov)
rankFeatures = features
# print(rankFeatures)
# print(len(rankFeatures))


r1, r2 = 0, dimensions
selectedFeatures = features
# selectedFeatures = np.take(rankFeatures, np.arange(r1, r2))
selectedData = getFeatures(dataAll, selectedFeatures)
# plotFeatures('111', 'f1', 'f2', selectedData[0], selectedData[1])

plotMatrix1(rankFeatures, selectedData)
