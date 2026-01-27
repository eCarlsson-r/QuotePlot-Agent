# Algorithm
#
# DBSCAN(data, k)
#   Arbitrary select a point p with label Unknown
#   If p is a border point (non-core point), label it as NOISE:
#      no points are density-reachable from p and DBSCAN visits the next point of the database.
#   If p is a core point, a cluster is formed by
#      Retrieving all points density-reachable (dr) from p w.r.t. Eps and MinPts:
#   retrieve all ddr points from p, retrieve all ddr points of the ddr points,
#   Labeling all retrieved points with the cluster label.
#   Merge the current cluster to existing cluster if find any dr point that is already a member of a cluster
#   Continue the process until all of the points have been processed.
#
import dm.stat as st
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import time

# Cluster data
# data: a list of objects. Each object is a list. The first attribute is the cluster label
def dbscan(data, Eps, MinPts, plotFunction = None):
    clusters = {}
    clusterId = 1  # the first cluster ID

    for p in data:
        if p[0] <= 0:
            newCluster, mergeList = findAllDRs(clusterId, p, data, Eps, MinPts)

            # If the new cluster has any objects,
            #   add it to the clusters
            #   also merge any clusters connected to the new cluster
            if len(newCluster) > 0:
                if len(mergeList) > 0:
                    # Merge clusters that are connected
                    mergeList = set(mergeList)  # create a set to remove duplicate cid
                    for cid in mergeList:
                        for d in clusters[cid]:
                            d[0] = clusterId
                        newCluster += clusters[cid]
                        del clusters[cid]

                # add the new cluster to the cluster set
                clusters[clusterId] = newCluster
                clusterId += 1

                if plotFunction is not None:
                    plotFunction(clusters)
                    time.sleep(1)

    return clusters

# clusters = list of clusters,
# each cluster is a list of data points.
# a data point is [label, v1, v2, ...]
def plotClusters(clusters):
    c = ['r','g','b','c','m','y','k']
    i = 0
    #plt.axis([0, 11, 0, 11])
    for k, v in clusters.iteritems():
        x = []
        y = []
        for p in v:
            x += [p[1]]
            y += [p[2]]
        plt.plot(x, y, c[i] + 'o')
        i+=1
    plt.draw()  # this will stop and display the current clusters

def findAllDRs(clusterId, p, data, Eps, MinPts):
    """
    Find all Density Reachable points from a core point p
    :param clusterId: int cluster id
    :param p: list a data point: [label, v1, v2, ...]
    :param data: list of data points
    :param Eps: float
    :param MinPts: int
    :return: list DRs, list of cluster IDs that need to be merged to the new cluster of DRs
    """
    if p[0] > 0: # already assigned
        return [],[]

    # find all DDRs from p
    ddrs,mergeList = findAllDDRs(clusterId, p, data, Eps, MinPts)

    # find all DRs from each DDR point from p
    drs = [p]
    for q in ddrs:
        d,m = findAllDRs(clusterId, q, data, Eps, MinPts)
        drs += d
        mergeList += m

    return ddrs, mergeList

def neighbors(p, data, Eps):
    ngh = []  # neighbor points from p
    for i in data:
        if i is p:
            continue

        d = st.disimilarity(p,i)
        if d < Eps :
            ngh.append(i)
    return ngh

def findAllDDRs(clusterId, p, data, Eps, MinPts):
    """
    Find all Directly Density Reachable points from a core point p
    :param clusterId: int cluster ID
    :param p: list a data point [label, v1, v2,....]
    :param data: list of data points
    :param Eps: float Epsilon
    :param MinPts: int Minimum points
    :return: list ddrs, list of cluster IDs to be merged to the new cluster of DDRs
    """
    mergeList = []

    # first check if p is a core point
    ddrs = neighbors(p, data, Eps)  # DDR points from p

    # count the number of neighborhoods
    NptsNo = len(ddrs) + 1 # number of neighborhoods

    # check if p is a core point
    if NptsNo >= MinPts:
        # p is a core point
        cluster = []  # new cluster
        p[0] = clusterId # assign core point p to the new cluster
        # assign all neighborhood points to the new cluster as well
        for j in ddrs:
            if j[0] <= 0:
                # if a neighborhood point is not assigned already, add to the new cluster
                j[0] = clusterId
                cluster.append(j)
            #else:
                # if the neighborhood point is already assigned to a cluster,
                #   all the points in the cluster are DC from this point
                #   so add the cluster ID to mergeList
            #    mergeList.append(j[0])
        return cluster,mergeList
    else:
        return [],[]

if __name__ == '__main__':
    # create 3 clusters
    sigma = 0.5
    NumPoints = 20
    db1 = st.genDataXY(NumPoints, sigma, 2, 2) # return a list of points. Each point is a list: [label, x0, x1,....]
    db2 = st.genDataXY(NumPoints, sigma, 6, 6)
    db3 = st.genDataXY(NumPoints, sigma, 2, 6)
    db = db1 + db2 + db3
    print(db)
    # you can also manually create data points
    #data = [[0,1,1], [0,1, 2], [0,1,1.5], [0, 5, 4], [0, 4.5, 4], [0, 4, 4.8]]

    # prepare plot
    plt.axis([0, 8, 0, 8])
    plt.ion()
    plt.show()

    # cluster the data using DBSCAN
    Eps = 2
    MinPts = 5
    clusters = dbscan(db, Eps, MinPts, plotClusters)
    print(clusters)

    plt.ioff()
    plt.show()
    #Eps = 3
    #MinPts = 5
    # centroids = dbscan(db, Eps, MinPts, gnuplot)
