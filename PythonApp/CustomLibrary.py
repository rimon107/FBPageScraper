from SentimentAnalysis import *


class AnalysisOfSentiment:

    def __init__(self):
        self.obj = SentimentAnalysis()

    # def GetSentiment(self, text):
    #     train = self.obj.GetTrainDataSet()
    #     dict = self.obj.GetDictionaryOfTrainData(train)
    #     t = self.obj.GetSampleDataForTraining(train, dict)
    #     classifier = self.obj.TrainNaiveBayesClassifier(t)
    #     features = self.obj.GetDataFeatures(text, dict)
    #     result = self.obj.GetClassifiedResult(classifier, features)
    #     return result


    def GetVaderSentimentIntensity(self, text):
        result = self.obj.VaderSentimentIntensityAnalyzer(text)
        return result

    def GetTextBlobSentimentAnalyzer(self, text):
        result = self.obj.TextBlobSentimentAnalyzer(text)
        return result

    def GetAzureSentimentAnalyzer(self, text):
        result = self.obj.AzureSentimentAnalyzer(text)
        return result

    def GetStanfordCoreNLPSentimentAnalyzer(self, text):
        result = self.obj.StanfordCoreNLPSentimentAnalyzer(text)
        return result

    def GetGoogleSentimentAnalyzer(self, text):
        result_score, result_magnitude = self.obj.GoogleSentimentAnalyzer(text)
        return result_score, result_magnitude

    def GetIBMWatsonSentimentAnalyzer(self, text):
        result_score, result_label = self.obj.IBMWatsonSentimentAnalyzer(text)
        return result_score, result_label
    # def GetNaiveBayesClassifierResult(self, text):
    #     # sentList = SentenseTokenizer.sent_tokenize(text)
    #     instance = 10000
    #     trainSet = self.obj.GetTrainDataSetForNLTK(instance)
    #     result = self.obj.GetNaiveBayesClassifierResult(trainSet,text)
    #     return result



