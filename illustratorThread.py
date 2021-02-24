import re
import time
import webbrowser

import tweepy
import json

from tweepy import Status


def write_status_to_file(last_post):
    reduced_status = {
        'twit_id': last_post.id_str,
        'twit_url': 'https://twitter.com/{screen_name}/status/{twit_id}'.format(
            screen_name=last_post.author.screen_name,
            twit_id=last_post.id_str),
        'created_at': str(last_post.created_at),
        'full_text': last_post.full_text,
        'in_reply_to_status_id': last_post.in_reply_to_status_id_str,
        'url_list': [],
        'img_list': []
    }
    if last_post.entities:
        for url in last_post.entities['urls']:
            reduced_status['url_list'] += url['expanded_url']
    try:
        if last_post.extended_entities:
            for media in last_post.extended_entities['media']:
                reduced_status['img_list'] += media['media_url']
    except AttributeError as err:
        with open("error_file.txt", "a") as file:
            file.write('ERROR: ' + last_post.id_str + '\t' + str(err) + '\n')
        print('ERROR: ' + last_post.id_str + '\t' + str(err) + '\n')
    try:
        with open(last_post.id_str + '.txt', "a") as text_file:
            json.dump(reduced_status, text_file)
    except UnicodeEncodeError as err:
        with open("error_file.txt", "a") as file:
            file.write('ERROR: ' + last_post.id_str + '\t' + str(err) + '\n')


def print_status(last_post):
    status_msg = 'https://twitter.com/{screen_name}/status/{twit_id}\n' \
                 '[{created_at}] - {full_text}\nURLs: {url_list}\nImgs: {img_list}\n' \
                 '-> https://twitter.com/{screen_name}/status/{in_reply_to_status_id}\n'
    # print(last_post.full_text)
    url_list = ''
    img_list = ''
    if last_post.entities:
        for url in last_post.entities['urls']:
            url_list += url['expanded_url'] + '\t'
    try:
        if last_post.extended_entities:
            for media in last_post.extended_entities['media']:
                img_list += media['media_url'] + '\t'
    except AttributeError as err:
        img_list = '*********'
    print(status_msg.format(screen_name=last_post.author.screen_name,
                            twit_id=last_post.id_str,
                            created_at=last_post.created_at,
                            full_text=last_post.full_text,
                            url_list=url_list,
                            img_list=img_list,
                            in_reply_to_status_id=last_post.in_reply_to_status_id_str))


def build_thread_last_to_first(api, last_twit_id):
    posts_illustrator = {}
    last_post = Status()
    last_post.in_reply_to_status_id = last_twit_id
    while last_post.in_reply_to_status_id:
        last_post = api.get_status(id=last_post.in_reply_to_status_id, tweet_mode='extended')
        print_status(last_post)
        write_status_to_file(last_post)
        posts_illustrator[last_post.id] = {
            'id': last_post.id,
            'text': last_post.full_text,
            'in_reply_to_status_id': last_post.in_reply_to_status_id
        }


last_twit_ids = [
    '1223361236181622785',
    '1234049934908940288',
    '1245077633823641603',
    '1255566722452553733',
    '1267145173831757826',
    '1278065479240822784',
    '1289299523395678208',
    '1322629306699390979',
    '1333498896547540993',
    '1344685363613282306'
]


def main():
    # Load credentials from json file
    with open("twitter_credentials.json", "r") as file:
        creds = json.load(file)
    auth = tweepy.OAuthHandler(creds["consumer_key"], creds["consumer_secret"])
    try:
        redirect_url = auth.get_authorization_url()

        # Open authorization URL in browser
        webbrowser.open(redirect_url)
        pin = input('Verification pin number from twitter.com: ').strip()

        # Get access token
        token = auth.get_access_token(verifier=pin)

        api = tweepy.API(auth)
        for twit_id in last_twit_ids:
            build_thread_last_to_first(api, twit_id)
        # https://twittercommunity.com/t/view-conversations-api-support/11090
        # As @thom_nic mentioned, the in_reply_to_status_id field can be used as a work around to re-construct a
        # conversation. For any tweets with this field, we can (1) find the tweet this current one is reply to,
        # then go to that tweet to check whether that one has a in_reply_to_status_id field, and continue this step.
        # (2) Search the entire collection of tweets to find whether there exists a tweet with a
        # in_reply_to_status_id that match this current tweet. Do this step for every tweet involved in the
        # conversation.
    except tweepy.TweepError as err:
        print('Error! Failed to get request token.')
        print(err)


if __name__ == "__main__":
    main()
