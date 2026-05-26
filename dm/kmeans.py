# Algorithm
#
# Kmeans(data, k, gnuplot)
#   Centroids = Randomly select k points
#   Do:
#    Assign points to nearest Centroids
#    For each cluster
#     Calculate centroid
#    Assign points to nearest Centroids
#    Until no new assignements
#
import random
import time
import dm.stat as st
import matplotlib.pyplot as plt
import math

# Cluster data into k clusters
# data: a list of objects. Each object is a list. The first attribute is the cluster label
# k: int, the number of clusters
def kmeans(data, k, plotFunction = None):
    # randomly select k points as the initial cluster centers
    centroids = selectRandom(k, len(data[0])-1, 0, 10)

    sse = -1
    for i in range(5): # max 5 iterations
        # assign data points to closest centroids
        assignToCluster(data, centroids)

        # re-calculate centroids
        centroids, nsse = calcCentroids(data,k)
        print(nsse)
        if plotFunction is not None:
            plotFunction(centroids, data)
            time.sleep(2)

        if sse == nsse:
            break
        sse = nsse
    return centroids

def plotClusters(centroids, data):

    c = ['r','g','b','c','m','y','k']

    plt.clf()
    plt.axis([0, 8, 0, 8])
    # centroids
    i = 0
    cr = 'r'
    for cp in centroids:
        i += 1
        cr = c[i]
        plt.plot(cp[1], cp[2], cr + 'x', ms=20, mew=3)
        # plot all points for this centroid

        # data points
        x = []
        y = []
        for p in data:
            if p[0] == cp[0]:
                x += [p[1]]
                y += [p[2]]
        plt.plot(x, y, cr + 'o')

    plt.draw()  # this will stop and display the current clusters

# re-calculate centroid from data points that are assigned
def calcCentroids(data, k):
    d = len(data[0])
    centroids = []

    sse = 0
    for i in range(k):
        # scan the entire database and
        # add up all points belonging to cluster i
        c = st.zeros(d)
        c[0] = i # centroid ID
        n = 0
        cd = []
        for p in data:
            if( p[0] == i ):
                cd.append(p)
                addVectors(c, p)  # c = c + p
                n += 1

        # now divide c with the number of points to get the centroid
        if n > 0:
            divVector(c,n)  # c = c/n
        else:
            # oops the cluster is empty, let's randomly pick a point
            c = selectRandom(1, d-1, 0, 10)[0]
            c[0] = i

        # we have a new centroid point for cluster i
        centroids.append(c)

        sse += calcSSE(c, cd)
    return centroids, sse

def calcSSE(c,d):
    sse = 0
    for p in d:
        d = st.disimilarity(c,p)
        sse += math.pow(d,2)
    return sse

def addVectors(c,p):
  for i in range(len(c)-1):
    c[i+1] += p[i+1]

def divVector(c,n):
    for i in range(len(c)-1):
        c[i+1] = c[i+1]/n

def assignToCluster(data, centroids):
    changed = False
    for p in data:
        i = findClosest(p, centroids)
        if p[0] != i:
            p[0] = i
            changed = 1
    return changed

# find find the closest centroid from p
def findClosest(p, centroids):
    minD = -1
    cidx = -1
    for c in centroids:
        d = st.disimilarity(c, p)
        if minD < 0 or d < minD:
            minD = d
            cidx = c[0]
    return cidx

# randomly select k points
def selectRandom(k, dimension, vmin, vmax):
    centroids = []
    for i in range(k):
        p = [i]  # label

        for j in range(dimension):
            p.append( random.random() * (vmax - vmin) + vmin )

        centroids.append(p)
    return centroids

if __name__ == '__main__':
    # create test data set
    sigma = 0.5
    NumPoints = 20
    db1 = st.genDataXY(NumPoints, sigma, 2, 2) # return a list of lists. Each list [label, x0, x1,....]
    db2 = st.genDataXY(NumPoints, sigma, 6, 6)
    db3 = st.genDataXY(NumPoints, sigma, 2, 6)
    db = db1 + db2 + db3

    # you can create manually too
    #data = [[0,1,1], [0,1, 2], [0,1,1.5], [0, 5, 4], [0, 4.5, 4], [0, 4, 4.8]]

    # prepare plot
    plt.axis([0, 8, 0, 8])
    plt.ion()
    plt.show()

    # cluster using K-means, k = 3
    centroids = kmeans(db, 3, plotClusters)
    print(centroids)
    plt.ioff()
    plt.show()
