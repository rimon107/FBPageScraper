import nltk
import nltk.data
from nltk.tokenize import word_tokenize
from nltk import NaiveBayesClassifier
from textblob import TextBlob
from nltk.classify import NaiveBayesClassifier
from nltk.sentiment import vader

import math
from nltk.corpus import subjectivity
from nltk.sentiment import SentimentAnalyzer
from nltk.sentiment.util import *

from pycorenlp import StanfordCoreNLP

import urllib.request
import json
from google.cloud import language
from google.cloud.language import enums
from google.cloud.language import types
import six

from watson_developer_cloud import NaturalLanguageUnderstandingV1
import watson_developer_cloud.natural_language_understanding.features.v1 as Features
WATSON_USERNAME = "20d75993-d1b9-4b30-8404-37c0a311937f"
WATSON_PASSWORD = "1Ko6VlgN8t7D"
WATSON_VERSION = "2017-02-27"
WATSON_APIURL = 'https://gateway.watsonplatform.net/natural-language-understanding/api'

class SentimentAnalysis:
    def GetTrainDataSet(self):
        trainSet = [("Great place to be when you are in Bangalore.", "pos"),
                 ("The place was being renovated when I visited so the seating was limited.", "neg"),
                 ("Loved the ambience, loved the food", "pos"),
                 ("The food is delicious but not over the top.", "neg"),
                 ("Service - Little slow, probably because too many people.", "neg"),
                 ("The place is not easy to locate", "neg"),
                 ("Mushroom fried rice was spicy", "pos"),
                 ("this is not bad", "pos"),
                 ("this is not good", "neg"),
                 ("this is good", "pos"),
                 ("this is bad", "neg"),
                 ]
        return trainSet

    def GetDictionaryOfTrainData(self, trainSet):
        # tokenizer = nltk.data.load('tokenizers/punkt/PY3/english.pickle')
        # result = tokenizer.tokenize(text)
        trainDictionary = set(word.lower() for passage in trainSet for word in word_tokenize(passage[0]))
        return trainDictionary

    def GetSampleDataForTraining(self, trainSet, dictionary):
        sample = [({word: (word in word_tokenize(x[0])) for word in dictionary}, x[1]) for x in trainSet]
        return sample

    def TrainNaiveBayesClassifier(self, sampleData):
        classifier = NaiveBayesClassifier.train(sampleData)
        return classifier

    def GetDataFeatures(self, data, dictionary):
        data_features = {word.lower(): (word in word_tokenize(data.lower())) for word in dictionary}
        return data_features

    def GetClassifiedResult(self, classifier, data_features):
        return classifier.classify(data_features)

    def VaderSentimentIntensityAnalyzer(self, text):		#Vader Sentiment Analysis.
        sid = vader.SentimentIntensityAnalyzer()
        ss = sid.polarity_scores(text)
        result = ss
        return result

    def TextBlobSentimentAnalyzer(self, text):		#Textblob Sentiment Analysis.
        analysis = TextBlob(text)
        # set sentiment
        return analysis.sentiment

    def AzureSentimentAnalyzer(self, text):		#Azure Sentiment Analysis.
        try:
            # Configure API access
            apiKey = '51e0f1de3d2849b9830c65379f59f5ea'
            sentimentUri = 'https://southeastasia.api.cognitive.microsoft.com/text/analytics/v2.0/sentiment'
            keyPhrasesUri = 'https://southeastasia.api.cognitive.microsoft.com/text/analytics/v2.0/keyPhrases'
            languageUri = 'https://southeastasia.api.cognitive.microsoft.com/text/analytics/v2.0/languages'
            # Prepare headers
            headers = {}
            headers['Ocp-Apim-Subscription-Key'] = apiKey
            headers['Content-Type'] = 'application/json'
            headers['Accept'] = 'application/json'

            # Detect language
            postData1 = json.dumps({"documents": [{"id": "1", "text": text}]}).encode('utf-8')
            request1 = urllib.request.Request(languageUri, postData1, headers)
            response1 = urllib.request.urlopen(request1)
            response1json = json.loads(response1.read().decode('utf-8'))
            language = response1json['documents'][0]['detectedLanguages'][0]['iso6391Name']  # Sample json: {"documents":[{"id":"1","detectedLanguages":[{"name":"English","iso6391Name":"en","score":1.0}]}],"errors":[]}

            # Determine sentiment
            postData2 = json.dumps({"documents": [{"id": "1", "language": language, "text": text}]}).encode('utf-8')
            request2 = urllib.request.Request(sentimentUri, postData2, headers)
            response2 = urllib.request.urlopen(request2)
            response2json = json.loads(response2.read().decode('utf-8'))
            sentiment = response2json['documents'][0]['score']  # Sample json: {"documents":[{"score":0.9858533790105,"id":"1"}],"errors":[]}

            # Determine key phrases
            # postData3 = postData2
            # request3 = urllib.request.Request(keyPhrasesUri, postData3, headers)
            # response3 = urllib.request.urlopen(request3)
            # response3json = json.loads(response3.read().decode('utf-8'))
            # keyPhrases = response3json['documents'][0][
            #     'keyPhrases']  # Sample json: {"documents":[{"keyPhrases":["best cloud platform","Azure"],"id":"1"}],"errors":[]}

            # Display results
            # print(sentiment)
            # print('Text: %s' % sampleText)
            # # print('Language: %s' % language)
            # print('Sentiment: %f' % sentiment)
            # print('Key phrases: %s' % keyPhrases)

            return sentiment
        except:
            return -1000

    def StanfordCoreNLPSentimentAnalyzer(self, text):  # Azure Sentiment Analysis.
        try:
            nlp = StanfordCoreNLP('http://localhost:7800')
            res = nlp.annotate(text,
                               properties={
                                   'annotators': 'sentiment',
                                   'outputFormat': 'json',
                                   'timeout': 10000,
                               })
            result = res["sentences"][0]["sentimentValue"]
            score = 0
            count = 0
            for s in res["sentences"]:
                score += float(s["sentimentValue"])
                count += 1

            score = math.ceil(score / count)
            return score
        except:
            return -1000

    def GoogleSentimentAnalyzer(self, text):  # Azure Sentiment Analysis.
        try:

            client = language.LanguageServiceClient()

            if isinstance(text, six.binary_type):
                text = text.decode('utf-8')

                # Instantiates a plain text document.
            document = types.Document(
                content=text,
                type=enums.Document.Type.PLAIN_TEXT)

            # Detects sentiment in the document. You can also analyze HTML with:
            #   document.type == enums.Document.Type.HTML
            sentiment = client.analyze_sentiment(document)
            print(sentiment)
            print(sentiment.document_sentiment.score)
            print(sentiment.document_sentiment.magnitude)

            return sentiment.document_sentiment.score, sentiment.document_sentiment.magnitude
        except:
            return -1000, -1000


    def IBMWatsonSentimentAnalyzer(self, text):  # IBM Watson Sentiment Analysis. Returns score and label (float, str pair)
        try:
            natural_language_understanding = NaturalLanguageUnderstandingV1(
                username=WATSON_USERNAME,
                password=WATSON_PASSWORD,
                version=WATSON_VERSION,
                url = WATSON_APIURL)
            response = natural_language_understanding.analyze( text=text, features=[Features.Sentiment()] )
            return float(response["sentiment"]["document"]["score"]), str(response["sentiment"]["document"]["label"])
        except:
            return -1000, "neutral"


    def GetTrainDataSetForNLTK(self, instances=100):
        subj_docs = [(sent, 'subj') for sent in subjectivity.sents(categories='subj')[:instances]]
        obj_docs = [(sent, 'obj') for sent in subjectivity.sents(categories='obj')[:instances]]
        train_subj_docs = subj_docs
        train_obj_docs = obj_docs
        trainSet = train_subj_docs + train_obj_docs
        return trainSet

    def GetSampleTrainDataForNLTK(self, trainSet):
        sentim_analyzer = SentimentAnalyzer()
        all_words_neg = sentim_analyzer.all_words([mark_negation(doc) for doc in trainSet])
        unigram_feats = sentim_analyzer.unigram_word_feats(all_words_neg, min_freq=4)
        sentim_analyzer.add_feat_extractor(extract_unigram_feats, unigrams=unigram_feats)
        sampleTrainData = sentim_analyzer.apply_features(trainSet)
        return sampleTrainData

    




