import sys
import math
import random
import time
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import dm.stat as st

# Cluster data into k clusters
# data: a list of objects. Each object is a list. The first attribute is the cluster label
def som(db, nn, radius, alpha, plotType=1, randomNN=False):

    if randomNN:
        # generate random weights for clustering
        wn = len(db[0]) - 1               # number of weight vectors
        l2d = create2DNNLayer(nn,wn,10)
    else:
        # generate 2D grid weights for grid fitting
        l2d = create2DNNLayerGrid(nn,10)

    # plot the initial neurons
    somPlot(plotType, db, l2d)

    n = 1
    while(n < 10):
        for i in range(10): # number of epochs
            for p in db: # sweep, present each data point
                r,c = forward(l2d,p)
                updateWeights(p, l2d, r, c, radius, alpha)
        n+=1

        # plot updated neurons
        somPlot(plotType, db, l2d)

    return []

fig1 = None
ax1 = None
def somPlot(plotType, db, l2d):
    if plotType == 1:
        some_colorMap(db, l2d)


def some_colorMap(db, l2d):
    global fig1, ax1
    # l2d = n by n neurons
    #   Each neuron: [cluster_index, x1, x2,...xM]
    # Use the first 3 components x1,x2,x3 as RGB color
    # Use the row, column as coordinates of the neurons

    # plot weights of the neurons
    maxR = 10
    maxC = 10
    if len(l2d) == 0:
        return

    rn = 0
    i = 1
    for r in l2d:
        cn = 0
        for c in r:
            if c[1] > maxR:
                maxR = c[1]
            if c[2] > maxC:
                maxC = c[2]

            r = hex(int(c[1]*256/maxR))[2:]
            g = hex(int(c[2]*256/maxC))[2:]
            if len(r) < 2:
                r = "0" + r
            if len(g) < 2:
                g = "0" + g

            rgb = r + g + "00"

            ax1.add_patch(
                patches.Rectangle(
                    (cn, rn),   # (x,y)
                    1,          # width
                    1,          # height
                    color="#"+rgb
                )
            )

            cn += 1
            i+= 1
        rn += 1

    # plot data points
    for p in db:
        cmd = ("%s %s\n" % (p[1],p[2])).encode()
        ax1.add_patch(
            patches.Rectangle(
                (p[1], p[2]),   # (x,y)
                0.1,          # width
                0.1,          # height
                color="black"
            )
        )

    plt.draw()
    time.sleep(1)

def updateWeights(p, l2d, r, c, radius, alpha):
    """
    update neurons around r, c
    :param p: list, a data point
    :param l2d: list, nn x nn neurons
    :param r: int, row
    :param c: int, column
    :param radius: float.
    :param alpha: float
    :return:
    """
    minR = r - radius
    minC = c - radius
    maxR = r + radius
    maxC = c + radius
    maxV = len(l2d[0]) #-1
    if( minR < 0 ):
        minR = 0
    if( minC < 0 ):
        minC = 0
    if( maxR > maxV ):
        maxR = maxV
    if( maxC > maxV ):
        maxC = maxV

    for i in range(maxR - minR):
        tr = i + minR
        for j in range(maxC - minC):
            tc = j + minC
            ds = math.sqrt((tr - r)*(tr - r) + (tc-c)*(tc-c))
            if( ds < radius ):
                updateWeight(p, l2d, tr, tc, alpha, 1.001 - ds/radius)

    return []

def updateWeight(p, l2d, r, c, alpha, factor):
    """
    update a neuron at r, c
    :param p: list. the data point
    :param l2d: list. array of neurons
    :param r: int. row
    :param c: int. column
    :param alpha: float.
    :param factor: float.
    """
    nr = l2d[r][c]
    for i in range(len(nr)):
        if( i > 0):
            dw = p[i] - nr[i]
            #print p[i], nr[i], dw * alpha * factor
            #ch = msvcrt.getch()
            nr[i] += dw * alpha * factor

def forward(layer2d, p):
    """
    present the input vectors p (a list, first element is a class label), and
    compute the degree of mismatch for each unit
    return the winning neuron location: winnerR, winnerC in layer2d
    :param layer2d: nn x nn neurons
    :param p: a data point [label, v1,...]
    :return: winner Row, winner Column
    """
    minDistance = -1
    winnerNeuron = False
    winnerR = -1
    winnerC = -1
    for r in range(len(layer2d)): # row
        v = layer2d[r]
        for c in range(len(v)): # column
            n = v[c]  # a neuron at row r, column c
            ds = calcDistance(p, n)  # calculate the distance between p and n: sum[(wij-xj)^2] over j (attributes)
            n[0] = ds
            if( minDistance < 0 or ds < minDistance):
                minDistance = ds
                winnerNeuron = n
                winnerR = r
                winnerC = c
    return winnerR, winnerC

def calcDistance(p,n):
    """
    calculate distance between p and n
    :param p: a vector [label, v1, ....]
    :param n: a vector [label, v1,....]
    :return: float  ||p - n||
    """
    d = 0
    for i in range(len(p)):
        if i > 0:
            d += math.pow(p[i] - n[i],2)
    return math.sqrt(d/(len(p)-1))

def create2DNNLayer(nn, wn, wRange):
    """
    Create 2D NN array
    :param nn: number of neurons
    :param wn: number of weights
    :param wRange: weigh value range
    :return: nn x nn array of neurons, each neuron is a list of wn weights
    """
    l2 = []       # nn x nn array of neuron
    for i in range(nn):
        rn = []    # a row of neurons
        for j in range(nn):
            n = [0]    # a neuron
            for k in range(wn):
                w = random.random()*wRange
                n.append(w)
            rn.append(n)
        l2.append(rn)
    return l2

def create2DNNLayerGrid(nn, wRange):
    l2 = []       # nn x nn array of neuron
    for i in range(nn):
        rn = []    # a row of neurons
        for j in range(nn):
            n = [0, j, i]    # a neuron
            rn.append(n)
        l2.append(rn)
    return l2

if __name__ == '__main__':
    #print hex(10)[2:] + hex(10)[2:0] + "00"

    mode = 0

    if len(sys.argv) > 1:
        mode = int(sys.argv[1])

    #---------------------------------------------------
    # genearte data points
    sigma = 0.5
    NumPoints = 20
    db1 = st.genDataXY(NumPoints, sigma, 1, 1) # return a list of lists. Each list [label, x0, x1,....]
    db2 = st.genDataXY(NumPoints, sigma, 6, 6)
    db3 = st.genDataXY(NumPoints, sigma, 1, 6)
    #db = db1 + db2
    db = db1 + db2 + db3
    #data = [[0,1,1], [0,1, 2], [0,1,1.5], [0, 5, 4], [0, 4.5, 4], [0, 4, 4.8]]

    #som2d(db, 10, 4, 0.03, gnuplot)
    #som2dGrid(db, 10, 4, 0.03, gnuplot)

    nn = 8
    radius = 4
    alpha = 0.03
    # prepare plot
    fig1 = plt.figure()
    ax1 = fig1.add_subplot(111, aspect='equal')
    plt.axis([0, nn, 0, nn])
    plt.ion()
    plt.show()

    if mode == 0:
        # Create 2D grid Neurons and plot color map grid
        som(db, nn, radius, alpha, 1, False)
    elif mode == 1:
        # Create random 2D Neurons and plot heat map
        som(db, nn, radius, alpha, 2, 1)
    else:
        # fit grid
        som(db, nn, 4, 0.03, 3, False)

    plt.ioff()
    plt.show()

    #l2d = [ [[0,0,0], [0,1,0], [0,2,0], [0,3,0]],
    #        [[0,0,1], [0,1,1], [0,2,1], [0,3,1]],
    #        [[0,0,2], [0,1,2], [0,2,2], [0,3,2]],
    #        [[0,0,3], [0,1,3], [0,2,3], [0,3,3]] ]
    #isclust.visualizeSOM(gnuplot, l2d, "X", "Y", 0, 5, 0, 5, "SOM")
