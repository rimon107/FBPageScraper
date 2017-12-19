import json
import datetime
import csv
import time
import CustomLibrary

from langdetect import detect
from text_cleaner import keep
from text_cleaner.processor.common import ASCII
from text_cleaner.processor.misc import URL
import re

try:
    from urllib.request import urlopen, Request
except ImportError:
    from urllib2 import urlopen, Request

app_id = "455829857840460"
app_secret = "82d68ee28f0df32397920195f41bbae7"  # DO NOT SHARE WITH ANYONE!
page_id = "Shwapno.ACILL"

# input date formatted as YYYY-MM-DD
since_date = ""
until_date = ""

access_token = app_id + "|" + app_secret

obj = CustomLibrary.AnalysisOfSentiment()

def request_until_succeed(url):
    req = Request(url)
    success = False
    while success is False:
        try:
            response = urlopen(req)
            if response.getcode() == 200:
                success = True
        except Exception as e:
            print(e)
            time.sleep(5)

            print("Error for URL {}: {}".format(url, datetime.datetime.now()))
            print("Retrying.")

    return response.read().decode('utf8')


# Needed to write tricky unicode correctly to csv
def unicode_decode(text):
    try:
        return text.encode('utf-8').decode()
    except UnicodeDecodeError:
        return text.encode('utf-8')


def getFacebookPageFeedUrl(base_url):

    # Construct the URL string; see http://stackoverflow.com/a/37239851 for
    # Reactions parameters
    fields = "&fields=message,link,created_time,type,name,id," + \
        "comments.limit(0).summary(true),shares,reactions" + \
        ".limit(0).summary(true)"

    return base_url + fields


def getReactionsForStatuses(base_url):

    reaction_types = ['like', 'love', 'wow', 'haha', 'sad', 'angry']
    reactions_dict = {}   # dict of {status_id: tuple<6>}

    for reaction_type in reaction_types:
        fields = "&fields=reactions.type({}).limit(0).summary(total_count)".format(
            reaction_type.upper())

        url = base_url + fields

        data = json.loads(request_until_succeed(url))['data']

        data_processed = set()  # set() removes rare duplicates in statuses
        for status in data:
            id = status['id']
            count = status['reactions']['summary']['total_count']
            data_processed.add((id, count))

        for id, count in data_processed:
            if id in reactions_dict:
                reactions_dict[id] = reactions_dict[id] + (count,)
            else:
                reactions_dict[id] = (count,)

    return reactions_dict


def processFacebookPageFeedStatus(status):

    # The status is now a Python dictionary, so for top-level items,
    # we can simply call the key.

    # Additionally, some items may not always exist,
    # so must check for existence first

    status_id = status['id']
    status_type = status['type']

    status_message = '' if 'message' not in status else \
        unicode_decode(status['message'])
    link_name = '' if 'name' not in status else \
        unicode_decode(status['name'])
    status_link = '' if 'link' not in status else \
        unicode_decode(status['link'])

    # Time needs special care since a) it's in UTC and
    # b) it's not easy to use in statistical programs.

    status_published = datetime.datetime.strptime(
        status['created_time'], '%Y-%m-%dT%H:%M:%S+0000')
    status_published = status_published + \
        datetime.timedelta(hours=-5)  # EST
    status_published = status_published.strftime(
        '%Y-%m-%d %H:%M:%S')  # best time format for spreadsheet programs

    # Nested items require chaining dictionary keys.

    num_reactions = 0 if 'reactions' not in status else \
        status['reactions']['summary']['total_count']
    num_comments = 0 if 'comments' not in status else \
        status['comments']['summary']['total_count']
    num_shares = 0 if 'shares' not in status else status['shares']['count']

    return (status_id, status_message, link_name, status_type, status_link,
            status_published, num_reactions, num_comments, num_shares)


def scrapeFacebookPageFeedStatus(page_id, access_token, since_date, until_date):
    with open('{}_facebook_statuses.csv'.format(page_id), 'w', encoding="utf-8", newline='') as file:
        w = csv.writer(file)
        w.writerow(["status_id", "status_message", "link_name", "status_type",
                    "status_link", "status_published", "num_reactions",
                    "num_comments", "num_shares", "num_likes", "num_loves",
                    "num_wows", "num_hahas", "num_sads", "num_angrys",
                    "num_special", "ScoreTextBlob", "ScoreVader", "ScoreAzure",
                    "ScoreStanfordCoreNLP", "ScoreGoogleNLP", "ScoreIBMNLP"])

        has_next_page = True
        num_processed = 0
        scrape_starttime = datetime.datetime.now()
        after = ''
        base = "https://graph.facebook.com/v2.9"
        node = "/{}/posts".format(page_id)
        parameters = "/?limit={}&access_token={}".format(100, access_token)
        since = "&since={}".format(since_date) if since_date \
            is not '' else ''
        until = "&until={}".format(until_date) if until_date \
            is not '' else ''

        print("Scraping {} Facebook Page: {}\n".format(page_id, scrape_starttime))

        while has_next_page:
            after = '' if after is '' else "&after={}".format(after)
            base_url = base + node + parameters + after + since + until

            url = getFacebookPageFeedUrl(base_url)
            statuses = json.loads(request_until_succeed(url))
            reactions = getReactionsForStatuses(base_url)



            for status in statuses['data']:

                # Ensure it is a status with the expected metadata
                if 'reactions' in status:
                    status_data = processFacebookPageFeedStatus(status)
                    reactions_data = reactions[status_data[0]]

                    # calculate thankful/pride through algebra
                    num_special = status_data[6] - sum(reactions_data)

                    score = GET_SENTIMENT(status_data[1])

                    w.writerow(status_data + reactions_data + (num_special,) + score)

                num_processed += 1
                if num_processed % 100 == 0:
                    print("{} Statuses Processed: {}".format
                          (num_processed, datetime.datetime.now()))

            # if there is no next page, we're done.
            if 'paging' in statuses:
                after = statuses['paging']['cursors']['after']
            else:
                has_next_page = False

        print("\nDone!\n{} Statuses Processed in {}".format(
              num_processed, datetime.datetime.now() - scrape_starttime))



def GET_SENTIMENT(msg):
    language = "en"
    status_message = CleanText(msg)

    try:
        language = str(detect(status_message))
    except:
        pass
    if status_message and not status_message.isspace() and language != "en":
        url = 'https://translate.yandex.net/api/v1.5/tr.json/translate?key=' + YANDEX_API_KEY + '&text=' + quote(
            status_message) + '&lang=en'
        r = requests.get(url)
        response = r.json()
        translated = response['text'][0]
    else:
        translated = status_message

    socre_textblob, sentiment_textblob = GET_TEXTBLOB_SENTIMENT(translated)
    socre_vader, sentiment_vader, complete_vader_score = GET_VADER_SENTIMENT(translated)
    socre_azure, sentiment_azure = GET_AZURE_SENTIMENT(translated)
    socre_stanford = GET_STANFORDCORENLP_SENTIMENT(translated)
    socre_google, sentiment_google, magnitude_google = GET_GOOGLENLP_SENTIMENT(translated)
    score_ibm, sentiment_ibm = GET_IBMWATSON_SENTIMENT(translated)

    rTextBlob = '{0:.2f}'.format(socre_textblob)
    rVader = '{0:.2f}'.format(complete_vader_score['compound'])
    rAzure = '{0:.2f}'.format(socre_azure)
    rStanfordCoreNLP = '{0:.2f}'.format(socre_stanford)
    rGoogleNLP = '{0:.2f}'.format(socre_google)
    rIBMNLP = '{0:.2f}'.format(score_ibm)

    return (rTextBlob, rVader, rAzure, rStanfordCoreNLP, rGoogleNLP, rIBMNLP)



def GET_TEXTBLOB_SENTIMENT(text):
    try:
        score = obj.GetTextBlobSentimentAnalyzer(text)
        polarity = float("{0:.2f}".format(score.polarity))
        if polarity >= 0.3:
            return polarity, 'positive'
        elif polarity <= -0.3:
            return polarity, 'negative'
        else:
            return polarity, 'neutral'
    except:
        return -1000, 'neutral'

def GET_VADER_SENTIMENT(text):
    try:
        score = obj.GetVaderSentimentIntensity(text)

        polarity = float("{0:.2f}".format(score['compound']))
        if polarity >= 0.3:
            return polarity, 'positive', score
        elif polarity <= -0.3:
            return polarity, 'negative', score
        else:
            return polarity, 'neutral', score
    except:

        score = {}
        score["pos"] = -1000
        score["neg"] = -1000
        score["neu"] = -1000
        score["compound"] = -1000
        return -1000, 'neutral', score


def GET_STANFORDCORENLP_SENTIMENT(text):  # Stanford Sentiment Analysis.
    try:
        resultStanfordCoreNLP = obj.GetStanfordCoreNLPSentimentAnalyzer(text)
        return float(resultStanfordCoreNLP)
    except:
        return -1000.00


def GET_GOOGLENLP_SENTIMENT(text):  # Google Cloud NLP Sentiment Analysis.
    try:

        sentiment_score, sentiment_magnitude = obj.GetGoogleSentimentAnalyzer(text)

        score = float("{0:.2f}".format(sentiment_score))
        magnitude = float("{0:.2f}".format(sentiment_magnitude))

        if score >= 0.6:
            return score, 'positive', magnitude
        elif score < 0.4:
            return score, 'negative', magnitude
        else:
            return score, 'neutral', magnitude
    except:

        return -1000, 'neutral', -1000

def GET_AZURE_SENTIMENT(text):
    try:
        score = float(obj.GetAzureSentimentAnalyzer(text))
        if score >= 0.6:
            return score, 'positive'
        elif score < 0.4:
            return score, 'negative'
        else:
            return score, 'neutral'
    except:
        return -1000, 'neutral'

def GET_IBMWATSON_SENTIMENT(text):
    try:
        score, label = obj.GetIBMWatsonSentimentAnalyzer(text)
        return score, label
    except:
        return -1000, 'neutral'

def CleanText(text):
    result = keep(
        text,
        [ASCII],
    )
    result = URL.remove(result)

    expression = '(\#[a-zA-Z0-9]+)|(\@[A-Za-z0-9]+)|\$(\w+)|([#@$"|])|([0-9]+)'

    result = ' '.join(re.sub(expression, " ", result).split())
    return result




if __name__ == '__main__':
    scrapeFacebookPageFeedStatus(page_id, access_token, since_date, until_date)