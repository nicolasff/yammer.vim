#!/usr/bin/python

import urllib2, time, random, json, os, urllib

class OAuth:
    def __init__(self, consumer_key, consumer_secret, oauth_token = None, oauth_token_secret = None):
        self.oauth_consumer_key = consumer_key
        self.oauth_consumer_secret = consumer_secret
        self.oauth_token = oauth_token
        self.oauth_token_secret = oauth_token_secret

    def pack(self, d):
        return ','.join(((k + '="' + str(v) + '"') for (k,v) in d.items()))

    def query(self, url, args = {}, postdata = None):
        args['oauth_consumer_key'] = self.oauth_consumer_key
        if self.oauth_token:
            args['oauth_token'] = self.oauth_token
        args['oauth_signature_method'] = 'PLAINTEXT'
        args['oauth_timestamp'] = int(time.time())
        args['oauth_nonce'] = random.randint(0, 2**32)
        args['oauth_signature'] = self.oauth_consumer_secret + '%26'
        if self.oauth_token_secret:
            args['oauth_signature'] += self.oauth_token_secret

        auth = 'OAuth ' + self.pack(args)

        r = urllib2.Request(url, urllib.urlencode(postdata) if postdata else None, {'Authorization': auth})
        result = urllib2.urlopen(r)
        return result.read()

    def split_qs(self, qs):
        args = qs.split('&')
        return dict((s.split('=') for s in args))


    # request oauth token
    def request_token(self):
        ret = self.split_qs(self.query('https://www.yammer.com/oauth/request_token'))
        return (ret['oauth_token'], ret['oauth_token_secret'])

    # request oauth access token
    def request_access(self, verifier):
        return self.split_qs(self.query('https://www.yammer.com/oauth/access_token', {'oauth_verifier': verifier}))

class MessageParser:

    def __init__(self):
        pass

    def read(self, contents):
        obj = json.loads(contents)

        # get users by id and short name
        users_ids = {}
        users_nicks = {}
        for r in obj['references']:
            if r['type'] != 'user':
                continue
            users_ids[r['id']] = r['full_name']
            users_nicks[r['name']] = r['full_name']

        # return string
        messages = [self.format_message(m, users_ids, users_nicks) for m in obj['messages']]

        return messages

    def format_message(self, m, users_ids, users_nicks):

        txt = users_ids[m['sender_id']] + ': '

        message_body = m['body']['plain']
        if '@' in message_body:
            for (k,v) in users_nicks.items():
                message_body = message_body.replace('@'+k, v)    # TODO: color as user name

        txt += message_body

        return {'text': txt, 'parent': m['thread_id'], 'id': m['id'], 'date': m['created_at']}

class MessageFormatter:

    def date_to_timestamp(self, s):
        return time.mktime(time.strptime(s,"%Y/%m/%d %H:%M:%S +0000"))

    def format(self, messages):
        top_msgs = []
        
        for tm in [m for m in messages if m['parent'] == m['id']]:
            tm['latest'] = tm['date']
            tm['children'] = []

            for m in messages:
                if m['parent'] != tm['id'] or m['id'] == tm['id']:    # look for replies
                    continue

                if self.date_to_timestamp(m['date']) > self.date_to_timestamp(tm['latest']):    # update thread freshness
                    tm['latest'] = m['date']

                tm['children'].append(m)

            top_msgs.append(tm)
            tm['children'].sort(key=lambda m: self.date_to_timestamp(m['date']))

        top_msgs.sort(key=lambda m: self.date_to_timestamp(m['latest']))
        top_msgs.reverse()

        # format as text.
        ret = ""
        for tm in top_msgs:
            ret += tm['text'] + "\n"
            first = True
            for cm in tm['children']:
                if first:
                    first = False
                    ret += "  \___  "
                else:
                    ret += "    |_  "
                ret += cm['text'] + "\n"

        return ret

class Yammer:

    def __init__(self):
        self.oauth = OAuth('M9TT2AMa0fTadxrR1jXbA', '8aXNPSeMpxHIYmeZu5G1zmmM6aM4SNbnb4VWnNnB8')
        self.root = 'https://www.yammer.com/api/v1/'
        self.tokenfile = os.path.expanduser("~/.yammervimtoken")
        self.load_credentials()

    def install(self):

        # try to load credentials from saved file.
        if self.load_credentials():
            return True

        # otherwise, request token
        (self.oauth.oauth_token, self.oauth.oauth_token_secret) = self.oauth.request_token()
        url =  "https://www.yammer.com/oauth/authorize?oauth_token=%s" % (self.oauth.oauth_token)

        # open yammer page
        os.system("gnome-open '%s'" % url)
        verifier = raw_input('Enter code from Yammer website: ')
        ret = self.oauth.request_access(verifier)
        self.oauth.oauth_token, self.oauth.oauth_token_secret = ret['oauth_token'], ret['oauth_token_secret']

        # save credentials
        f = open(self.tokenfile, 'w')
        f.write(self.oauth.oauth_token + "\n" + self.oauth.oauth_token_secret)
        f.close()


    def load_credentials(self):
        """ Load OAuth tokens from file"""
        try:
            f = open(self.tokenfile, 'r')
            self.oauth.oauth_token = f.readline().strip()
            self.oauth.oauth_token_secret = f.readline().strip()
            f.close()
            return True
        except:
            return False


    def messages(self):
        return self.load('messages')

    def messages_sent(self):
        return self.load('messages/sent')

    def post(self, txt):
        txt = txt.strip()
        if txt == "":
            return False

        return self.load('messages', '', {'body': txt})

    def load(self, what, get = "", post = {}):
        url = self.root + what + '.json' + get
        return self.oauth.query(url, {}, post)


if __name__ == "__main__":  # install
    print "Installing yammer.vim"
    y = Yammer()
    y.install()
    print "done. Showing messages..."

    mf = MessageFormatter()

    mp = MessageParser()
    messages = mp.read(y.messages())

    s = mf.format(messages)

    print s
