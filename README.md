SubliminalCollaborator
======================

Sublime Text 2 Plugin for remote pair programming.

This project is in active development and not quite feature complete yet, but the intent is to make this into a fully featured and capable 
code collaboration tool with minimal setup and infrastructure to get up and going.

## NEWS

The feature set target for **alpha** has been achieved!  You can now, once you are setup, do the following:

* Connect to an IRC channel and find other SubliminalCollaborator clients to...
    * Share a view over a direct connection (local/company network only, *NAT traversal is a planned feature*)
    * Partner can see the file, including syntax coloring as was configured by the host at the time of send
    * Host and Partner can highlight multiple sections of the file and see what the other is highlighting in real-time
    * Partner's viewpoint follows that of the Host when the Host moves their viewpoint

Instructions below on how to play with this: more details and screenshots coming soon.

## Roadmap

[Planned Milestones](https://github.com/nlloyd/SubliminalCollaborator/issues/milestones)

## Getting Started

**NOTE: command/ctrl + ~ to see what is actually going on.  Right now everything is logged to the sublime console.  Status bar feedback on background operations is a pending feature.**

1. git clone into your Packages directory (When this goes Beta I will add it to the [Sublime Package Control](http://wbond.net/sublime_packages/package_control) repository)
1. Start Sublime Text 2
1. To generate a basic User/Accounts.sublime-settings file, select menu Preferences > Package Settings > SubliminalCollaborator > Settings - User
1. Uncomment the following and fill in with the details for your chosen IRC server (can have multiple under "irc")
```javascript
// "irc": [
//     {
//         "host": "irc.somewhere.com",
//         "port": 6667,
//         "username": "",
//         "password": "",
//         "channel": "subliminalcollaboration"
//     }
// ],
```
1. Save the settings file.
1. From the command palette: `Collaborate: Connect to Chat Server`
1. Select the representative chat config string of your choice (protocol|host:port is the format)
1. Once connected... from the command palette: `Collaborate: Start New Session`
1. Choose the chat connection to use, then the username from the list of the known confirmed SubliminalCollaborator clients available through this chat
    * At this point a dialog between clients is initiated where the two peers attempt to connect directly using the available IP addresses of the peer hosting the session... this may take a while... command/ctrl + ~ to see what is actually going on.
1. Choose a view to share from the presented list of open views.
1. Highlight something!  Tell your peer to highlight something!  Play around with it and give me feedback while I work on adding more to this thing!


## Rough Feature Plan
**old, see [Issues](https://github.com/nlloyd/SubliminalCollaborator/issues?labels=&milestone=&page=1&state=open) and [Milestones](https://github.com/nlloyd/SubliminalCollaborator/issues/milestones) for more accurate details of what is to come.**

The current feature plans:
- quickly share a file with another user identified via IM system (irc and jabber currently targetted)
- support for HOST and PARTNER roles
- HOST role features
    - show currently viewed region of document to PARTNER
    - show highlighted regions of text to PARTNER
    - send edit/delete events to PARTNER as they occur
    - swap HOST-PARTNER role with other user
- PARTNER role features
    - show highlighted regions of text to HOST ('tell me more about this that you just edited')
    - 'follow' and 'unfollow' toggle (whether you follow the HOST view or not)
    - request HOST to swap roles


Show your support by donating!

<a href='http://www.pledgie.com/campaigns/17989'><img alt='Click here to lend your support to: SubliminalCollaborator and make a donation at www.pledgie.com !' src='http://www.pledgie.com/campaigns/17989.png?skin_name=chrome' border='0' /></a>


## License

All of SublimeMaven is licensed under the MIT license.

  Copyright (c) 2012 Nick Lloyd, Frank Papineau, Rippa Gasparyan

  Permission is hereby granted, free of charge, to any person obtaining a copy
  of this software and associated documentation files (the "Software"), to deal
  in the Software without restriction, including without limitation the rights
  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
  copies of the Software, and to permit persons to whom the Software is
  furnished to do so, subject to the following conditions:

  The above copyright notice and this permission notice shall be included in
  all copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
  THE SOFTWARE.
  