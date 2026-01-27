import urllib
import json
import time

# Class for accessing KOPO MES server for retrieving and sending messages for a chapter of a journey
class Message(object):
    def __init__(self, username, passwd, lesson_id, pathToDataFolder = "C:"):
        """
        Initilize the new object
        :param username: username of a KOPO MES account
        :param passwd: password
        :param lesson_id: chapter ID of a journey at KOPO MES. Create a journey and a chapter without any questions. Get the chapter ID as lesson_id.
        """
        self.webservice_url = 'https://www.a.kopo.com/ws/ib.php'
        #self.webservice_url = 'http://localhost/m/ib.php'
        self.username = username
        self.passwd = passwd
        self.user_id = 0
        self.sbj_id = 0
        self.lesson_id = lesson_id

        self.umsg_id = 0  # keep track of the last message process
        self.messages = [] # retrieved messages
        self.pathToDataFolder = pathToDataFolder

    def login(self):
        """
        Login to KOPO MES using the username and password.
        :return: dictionary {'err': 0 if success, 1 if error logging in, 'msg': 'Any message',...}
        """
        data_values = {'s' : 'login',
                  'username' : self.username,
                  'password' : self.passwd }
        data = urllib.urlencode(data_values)

        httprequest = urllib.Request(self.webservice_url, data)
        response = urllib.urlopen(httprequest)  # send a HTTP request
        self.cookie = response.headers.get('Set-Cookie')  # get the cookie to reuse the session
        html = response.read()
        #print html   # print out what we received from the server
        r = self.parseJson(html)
        if r['err'] == 0:
            self.user_id = r['user_id']
            self.skey = r['skey']
        return r

    def retrieveMessages(self):
        """
        Retrieve the latest 50 messages from the sever for the lesson (chapter of a journey).
        Server returns maximum 50 messages, the latest first in descending order of umsg_id (message id)
        :return: dictionary. {'err': 0 if no error, 1 if error while retrieving the messages, ...}
        """
        data_values = {'s' : 'gmsg_bot',  # get messages (sent, received) since umsg_id in ascending order. The latest the last
                  'skey' : self.skey,
                  'user_id' : self.user_id,
                  'umsg_id' : self.umsg_id,          # get messages greater than this message id.
                  'lesson_id': self.lesson_id}
        data = urllib.urlencode(data_values)
        req2 = urllib.Request(self.webservice_url, data)
        req2.add_header('cookie', self.cookie)      # reuse the session. Need this
        response = urllib.urlopen(req2)
        html = response.read()
        r = self.parseJson(html)
        if r['err'] == 0:
            self.messages = r['records']
            self.umsg_id = self.messages[0]['umsg_id'] # the last message id
            self.sbj_id = self.messages[0]['sbj_id']  # subject id (journey)
        return r

    def getUserID(self):
        return self.user_id

    def getMessages(self):
        """
        Return the retrieved messages

        :return: an array of messages. Each memssage is a dictionary. E.g., messages[0]['umsg_id'] = message id
        """
        return self.messages

    def getLastMessage(self):
        """
        Find the latest message to reply to from the retrieved messages.

        :return: the message record if it finds, 0 if cannot find one.
        """
        self.sbj_id = 0
        for msg in self.messages:
            sid = msg['user_id']
            if sid > 0 and msg['receiver_id'] > 0:
                self.sbj_id = msg['sbj_id']  # subject id (journey)
                return msg
        return 0  # cannot find a msg

    def downloadMessageFile(self, msg):
        """
        Download the first file attached to the msg if any.

        :param msg:
        :return: file data received
        """
        fileid1 = msg['fileid1']
        filename1 = msg['fileid1']
        umsg_id = msg['umsg_id']
        if fileid1 > 0:
            # downloading file
            data_values = {'s' : 'gmfl_bot',   # service code for sending a new message to a student
                      'skey' : self.skey,
                      'user_id' : self.user_id,
                      'umsg_id' : umsg_id,
                      'fileid' : fileid1
                      }
            data = urllib.urlencode(data_values)
            f = urllib.urlopen(self.webservice_url, data)
            fdata = f.read()
            # save the file if needed
            #with open(self.pathToDataFolder + '/' + filename1, "wb") as myfile:
            #    myfile.write(fdata)
            return fdata
        else:
            print("No file attached")
            return 0

    def sendMessage(self, receiver_id, content = "Hi"):
        """
        Send a message for the current subject (journey) and lesson (chapter) to the receiver
        :param receiver_id: user id of the receiver
        :param content: content of the message. It can be in HTML or just a plain text.
        :return: dictionary {'err': 0 if no error, 1 if error,...}
        """

        if receiver_id == self.user_id:
            return {'err':1,'msg':'Sender and receiver are the same.'}  # cannot send to yourself

        if self.sbj_id <= 0:
            return {'err':1,'msg':'sbj_id invalid.'}

        data_values = {'s' : 'smsg_bot',   # service code for sending a new message to a student
                  'skey' : self.skey,
                  'user_id' : self.user_id,
                  'receiver_id' : receiver_id,    # user_id of the student. must be > 0
                  'sbj_id' : self.sbj_id,              # subject (journey). must be > 0
                  'lesson_id' : self.lesson_id,        # lesson (chapter of the journey). must be > 0
                  'content' : content             # message content goes here
                  }

        data = urllib.urlencode(data_values)
        req3 = urllib.Request(self.webservice_url, data)
        req3.add_header('cookie', self.cookie)
        response = urllib.urlopen(req3)
        html = response.read()
        #print html   # the result. If err = 1, something went wrong

        return self.parseJson(html)

    def parseJson(self, s):
        try:
            response_json = json.loads(s)
            return self.convertInt(response_json)
        except:
            print(s)
            return {'err':1, 'msg': 'Error parsing JSON string'}

    def convertInt(self, j):
        if isinstance(j,dict):
            for key, value in j.iteritems():
                j[key] = self.convertInt(value)
            return j
        elif isinstance(j, basestring):
            if self.isInt(j):
                return int(j)
            else:
                return j
        elif isinstance(j, list):
            l = []
            for v in j:
                l.append(self.convertInt(v))
            return l
        else:
            return j

    def isInt(self, s):
        try:
            int(s)
            return True
        except ValueError:
            return False

    def processMessages(self, messageComposer, buildDatabase=None):
        print("Attempting to login...")
        r = self.login()
        if r['err'] > 0:
            print(r)  # login failed
            return 1
        print("Login success. Begin processing messages.")

        # login success, start processing messages
        while True:
            # now pause for a while to allow new messages arrive
            time.sleep(5)  # !! do not change this. Your IP and account may get blocked if send requests too frequently.

            # print 'Fetching new message records.'
            r = self.retrieveMessages()  # retrieve the last 5 messages
            if r['err'] > 0:
                # print r # no messages or error
                continue

            # print 'Got some new messages. Finding a new message to reply to.',
            print(r)
            msgs = self.getMessages() # get the retrieved messages
            if buildDatabase is not None:
                buildDatabase(msgs)  # callback
            users = []  # keep track of users we replied this round to avoid replying old messages
            for msg in msgs:
                receiver_id = msg['user_id']
                if (receiver_id <=0 ) or (receiver_id in users):
                    continue # skip invalid user_id and users that we already replied

                users.append(receiver_id)
                if receiver_id == self.getUserID(): # check if the sender is me
                    print('Sender is the same as the receiver, skipping') # shouldn't reply to itself
                    continue # skip

                # get seonder details
                sendername = msg['sendername']  # name of the sender
                content = msg['content']        # content of the message
                umsg_id = msg['umsg_id']     # message id

                # optionally get the file attached if any
                fdata = self.downloadMessageFile(msg)

                # compose content for replying
                content = messageComposer(msg, fdata)  # we should use some machine learning tools to compose a reply message

                # send a reply to the student for the chapter
                print('Sending message to ', receiver_id, sendername)
                r = self.sendMessage(receiver_id, content)
                if r['err'] > 0:
                    print(r)  # something went wrong. exiting program
                    return 1

# Test the api
if __name__ == '__main__':
    print("Hi this is API to be imported to another program")

#--------------------------------------------
