SubliminalCollaborator
======================

Sublime Text 2 Plugin for remote pair programming.

## NEWS

The feature set target for **beta** has been achieved!  You can now, once you are setup, do the following:

* Connect to an IRC channel and find other SubliminalCollaborator clients to...
    * Share a view over a direct connection (local/company network only, *NAT traversal is a planned feature*)
    * Partner can see the file, including syntax coloring as was configured by the host at the time of send
    * Host and Partner can highlight multiple sections of the file and see what the other is highlighting in real-time
    * Partner's viewpoint follows that of the Host when the Host moves their viewpoint
    * Host edits and cut, copy, and paste events are sent to the Partner
    * Automatic resync if the Host and Partner view become out of sync
    * Swap on demand sharing roles (initiated by either Host or Partner)

Also new, Google Group space for this project!  Since github doesn't offer much by way of a dialog with users and contributors we have [this Google Group]() setup for future use.

Have a feature idea that you want to discuss? [Bring it up here](https://groups.google.com/forum/?fromgroups#!forum/subliminalcollaborator)
Have a question about a feature? [Bring it up here](https://groups.google.com/forum/?fromgroups#!forum/subliminalcollaborator)
Have a bug you want to report? [Bring it up here](https://groups.google.com/forum/?fromgroups#!forum/subliminalcollaborator)
Want to hear about the latest that is happening on this project? [Read about it here!](https://groups.google.com/forum/?fromgroups#!forum/subliminalcollaborator)


## Roadmap

[Planned Milestones](https://github.com/nlloyd/SubliminalCollaborator/issues/milestones)
[Issues](https://github.com/nlloyd/SubliminalCollaborator/issues?labels=&milestone=&page=1&state=open)

## Getting Started

### Setup and Configuration

1. git clone into your Packages directory (When this goes Beta I will add it to the [Sublime Package Control](http://wbond.net/sublime_packages/package_control) repository)
1. Start Sublime Text 2
1. To generate a basic **User/Accounts.sublime-settings file, select menu Preferences > Package Settings > SubliminalCollaborator > Settings - User**
1. Uncomment the following and fill in with the details for your chosen IRC server (can have multiple under "irc")... then save.

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

#### Install/Uninstall Cut, Copy, Paste Proxy

In order to share cut, copy, and paste events in a session some special setup is required...

1. Select the menu **Preferences > Package Settings > SubliminalCollaborator > Install Edit Menu Proxy Commands** or in the command palette select `Collaborate: Install Edit Menu Proxy Commands`.

To undo this action, choose `Uninstall Edit Menu Proxy Commands` in the same places.

### Starting a Session

1. From the command palette: `Collaborate: Connect to Chat Server`
1. Select the representative chat config string of your choice (protocol|host:port is the format)
1. Once connected... from the command palette: `Collaborate: Start New Session`
1. Choose the chat connection to use, then the username from the list of the known confirmed SubliminalCollaborator clients available through this chat
    * At this point a dialog between clients is initiated where the two peers attempt to connect directly using the available IP addresses of the peer hosting the session... this may take a while... command/ctrl + ~ to see what is actually going on or just follow along with the updates in the status bar.
1. Choose a view to share from the presented list of open views.


### Interacting in a Session

Now that you are in a session you can do the following as the host:

- Edit the shared view in almost any way (typical edits such as entering and deleting text as well as cut, copy, and paste).
- Scroll the view and the peer will see what you see.
- Any selections are specially highlighted on the peer's view.
- If the view gets out-of-sync for any reason then an automatic resync will occur with minimal interruption (you as the host won't see anything except a brief message in the status bar).
- At any time from the command palette choose Collaborate: Swap Roles with Peer to request a role change and, if your peer accepts, then they will become the host and you the watching peer.

If you are not the host you can:

- See what the host sees, and while they are not moving the view you may freely scroll independently.
- Highlight regions of interest and those regions will be specially highlighted in the host's view.
- See highlighted regions of the host's view.
- Request through the command palette to swap roles with the host via the Collaborate: Swap Roles with Peer command.

## Troubleshooting

#### Partner view stutters periodically

This is a known issue with the automatic resync mechanism.  Basically chunks of the view are sent very quickly to be updated on the partner side, and the view attempts to follow the location of these edits.  Work is ongoing to find a solution to this.

#### Cut, Copy, and Paste no longer working

Something bad happened with the plugin, you haven't installed the command proxy as instructed below, or you uninstalled the plugin without uninstalling the command proxy.  For most cases you can simply copy the file, if it exists, from **~/.subliminal_collaborator/Main.sublime-menu.backup** into **path/to/SublimeText/Packages/Default**, renaming it and overwriting **Main.sublime-menu**.


Show your support by donating!

<a href='http://www.pledgie.com/campaigns/17989'><img alt='Click here to lend your support to: SubliminalCollaborator and make a donation at www.pledgie.com !' src='http://www.pledgie.com/campaigns/17989.png?skin_name=chrome' border='0' /></a>


## License

All of SubliminalCollaborator is licensed under the MIT license.

  Copyright (c) 2012 Nick Lloyd

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
  