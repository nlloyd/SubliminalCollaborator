
print 'SANDBOX YAY!!!'
import sublime, sublime_plugin
import threading
import logging


from oyoyo.client import IRCClient 
from oyoyo.cmdhandler import DefaultCommandHandler  

#def connect_callback(cli):
     # Identify to nickserv
#     helpers.identify(cli, "my9pv")
     
#     helpers.join(cli, "#subliminalcollaborator")	

#class MyHandler(DefaultCommandHandler): 

# Handle messages (the PRIVMSG command, note lower case)     
#	def privmsg(self, nick, chan, msg):         
#		print "%s in %s said: %s" % (nick, chan, msg) 

#cli = IRCClient(MyHandler, host="irc1.pearsoncmg.com", port=6667, nick="frankp")

#conn = cli.connect()

#conn

# # def connect_callback(cli):
# #     # Identify to nickserv
# #     helpers.identify(cli, "my9pv")

# #     # Join the channel '#test'
# #     helpers.join(cli, "#subliminalcollaborator")

class MyHandler(DefaultCommandHandler):
    def privmsg(self, nick, chan, msg):
        print "%s in %s said: %s" % (nick, chan, msg)

cli = IRCClient(MyHandler, host="irc.pearsoncmg.com", port=6667, nick="subliminal_nick",
         connect_cb=None)

class IRCClientThread(threading.Thread): 
    def __init__(self, irc_client):
        self.client = irc_client
        threading.Thread.__init__(self)

    def run(self):
        logging.basicConfig(level=logging.DEBUG)
        conn = self.client.connect()
        while True:
         conn.next()

       	irc_thread = IRCClientThread(cli)
       	irc_thread.start()

settings = sublime.load_settings('Preferences.sublime-settings')
#{
#    'sublinimal_collaborator_config': {
#        'irc': {
#            'host': "irc.pearsoncmg.com",
#            'port': 6667,
#            'pwd': "my9pv",
#            'nick': "subliminal_nick"
#        }
#        }
#}
collab_config = settings.get('subliminal_collaborator_config', None)

	
class CollabSessionBlahBlah(sublime_plugin.WindowCommand):

    def run(self):
        self.window.show_quick_panel(['Share active view (default)', 'Share other view...'])

    def view_to_share(self, choice_idx):
        if choice_idx < 1:
            print 'blah'
        else:
            view_names = []
