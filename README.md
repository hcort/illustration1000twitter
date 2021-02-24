# illustration1000twitter
## Download Twitter threads using the API

See https://twittercommunity.com/t/view-conversations-api-support/11090

```
As @thom_nic mentioned, the in_reply_to_status_id field can be used as a work around to re-construct a conversation. 
For any tweets with this field, we can (1) find the tweet this current one is reply to, then go to that tweet to check 
whether that one has a in_reply_to_status_id field, and continue this step. (2) Search the entire collection of tweets
to find whether there exists a tweet with a in_reply_to_status_id that match this current tweet. 
Do this step for every tweet involved in the conversation.
```
Every tweet found in this way is stored in a json file so the thread can be reconstructed later without accessing the Twitter API.

You have to manually scroll to the last tweet in the thread in order to get its id.

## Reconstruct Twitter thread

All the json files are dumped into a MongoDB collection. After this we can rebuild a thread retrieving tweets using the in_reply_to_status_id.

Once the thread is rebuilt it is stored in another MongoDB collection and printed into an HTML file with a lighter format.

TODO
* Integrate thread parsing with database, avoid intermediate json files.
* Download image files.
