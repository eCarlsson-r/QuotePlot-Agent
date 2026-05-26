import random
import math

def epoch(perceptron, dataset, labels, alpha=0.01):
    error = 0
    for i in range(len(dataset)):
        x = dataset[i]
        label = labels[i]
        error += sweep(perceptron, x, label, alpha)
    return error  # Sum of squared errors

def sweep(perceptron, x, label, alpha=0.01):
    # present one data and update weights

    y = forward(perceptron, x)
    #print y, label

    # update weights
    x += [1]  # add bias
    [weights, afunction] = perceptron
    for i in range(len(weights)):
        wt = weights[i]
        # for pure linear function
        weights[i] = wt + alpha * (label - y) * x[i]

        # for sigmoid function: alpha*(dj-oj)oj(1-oj)xi
        #weights[i] = wt + alpha * (label - y)*y*(1-y) * x[i]

    error = math.pow(label - y,2)
    return error # squared error

def forward(perceptron, x):
    [weights, afunction] = perceptron
    x += [1] # add bias
    sum = 0
    for i in range(len(weights)):
        sum += x[i]*weights[i]
    output = afunction(sum)
    return output

def createPerceptron(inputNo, afunction):
    weights = [random.random()*2-1]*(inputNo+1) # the last weight is the bias weight

    return [weights, afunction]

def sigmoid(input):
    return 1 / (1 + math.exp(-input))

def step(input):
    if input > 0:
        return 1
    else:
        return -1

if __name__ == '__main__':
    #---------------------------------------
    # generate test data
    import dm.stat as st
    # Randomly generate test data. two classes
    sigma = 0.5
    NumPoints = 20

    # 20 positive
    db1 = st.gen2DData(NumPoints, sigma, 2, 2) # return a list of data points around (2,2). Each list [x0, x1]
    labels1 = [1]*NumPoints

    # 20 negative
    db2 = st.gen2DData(NumPoints, sigma, 6, 6) # return a list of data points around (6,6). Each list [x0, x1]
    labels2 = [-1]*NumPoints  # 0 or -1

    dataset = db1 + db2
    classlabels = labels1 + labels2
    dim = 2

    #---------------------------------------
    perceptron = createPerceptron(2, step)  # create a perceptron with 2 inputs
    print('Perceptron', perceptron)

    # train the perceptron
    for i in range(50): # max 50 iterations
        error = epoch(perceptron, dataset, classlabels, 0.01)
        RMS = math.sqrt(error)
        print('RMS and weights', RMS, perceptron)
        if RMS < 0.001:
            break

    # predict using the trained perceptron
    predictedClasses = []
    for data in dataset:
        predicted = forward(perceptron, data)
        #print predicted
        if predicted > 0:
            predicted = 1
        else:
            predicted = -1
        predictedClasses.append(predicted)

    # print out performance stat
    st.contingencyTable(predictedClasses, classlabels)

