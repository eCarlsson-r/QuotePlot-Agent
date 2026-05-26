import random

def oneR(data, labels, binNo, positiveLabel = 1, negativeLabel = -1):
  """
  Create one-R classification model that has the minimum error rate
  :param data: list of data points. Each point a list of values.
  :param labels: list of class labels of the data points labels[i] is the class label of the i-th data point in data
  :param binNo: the number of bins to create for each attributes
  :param positiveLabel: int
  :param negativeLabel: int
  :return: classification model [minError, minErrorDim, minAttributeBins, minAttributeBinClasses]
           minError = minimum error rate
           minErrorDim = the attribute no having the minimum error rate
           minAttributeBins = dict, bin ranges of the attribute  minAttributeBins[k] is the k-th bin range of the attribute
           minAttributeBinClasses = dict, class labels of the bin ranges minAttributeBinClasses[k] is the class label of k-th bin range
           see predictOneR() function to see how this model is used to predict data points
  """
  dim = len(data[0])    # the number of attributes

  #-----------------------------------------------
  # create bins for each attribute
  attributebins = createBins(data,binNo)
  #print 'Attributes', attributebins

  #-----------------------------------------------
  # For each attribute, calculate error rate
  #   For each bin, calculate error rate
  attributeclasses = []
  minError = 1
  minErrorDim = 0

  # scan each attribute to calculate the error rate
  for i in range(dim): # i-th attribute
    bins = attributebins[i] # bin ranges of ith dim {binNo:[min, max],...}
    error = 0.00001
    errorNo = 0.00001

    # for each bin of the attribute, determine its class
    classes = {} # {binNo:class, ....} classes of bins
    for k in bins: # k-th bin of the i-th attribute
      binRange = bins[k]  # bin range [min, max]

      pn = 0  # count positive objects
      nn = 0  # count negative objects

      # Find all objects having value within this bin range
      for j in range(len(data)): # j-th data point
        v = data[j][i]  # value of ith attribute of j-th object
        label = labels[j] # object label
        if v >= binRange[0] and v < binRange[1]:
          if label == positiveLabel:
            pn = pn + 1
          else:
            nn = nn + 1

      if (pn + nn) == 0:
        # no data fit in this range due to lack of data, what shall we do?
        # option1: we can assume the class label that minimizes the error rate
        classes[k] = positiveLabel # class label of k-th bin range
        error = 0
        print(0)
      else:
        # what's the majority?
        if pn > nn:
          # positive is majority, assign kth bin as positive class
          classes[k] = positiveLabel    # class label of k-th bin range
          error = error + nn            # all negative cases in this bin range are errors
        else:
          # negative is majority, assign kth bin as negative class
          classes[k] = negativeLabel
          error = error + pn            # all positive cases in this bin range are error

    error = error/len(data)             # error rate is the number of errors / total number of data points

    # update the attribute with the minimum error rate
    if minError > error:
      minError = error
      minErrorDim = i
    attributeclasses.append(classes)  # add class assignments of the current attribute

  return [minError, minErrorDim, attributebins[minErrorDim], attributeclasses[minErrorDim]]

def createBins(data, binNo):
  """
  Create equal size bins for each attribute
  :param data: list of object, each object is a list of [label, v1, v2, ...]
  :return: list of dictionaries. index is bin No, valu is bin range {0:[min,max], 1[min,max],...}
  """
  attributebins = []  # each element is the ranges of bins for each dimension

  # for each attribute
  for i in range(dim):
    # determin min/max values of the current dimension
    min = 10000
    max = -10000
    # for each record
    for j in range(len(data)):
      v = data[j][i]
      if v < min:
        min = v
      if v > max:
        max = v
    binSize = abs(max - min)/binNo  # equal size bin
    bins = {}
    b = min

    # construct equalize size bin ranges
    for j in range(binNo):
      bins[j] = [b, b+binSize]  # range of jth bin, starting from 0
      b = b + binSize

    # add the bin ranges of the current dimension
    attributebins.append(bins)

  #print 'Attributes', attributebins
  return attributebins

# predict a data point using oneRModel
def predictOneR(dataPoint, oneRModel):
    [minError, minErrorDim, bins, classes]  = oneRModel

    v = dataPoint[minErrorDim] # value of
    for k, r in bins.iteritems():
        min = r[0]
        max = r[1]
        if v >= min and v <max:
            return classes[k]
    return 1 # doesn't fit in the range so what shall we do? Option 1. return the majority class or some constant

#-----------------------------------------------------------
# Program starts from here
if __name__ == '__main__':
    import dm.stat as st
    # Randomly generate test data. two classes
    sigma = 0.5
    NumPoints = 20

    # 20 positive
    db1 = st.gen2DData(NumPoints, sigma, 2, 2) # return a list of data points around (2,2). Each list [x0, x1]
    labels1 = [1]*NumPoints

    # 20 negative
    db2 = st.gen2DData(NumPoints, sigma, 6, 6) # return a list of data points around (6,6). Each list [x0, x1]
    labels2 = [-1]*NumPoints

    data = db1 + db2
    classlabels = labels1 + labels2
    dim = 2

    # you can also define your own data. Each first element is cluster assigned. initially 0
    #data = [[0,1,1], [0,1, 2], [0,1,1.5], [0, 5, 4], [0, 4.5, 4], [0, 4, 4.8]]

    # You can also read from file
    #[dim, data, labels] = st.readSVMLight("test.dat")
    #print "Dimension of data: ", dim
    #print "Data read: ", data
    #print "labels of data: ", labels

    binNo = 2
    model = oneR(data, classlabels, binNo, 1, -1)
    [minError, minErrorDim, bins, classes] = model
    print("---------------------------------------")
    print("Classification model created")
    print("minError = ", minError)
    print("minError Attribute No=", minErrorDim)
    print("Bin ranges (brances of the one level decision tree) = ", bins)
    print("Bin classes (the leaf nodes of the decision tree) =", classes)

    # perform prediction using the model
    # ** this is the substitution sampling method.
    #    We should use a better method for performance testing
    predictedClassLabels = []
    for p in data:
        prediction = predictOneR(p, model)
        predictedClassLabels.append(prediction)

    print(predictedClassLabels)
    # print out performance stat
    st.contingencyTable(predictedClassLabels, classlabels)

#--------------------------------------------------------
