from lucy import text

# read data_questions
r = text.readLabelledTextLines("data/data_questions.txt")
stringlist = r[0]
y = r[1]
#print r[0]
#print y

# generate vocabulary
r = text.genvocabFromStringList(stringlist, dfthreshould=2)
vocab = r[0]
vocabf = r[1]
vocabidf = r[2]
#print vocab
text.saveVocab("data_questions_vocab.txt", vocab, vocabf, vocabidf)

# generate features
features = text.genfeaturesFromList(stringlist, vocab, vocabidf)  # list of dictionaries
text.saveFeatures("data_questions_feature.csv", vocab, features, y)
