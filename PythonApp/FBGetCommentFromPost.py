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
file_id = "Shwapno.ACILL"

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


def getFacebookCommentFeedUrl(base_url):

    # Construct the URL string
    fields = "&fields=id,message,reactions.limit(0).summary(true)" + \
        ",created_time,comments,from,attachment"
    url = base_url + fields

    return url


def getReactionsForComments(base_url):

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


def processFacebookComment(comment, status_id, parent_id=''):

    # The status is now a Python dictionary, so for top-level items,
    # we can simply call the key.

    # Additionally, some items may not always exist,
    # so must check for existence first

    comment_id = comment['id']
    comment_message = '' if 'message' not in comment or comment['message'] \
        is '' else unicode_decode(comment['message'])
    comment_author = unicode_decode(comment['from']['name'])
    num_reactions = 0 if 'reactions' not in comment else \
        comment['reactions']['summary']['total_count']

    if 'attachment' in comment:
        attachment_type = comment['attachment']['type']
        attachment_type = 'gif' if attachment_type == 'animated_image_share' \
            else attachment_type
        attach_tag = "[[{}]]".format(attachment_type.upper())
        comment_message = attach_tag if comment_message is '' else \
            comment_message + " " + attach_tag

    # Time needs special care since a) it's in UTC and
    # b) it's not easy to use in statistical programs.

    comment_published = datetime.datetime.strptime(
        comment['created_time'], '%Y-%m-%dT%H:%M:%S+0000')
    comment_published = comment_published + datetime.timedelta(hours=-5)  # EST
    comment_published = comment_published.strftime(
        '%Y-%m-%d %H:%M:%S')  # best time format for spreadsheet programs

    # Return a tuple of all processed data

    return (comment_id, status_id, parent_id, comment_message, comment_author,
            comment_published, num_reactions)


def scrapeFacebookPageFeedComments(page_id, access_token):
    with open('{}_facebook_comments.csv'.format(file_id), 'w', encoding="utf-8", newline='') as file:
        w = csv.writer(file)
        w.writerow(["comment_id", "status_id", "parent_id", "comment_message",
                    "comment_author", "comment_published", "num_reactions",
                    "num_likes", "num_loves", "num_wows", "num_hahas",
                    "num_sads", "num_angrys", "num_special", "ScoreTextBlob", "ScoreVader", "ScoreAzure",
                    "ScoreStanfordCoreNLP", "ScoreGoogleNLP", "ScoreIBMNLP"])

        num_processed = 0
        scrape_starttime = datetime.datetime.now()
        after = ''
        base = "https://graph.facebook.com/v2.9"
        parameters = "/?limit={}&access_token={}".format(
            100, access_token)

        print("Scraping {} Comments From Posts: {}\n".format(
            file_id, scrape_starttime))

        with open('{}_facebook_statuses.csv'.format(file_id), 'r', encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)

            # Uncomment below line to scrape comments for a specific status_id
            # reader = [dict(status_id='5550296508_10154352768246509')]

            for status in reader:
                has_next_page = True

                while has_next_page:

                    node = "/{}/comments".format(status['status_id'])
                    after = '' if after is '' else "&after={}".format(after)
                    base_url = base + node + parameters + after

                    url = getFacebookCommentFeedUrl(base_url)
                    # print(url)
                    comments = json.loads(request_until_succeed(url))
                    reactions = getReactionsForComments(base_url)

                    for comment in comments['data']:
                        comment_data = processFacebookComment(
                            comment, status['status_id'])
                        reactions_data = reactions[comment_data[0]]

                        # calculate thankful/pride through algebra
                        num_special = comment_data[6] - sum(reactions_data)

                        score = GET_SENTIMENT(comment_data[3])

                        w.writerow(comment_data + reactions_data +
                                   (num_special, ) + score)

                        if 'comments' in comment:
                            has_next_subpage = True
                            sub_after = ''

                            while has_next_subpage:
                                sub_node = "/{}/comments".format(comment['id'])
                                sub_after = '' if sub_after is '' else "&after={}".format(
                                    sub_after)
                                sub_base_url = base + sub_node + parameters + sub_after

                                sub_url = getFacebookCommentFeedUrl(
                                    sub_base_url)
                                sub_comments = json.loads(
                                    request_until_succeed(sub_url))
                                sub_reactions = getReactionsForComments(
                                    sub_base_url)

                                for sub_comment in sub_comments['data']:
                                    sub_comment_data = processFacebookComment(
                                        sub_comment, status['status_id'], comment['id'])
                                    sub_reactions_data = sub_reactions[
                                        sub_comment_data[0]]

                                    num_sub_special = sub_comment_data[
                                        6] - sum(sub_reactions_data)

                                    score = GET_SENTIMENT(sub_comment_data[3])

                                    w.writerow(sub_comment_data +
                                               sub_reactions_data + (num_sub_special,) + score)

                                    num_processed += 1
                                    if num_processed % 100 == 0:
                                        print("{} Comments Processed: {}".format(
                                            num_processed,
                                            datetime.datetime.now()))

                                if 'paging' in sub_comments:
                                    if 'next' in sub_comments['paging']:
                                        sub_after = sub_comments[
                                            'paging']['cursors']['after']
                                    else:
                                        has_next_subpage = False
                                else:
                                    has_next_subpage = False

                        # output progress occasionally to make sure code is not
                        # stalling
                        num_processed += 1
                        if num_processed % 100 == 0:
                            print("{} Comments Processed: {}".format(
                                num_processed, datetime.datetime.now()))

                    if 'paging' in comments:
                        if 'next' in comments['paging']:
                            after = comments['paging']['cursors']['after']
                        else:
                            has_next_page = False
                    else:
                        has_next_page = False

        print("\nDone!\n{} Comments Processed in {}".format(
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
    scrapeFacebookPageFeedComments(file_id, access_token)


# The CSV can be opened in all major statistical programs. Have fun! :)