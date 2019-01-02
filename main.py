# coding:utf-8
from flask import Flask, jsonify, abort, make_response
import sys
import feedparser
from requests_oauthlib import OAuth1Session
import re
import MeCab
import json, config
import random
import markovify

RSS_URL = "http://feeds.feedburner.com/hatena/b/hotentry"

CK = config.CONSUMER_KEY
CS = config.CONSUMER_SECRET
AT = config.ACCESS_TOKEN
ATS = config.ACCESS_TOKEN_SECRET

def text_from_hotentry():
  combined_text = ""

  dic = feedparser.parse(RSS_URL)

  p = re.compile(r"<[^>]*?>")
  for entry in dic.entries:
    title = re.sub("( \| | \- |:).+", "", entry.title)
    title = re.sub("（.+）$", "", title)
    combined_text += title + "。"
    combined_text += re.sub(r"<[^>]*?>", "", entry.content[0].value)

  return combined_text

def text_from_twitter(twitter_name):
  combined_text = ""

  args = sys.argv
  twitter = OAuth1Session(CK, CS, AT, ATS)
  twitter_params ={'count' : 100}
  url = "https://api.twitter.com/1.1/statuses/user_timeline.json?screen_name=" + twitter_name
  res = twitter.get(url, params = twitter_params)

  if res.status_code == 200:
      timelines = json.loads(res.text)
      for line in timelines:
          text = re.sub("https?://[\w/:%#\$&\?\(\)~\.=\+\-]+", "", line['text']) + "\n"
          combined_text += re.sub("@[\w]+", "", text) + "。"

  return combined_text

def model_from_text(text):
  sentences = []
  m = MeCab.Tagger("-Ochasen")
  m.parse("")
  result = m.parse(text).split("\n")
  
  breaking_chars = [
      '(',
      ')',
      '[',
      ']',
      '"',
      "'",
      "「",
      "」",
      "『",
      "』",
  ]

  sentence = ""
  for item in result:
      str = item.split("\t")
      if str[0] not in breaking_chars:
        sentence += str[0]
      if str[0] != '。' and str[0] != '、':
        sentence += ' '
      if str[0] == '。':
        sentences.append(sentence + '\n')
        sentence = ""
  
  random.shuffle(sentences)
  text = ''.join(sentences)

  text_model = markovify.NewlineText(text, state_size=2)

  return text_model

api = Flask(__name__)

@api.route('/markovify/<string:twitter_name>', methods=['GET'])
def main(twitter_name):
  text = text_from_hotentry()
  hotentry_model = model_from_text(text)

  text += text_from_twitter(twitter_name)
  twitter_model = model_from_text(text)
  
  model = markovify.combine([ hotentry_model, twitter_model ], [ 3, 1 ])

  result = []
  for i in range(3):
      result.append(model.make_short_sentence(60).replace(" ", ""))

  # return make_response(jsonify(result))
  return make_response(json.dumps(result, ensure_ascii=False))

if __name__ == '__main__':
    api.run(host='0.0.0.0', port=3000)