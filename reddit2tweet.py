# -*- coding: utf-8 -*-
"""
Created on Wed Jun 19 10:07:03 2019

@author: BLEE1
"""

import praw
import json
import requests
import tweepy
import time
import os
import urllib.parse
from glob import glob
import credentials

# Place your Twitter API keys here
ACCESS_TOKEN = credentials.ACCESS_TOKEN
ACCESS_TOKEN_SECRET = credentials.ACCESS_SECRET
CONSUMER_KEY = credentials.CONSUMER_KEY
CONSUMER_SECRET = credentials.CONSUMER_SECRET

# Place your Reddit API secrets here
client_id = credentials.client_id 
client_secret = credentials.client_secret
user_agent = credentials.user_agent
username = credentials.username
password = credentials.password

# Place the subreddit you want to look up posts from here
SUBREDDIT_TO_MONITOR = 'funny'

# Place the name of the folder where the images are downloaded
IMAGE_DIR = 'C:/Users/blee1/Documents/py_script/RedditImg'

# Place the name of the file to store the IDs of posts that have been posted
POSTED_CACHE = 'C:/Users/blee1/Documents/py_script/RedditImg/posted_posts.txt'

# Place the string you want to add at the end of your tweets (can be empty)
TWEET_SUFFIX = ' #gag #9gag'

# Place the maximum length for a tweet
TWEET_MAX_LEN = 140

# Place the time you want to wait between each tweets (in seconds)
DELAY_BETWEEN_TWEETS = 30

# Place the lengths of t.co links (cf https://dev.twitter.com/overview/t.co)
T_CO_LINKS_LEN = 24

def connect_to_reddit(subreddit):
    ''' Connect to Reddit '''
    print('Connecting to reddit...')
    reddit_api = praw.Reddit(client_id=client_id, 
                             client_secret=client_secret,
                             user_agent=user_agent,
                             username=username,
                             password=password)
    return reddit_api.subreddit(subreddit)

def tweeted(post_id):
    ''' Don't want reposts '''
    found = False
    with open(POSTED_CACHE, 'r') as in_file:
        for line in in_file:
            if post_id in line:
                found = True
                break
    return found

def tweet_creator(subreddit_info):
    ''' Gets reddit URL '''
    post_dict = {}
    post_ids = []
    print('Getting posts from Reddit')

    for submission in subreddit_info.hot(limit=5):
        if not tweeted(submission.id):
            # Link to what the post is linking to
            post_dict[submission.title] = {}
            post = post_dict[submission.title]
            post['link'] = submission.url

            # Store the url the post points to (if any)
            # imgur URLs are downloaded and uploaded
            post['img_path'] = get_image(submission.url)
            post_ids.append(submission.id)
        
        else:
            print('Already tweeted: {}'.format(str(submission)))

    return post_dict, post_ids

def strip_title(title, num_characters):
    ''' Limit title length '''

    # For longer URLs use urllib.parse
    if len(title) <= num_characters:
        return title
    else:
        return title[:num_characters - 1] + '…'


def get_image(img_url):
    ''' Download the image '''
    if 'imgur.com' in img_url:
        file_name = os.path.basename(urllib.parse.urlsplit(img_url).path)
        img_path = IMAGE_DIR + '/' + file_name
        print('Downloading image at URL ' + img_url + ' to ' + img_path)
        resp = requests.get(img_url, stream=True)
        if resp.status_code == 200:
            with open(img_path, 'wb') as image_file:
                for chunk in resp:
                    image_file.write(chunk)
            # Return the path of the image, which is always the same since we just overwrite images
            return img_path
        else:
            print('Image failed to download. Status code: ' + resp.status_code)
    else:
        print('Post doesn\'t point to an i.imgur.com link')
    return None


def tweeter(post_dict, post_ids):
    ''' Tweets all of the selected reddit posts '''
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth)

    for post, post_id in zip(post_dict, post_ids):
        img_path = post_dict[post]['img_path']

        extra_text = ' ' + post_dict[post]['link'] + TWEET_SUFFIX
        extra_text_len = 1 + T_CO_LINKS_LEN + len(TWEET_SUFFIX)
        if img_path:  # Image counts as a link
            extra_text_len += T_CO_LINKS_LEN
        post_text = strip_title(post, TWEET_MAX_LEN - extra_text_len) + extra_text
        print('[bot] Posting this link on Twitter')
        print(post_text)
        if img_path:
            print('[bot] With image ' + img_path)
            api.update_with_media(filename=img_path, status=post_text)
        else:
            api.update_status(status=post_text)
        log_tweet(post_id)
        time.sleep(DELAY_BETWEEN_TWEETS)


def log_tweet(post_id):
    ''' Takes note of when the reddit Twitter bot tweeted a post '''
    with open(POSTED_CACHE, 'a') as out_file:
        out_file.write(str(post_id) + '\n')


def main():
    ''' Runs through the bot posting routine once. '''
    # If the tweet tracking file does not already exist, create it
    if not os.path.exists(POSTED_CACHE):
        with open(POSTED_CACHE, 'w'):
            pass
    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR)

    subreddit = connect_to_reddit(SUBREDDIT_TO_MONITOR)
    post_dict, post_ids = tweet_creator(subreddit)
    tweeter(post_dict, post_ids)

    # Clean out the image cache
    for filename in glob(IMAGE_DIR + '/*'):
        os.remove(filename)
