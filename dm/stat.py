import random
import math

#--------------------------------------------------
# Generate data points
# Each point = [0, x_1, ..., x_NumPoints]
def genData(dimension, NumPoints, vmin, vmax, uniform=False):
  db = []
  for i in range(NumPoints):
    d = [0]
    for j in range(dimension):
      if( uniform ):
        e = random.random()*(vmax - vmin) + vmin
      else:
        e = random.gauss((vmax - vmin)/2, vmax - vmin)
      d.append(e)
    db.append(d)
  return db

# generate 2D data points centered around cx and cy within the diameter
def genDataXY(NumPoints, sigma, cx, cy, uniform=False):
  db = []
  for i in range(NumPoints):
    if( uniform ):
      x = (random.random() - 0.5) * sigma + cx
      y = (random.random() - 0.5) * sigma + cy
    else:
      x = random.gauss(cx, sigma)
      y = random.gauss(cy, sigma)
    db.append([0,x,y])
  return db

# Generate test data: 2D data points centred around cx and cy within the diameter
def gen2DData(NumPoints, sigma, cx, cy, uniform=False):
  db = []
  for i in range(NumPoints):
    if( uniform ):
      x = (random.random() - 0.5) * sigma + cx
      y = (random.random() - 0.5) * sigma + cy
    else:
      x = random.gauss(cx, sigma)
      y = random.gauss(cy, sigma)
    db.append([x,y])
  return db

# Measure disimilarity between x1 and x2
def disimilarity(x1,x2):
  # Euclidean distance
  d = 0
  for i in range(len(x1)-1):
    # print x1
    d += math.pow(x1[i+1] - x2[i+1],2)
  return math.sqrt(d)

def zeros(k):
  d = [0]*k
  return d

# Read svm sparse format from file 'fname' (with labels only)
# output: [dimension, data[[clusterAssigned, attribte1,...], labels[]]
def readSVMLight(fname):
  """
  Read SVM Light format file
  :param fname: str, pull path to the file including name
  :return: int dim, list of data points (each point is a list [label, v1, ...], list of lables of data points
  """
  dimension = 0
  data = []
  labels = []
  for line in open(fname).readlines():
    label, lineattr = line.split(' ', 1)
    attr = {0:float(label)}  # 0 is class label
    for e in lineattr.split():
      index,value= e.split(":")
      d = int(index)
      attr[d] = float(value)
      if d > dimension:
        dimension = d
    data.append(attr)           # attributes of each data point
    labels.append(float(label)) # label of each data point

  data2 = []
  for i in range(len(data)):
    d = [0] * (dimension + 1)
    dic = data[i]  # attributes of ith data point (first one is the label)
    for k in dic.keys():
      d[k] = dic[k]
    data2.append(d)

  return [dimension, data2, labels]

def readCSVFileToNumpyArray(fname, delimiter=',', skipHeader=False):
    from numpy import genfromtxt
    if skipHeader:
        skipHeader = 1
    else:
        skipHeader = 0

    my_data = genfromtxt(fname, delimiter=delimiter, skipHeader=skipHeader)
    return my_data

# build contingency table assuming cluster0 is clusterZeroLabel
def contingencyTable(predicted, classlabels):
    """
    Build contingency table (confusion matrix)
    :param data: list of data points. Each point is a list [v1, ....]
    :param predicted: list of predicted class labels of each data point
    :param classlabels: list of class labels of each data point  labels[i] is the class label of the ith data pint in data
    """
    TP = 0
    TN = 0
    FP = 0
    FN = 0

    for i in range(len(predicted)):
        predictedLabel = predicted[i]
        classdLabel = classlabels[i]
        # what's the acutual class label?
        if classdLabel > 0:  # positive
            # what's the predicted class label?
            if predictedLabel == classdLabel:
                TP = TP + 1  # positive is classified as postive
            else:
                FN = FN + 1  # positive is falsely classified as negative
        else:  # negative
            if predictedLabel == classdLabel:
                TN = TN + 1  # negative is classified as negative
            else:
                FP = FP + 1  # negative is falsley classified as positive

    N = TP + TN + FP + FN

    print("   +  -   predicted")
    print(" +", TP, FN)
    print(" -", FP, TN)

    print("Acc = ", (TP+TN)/float(N))
    print("Error = ", (FN+FP)/float(N))
    print("Precision = ", float(TP)/(TP+FP+0.00001))
    print("Recall = Sensitivity = TP rate = ", float(TP)/(TP+FN+0.00001))
    print("Specificity = 1- FP Rate = ", float(TN)/(TN+FP+0.00001))
