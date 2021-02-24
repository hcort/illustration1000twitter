import json
import os
import re
from json import JSONDecodeError

from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from illustratorThread import last_twit_ids


def format_string_local(usr, pwd, host, dbname):
    # TODO leer puerto desde un parámetro
    return "mongodb://{usr}:{pwd}@{host}/{dbname}".format(usr=usr, pwd=pwd, host=host, dbname=dbname)


def format_string_atlas(usr, pwd, host, dbname):
    return "mongodb+srv://{usr}:{pwd}@{host}/{dbname}".format(usr=usr, pwd=pwd, host=host, dbname=dbname)


class MongoDBConnection:
    def __init__(self, usr, pwd, host, dbname):
        self.__user = usr
        self.__pwd = pwd
        self.__host = host
        self.__dbname = dbname
        self.connection = None
        self.__conn_str = ''

    def __enter__(self):
        self.__conn_str = format_string_local(self.__user, self.__pwd, self.__host, self.__dbname)
        print(self.__conn_str)
        self.connection = MongoClient(self.__conn_str)
        # self.connection = MongoClient(host=self.__host, username=self.__user, password=self.__pwd)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connection.close()


def character_list_to_url_list(char_list):
    # por un error aparecen como "url_list": ["h", "t", "t", "p", "s", ":", "/", "/", "i", "n", "s", "t", "a", ...
    url_list_str = ''.join(char_list)
    split_str = [value for value in re.split('(https?://)', url_list_str) if value]
    k = 2
    return [split_str[idx * k] + split_str[idx * k + 1] for idx, item in enumerate(split_str[::k])]


def fix_bad_url_img(obj):
    if obj['url_list']:
        obj['url_list'] = character_list_to_url_list(obj['url_list'])
    if obj['img_list']:
        obj['img_list'] = character_list_to_url_list(obj['img_list'])


def populate_collection_from_files(collection, path):
    for file in os.scandir(path):
        try:
            with open(file.path, 'r') as jsonfile:
                obj = json.loads(jsonfile.read())
                if collection.find_one({"twit_id": obj['twit_id']}):
                    print(obj['twit_id'] + ' -> repetido')
                else:
                    collection.insert_one(obj)
            os.remove(file.path)
        except JSONDecodeError as err:
            print(file.path + ' -> ' + str(err))


def dump_collection(source, dest):
    for item in list(source.find()):
        try:
            dest.insert_one(item)
        except DuplicateKeyError as err:
            print(str(err))


def generate_thread_from_last_post(coleccion, last_post_id):
    last_tweet = coleccion.find_one({"twit_id": last_post_id})
    thread = {
        'first_tweet': '',
        'first_tweet_text': '',
        'partial': False,
        'last_tweet': last_post_id,
        'tweets': [last_post_id]
    }
    if not last_tweet:
        return None
    while last_tweet['in_reply_to_status_id']:
        last_tweet = coleccion.find_one({"twit_id": last_tweet['in_reply_to_status_id']})
        if last_tweet:
            thread['tweets'].append(last_tweet['twit_id'])
        else:
            thread['partial'] = True
            break
    if not last_tweet:
        # hilo incompleto -> el tweet más antiguo es thread['tweets'][-1]
        last_tweet = coleccion.find_one({"twit_id": thread['tweets'][-1]})
    thread['first_tweet'] = last_tweet['twit_id']
    thread['first_tweet_text'] = last_tweet['full_text']
    reverse_list = thread['tweets'][::-1]
    thread['tweets'] = reverse_list
    return thread


def create_html_thread(coleccion, thread, is_partial=False):
    output_filename = os.path.join('html_files', thread['first_tweet'] + ('_parcial_' if is_partial else '') + '.html')
    with open(output_filename, 'w+', encoding="utf-8") as output_file:
        try:
            with open('html_output.html') as html_header:
                output_file.writelines(html_header.readlines())
            total = len(thread['tweets'])
            for idx, tweet_id in enumerate(thread['tweets']):
                tweet = coleccion.find_one({"twit_id": tweet_id})
                div_pattern = "<div class=\"grid-item\">" \
                              "<div>{tweet_header}</div>" \
                              "<div>{tweet_text}</div>" \
                              "<div>{url_list}</div>" \
                              "<div>{img_list}</div>" \
                              "</div>"
                tweet_header = '<p>#{idx}/{total} - ' \
                               '<a href=\"{url}\">{tweet_id}</a> - Posted: {date}</p>'.format(idx=str(idx + 1),
                                                                                              total=str(total),
                                                                                              url=tweet['twit_url'],
                                                                                              tweet_id=tweet['twit_id'],
                                                                                              date=tweet['created_at'])
                tweet_text = '<p>' + tweet['full_text'] + '</p>'
                url_list = "<p><ul>"
                for url in tweet['url_list']:
                    url_list += "<li><a href=\"" + url + "\">" + url + "</a></li>"
                url_list += "</ul></p>"
                img_container = "<div class=\"flex\">"
                for img in tweet['img_list']:
                    img_container += "<div><img src=\"" + img + "\"/></div>"
                img_container += "</div>"
                formatted_div = div_pattern.format(tweet_header=tweet_header,
                                                   tweet_text=tweet_text,
                                                   url_list=url_list,
                                                   img_list=img_container)
                output_file.write(formatted_div)
        finally:
            # escribir pie de HTML
            html_footer = "</div></body></html>"
            output_file.write(html_footer)


def check_full_thread_is_stored(last_tweet_id):
    thread = None
    with open("twitter_credentials.json", "r") as file:
        creds = json.load(file)
    with MongoDBConnection(creds["mongo_user"], creds["mongo_pass"], creds["mongo_local"],
                           creds["mongo_dbname"]) as mongo:
        database = mongo.connection['twitterillustration']
        coleccion_threads = database['threads']
        thread = coleccion_threads.find_one({'last_tweet': last_tweet_id})
    return thread is not None


def main():
    # Load credentials from json file
    with open("twitter_credentials.json", "r") as file:
        creds = json.load(file)
    with MongoDBConnection(creds["mongo_user"], creds["mongo_pass"], creds["mongo_local"],
                           creds["mongo_dbname"]) as mongo:
        database = mongo.connection['twitterillustration']
        coleccion_tweets = database['downloadedtweets']
        for item in last_twit_ids:
            thread = generate_thread_from_last_post(coleccion_tweets, item)
            if thread:
                if not thread['partial']:
                    coleccion_threads = database['threads']
                    coleccion_threads.insert_one(thread)
                else:
                    print('El hilo ' + item + ' no está completo en la base de datos')
                create_html_thread(coleccion_tweets, thread, thread['partial'])
            else:
                print('El hilo ' + item + ' no existe en la base de datos')


if __name__ == "__main__":
    main()
