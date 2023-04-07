# Netboot Studio TODO List

March 26, 2023



Musings on rewriting of UI presentation layer
* much more object orientation and polymorphism
* object own their html elements
* objects clean themselves up when requested

March 23, 2023

Can we do image maintenance tasks using dism and wine?
  * add drivers
  * install updates



https://www.winehq.org/pipermail/wine-bugs/2016-September/450767.html
```
$ export WINEARCH=win32 WINEPREFIX=$HOME/.wine32
$ winetricks -q dotnet452 wininet
$ winecfg # set Windows version to 10
$ wine adksetup.exe /features OptionId.DeploymentTools
$ cd $WINEPREFIX/drive_c/Program\ Files/Windows\ Kits/10/Assessment\ and\
Deployment\ Kit/Deployment\ Tools/x86/DISM
$ wine dism.exe
```


https://www.winhelponline.com/blog/slipstream-windows-10-integrate-updates-setup-media-iso/

```
dism.exe /Get-WimInfo /wimFile:"D:\Win10ISO\sources\install.wim"
dism.exe /image:"D:\Mounted-WIM" /Add-Package /PackagePath:"D:\v1709 updates"
dism.exe /Unmount-wim /mountdir:"D:\Mounted-WIM" /commit
```


how to download updates:
https://www.winhelponline.com/blog/download-update-wu-catalog-rss-using-any-browser/

https://github.com/potatoqualitee/kbupdate

https://github.com/aaronparker/LatestUpdate



March 20, 2023

* reject un-named taskss

* rework "i just logged in" flow
  * client list needs to be properly selected
  * cool animation while connecting to broker and initializing data sources
  * make sure to cleanup stuff when de-authed

* need tasks to be retry-able (optionally edit input fields)

* we need buttons in tasks pane
  * cancel task
  * clear task (deletes any temp folders), not available for running tasks
  * clear all tasks (skips running)
  * view (stream?) task logfile
    * create a bespoke mqtt topic for this task, and publish each new line as they are appended to the logfile
  * end-tasks should define these, not the parent class

* Dynamic unattended config
  * we support only 3 types of unattended configs: windows, debian/ubuntu, vmware
  * based on image_type in metadata.yaml, for the assigned boot_image, render unattended.cfg from a common set of data
  * new type of on-disk, or in-database config, storing a bunch of generic common keys, and also special keys only used by certain installers
  * render all unattended.cfg from common set of data, different templates

March 18, 2023

New overall goal set:

* move evrything over to user: netbootstudio
* integrate with AD for auth
  * login and check group membership to determine roles
  * in settings, add fields for mapping groups to roles
    * Admin - full control, including appliance manager
    * Manager - can edit server-wide settings
    * Creator - can create and modify files for netbooting and unattended
    * Installer - can edit client settings for netbooting
    * Viewer - can only view client status / dashboard
* appliance manager for updates, status
  * can appliance manager be the first-time installer too?
    * we can elminate need to reboot by (re) starting needed services, loading modules
    * what if we repurpose the debian liveimage scripts to create a ready-to-go debian installation, and distribute the vmdk?
  * Update = stop & remove all existing containers, clone repo, run install script, deploy
  * manage certificates
  * Backups
    * export database
    * export all config files as single package (just zip everything)
    * export boot images as a separate package
    * auto-backup to NFS/SMB share?
* improve support for Windows unattended
  * add computer to domain
  * install programs
  * modify registry
  * run powershell & cmd commands
  * mount network paths
  * add local user
* Add more things to settings
  * ipxe git repo
* create boot image wizard
  * ESX
  * Windows from ISO
  * Windows from ?? custom image builder?
  * WinPE (or some kind of live image)
  * Debian via web
  * Debian via locally cached files
  * Gparted
  * Clonezilla
  * Ubuntu Livecd
  * Custom Debian Livecd
  * Generic ISO parser
    * detect various iso boot formats and attempt to make it bootable via netboot
    * is there a UEFI tool that can boot iso files directly?


Nov 27 NOtes

Windows
  * join a domain
  * probably skip the rest, let group policy do it

we can use dhcp overrides for the ipxe.bin file. by calling ipxe-arm64.efi, it will ignore arch and return arm64 version
ctrl+b for troubleshooting menu seems broke. didnt work on NUC or on rockpi dec 2, 2021

need to find a way to deliver stage4 output.log to server for troubleshooting

## Thanksgiving Sprint - Nov 17, 2021
This is what we want to get done in order to show Joe at thanksgiving

* nfs server issue fixed, BUT it does not start up automatically after reboot
  
* tasks pane remaining work:
  * cancel task button
  * buttons in general
  * need timeout for cleaning out the tasks lists (get_tasks() being called every second is a decent time to check if expirations)
    * task status entries have expirations (just like client state)
    * every call to send_message resets the expiration date to now + 30 minutes?

* webui
  * Create Image task wizard
    * create it
    * showmodal now has pages, need to animate next and previous motions
* tasks
  * create new image: debian netinstall
  * create new image: debian liveimage

### if we have time
* make edit modal, and make it work for uboot scripts, ipxe stage1, unattended configs
* add a "hey, you dont have any ipxe builds yet" warning pop-up
* need a delete confirmation dialog

### Next Sprint

* backend
  * we have client state, still need to:
    * revisit and document 4hr timeout for stuff
  * we need to make stage4 for windows work at least enough to report state
    * also, mount.cmd can set a state "Unattended: mounting smb share"
      * vaguely remember doing the effective same as curl on windows cmd is difficult. need a reliable solution
  * Flesh out tasks, make things work perfect on arm64 host (including building amd64 binaries)
    * building ipxe for amd64 clients, on an arm64 host will be challenging and slow

  * we now "own" unattended config files, so we need to create a wizard for generating them
    * ultimately this is good news, we can handle a lot of things that were previously in the users hands
    * can we store unattended config in a neutral enough format that we could generate windows/linux/vmware config files from that single source?
    * should we support manually crafted config files?

  * Make another attempt at using watchdog for filewatcher
  * tasks
    * create build wimboot task
      * can it be built for arm64??
    * create task new image windows from iso
    * create task new image vmware esx from iso
    * create task new image gparted live from iso
      * do we even care? our own live image creation wizard sorta makes this pointless
* webui
    * make wimboot builds tab work, no edit, no downloads
    * client list should show ipxe build by name, not uuid
    * hide delete buttons for builtins, need to redo fancylist

### Following Sprint

* put taskmanager in a separate container, one that can scale out in a docker swarm
  * tasks queue becomes a sql table
    * worker instances can try to get a task from the table, we just need to do a locksync where we get and delete that row from the table in the same transaction
  * /opt/NetbootStudio needs to be mounted the same on all hosts

### Backlog
* for windows 11 you can bypass the secure boot and TPM checks
  * create HKEY_LOCAL_MACHINE -> SYSTEM -> Setup -> LabConfig
  * two keys (32bit dword, value 1 for both):
    * BypassTPMCheck
    * BypassSecureBootCheck
  * do this before running setup and you should be good to go
  * to bring up prompt during setup, shift + f10
  * if it says not campatible, just hit back one page and do the above steps
* Windows on arm64
  * the only roadblock is that wimboot is not available on arm64 yet.
  * if we can figure out how to boot windows in a different way without wimboot, we can do it
* we currently provide zero feedback for login success/failure
  * good time for a toast message?
  * also we should use the loading screen while trying
* messageprocessor name is a relic of older paradigm. 
  * rename to apiprocessor or something similar, and shift functionality around so that it only handles api call
* eradicate NSMessage
  * relic, still used in a couple places, can be distilled to just contents (all the nsmessage header crap is pointless now)
* a wizard for generating simple .deb and .rpm files
  * we would also need to host our own repo for these
* task names need to include name
* ipxe builds are not reporting failures
  * probably an overall tasks problem
* we need ntp server info in config file and first-time setup
  * right now we are presuming ntp server is the same as gateway provided by dhcp
* for ipxe builds we can have special console setting, heck we should make all the builds options configurable
  * dont forget to make a way to flag certian build options as required or disallowed
```
#define COMCONSOLE COM2
#define COMSPEED 9600
#define COMDATA 8
#define COMPARITY 0
#define COMSTOP 1
 ```

* in clients list, the config: boot image -> unattended thing looks alright, lets turn into chips for each item so it looks nicer
* in messageprocessor, we should name q_staging -> tasks_staging_queue or something
* should we have a checkbox for do_stage4 ?
* right now we are using ubuntu as our docker base
  * why not debian:bullseye-slim ?
* for vmware, we can on-demand generate an extra.tgz to give the installer: https://github.com/lamw/stateless-esxi-arm
* if a boot image has non-compliant or missing metadata.yml, just ignore it. dont print a stacktrace
* if a new file is added while i have a drop-down menu visible tied to that data source, the new item goes at the bottom of the drop-down instead of sorted
* tweak sorting, put builtins first anyway
* lets generate a separate boot_images list for each arch, and only use the arch we need in the edit client modal
  * arch: none goes on both lists
* SSL for database?
* can we make it so stage server can be https again? 
  * issue was clients without realtime clock cant validate certs because wrong date
  * clients now update clock from ntp (but only affects ipxe, not hw clock), so in theory we can go back to https now
* when stage server moves back to https, need a single http endpoint that can be fetched for a helpful error message
  * or maybe this should happen in stage1
* move boot_image name to metadata (for folder images) so we can use spaces in names 
  * folder becomes name with spaces replaced by underscore, and is not updated if you edit name later on
  * foldername is entirely arbitrary, we dont use it outside of the actual paths
  * OR: just make boot_image folders uuids
* metadata for ipxebuilds is in .json, but for boot images is .yaml. change both to .yaml
  * consider changing config.ini to config.yaml as well
* if this is the first ipxe build for this arch, set it as default
* for tftp_root we need a file/folder tree structure to explore instead of fancylist
* need to add supports_unattended to boot image info in ui
* when scanning boot images, ignore any folders with
  * invalid characters in name?
* boot_images (and others) need to be sorted by name when returned by api
  * they are sorted, but now builtins are not at the top and should be
* where to fdt files come from?
  * user can uplod them on the tftp tab, but where does the user find them?
  * can we get them automatically?
* in mqtt message, info and config are transmitted as encoded strings instead of dicts
* use manufacturer mac address lookup to get more info
* add docstrings to everything
  * generate docs using docutils
  * use restructuredtext comment style (epytext is ancient, dead since 2009)
    * did a bunch, still more to go
* clean up tftp file access logging
  * info level message only if file found, remove debug message
* figure out how to log access to files that are behind web.static
  * there is a logger parameter we currently set to None
* update documentation regarding license, and licences of libraries
* first-time-installation:
  * generate a secrets file (gitignored) and use it when deploying docker, and for live config
  * partway done, config.ini now contains auto-generated uuids for passwords
  * first-time-setup generates these uuid passwords, they do not change in the course of normal use
* other:
  * Need http to redirect to https (right now we just get connection reset)
  * fix auth issues
    * lots of web resources are not behind auth, lets get everything we can behind auth
    * auth tokens are not being regularly refreshed, so a browser session becomes stale if it sits for a while
    * but also, everything is going over mqtt and that session stays active regardless
    * the auth token system is not really doing much in the way of security
    * also, need timeout for auto logout
  * need a way to backup all config, including database
  * manage files in tftp_root (upload / delete / rename)
    * disallow/ignore reserved boot.scr.uimg and ipxe.bin
* ipxe should add vci and user_class info
* we will need to translate a lot of the old v1 wizard data into our new holy info system
  * list of ubuntu/debian releases and urls
    * include mint/lmde
    * include various sub-releases of debian/ubuntu (mate/kde/lxde etc)
  * same for gparted live
  * arch/vci info (arch types at bootp)
  * available preseed options for debian/ubuntu
  * available preseed options for windows
  * preseed options for vmware esxi
* need to understand preseed and booting for redhat/fedora/centos
* since we have the ca cert, we should be able to install it on the target system during install
  * stage4 probably
  * can we provide it to the linux kernel at boot? what about vmware? windows?
* http/https:
  * default to self-signed when missing certs
  * http redirect to https when certs good
  * way to upload new certs and trigger a reload
* settings
  * manage certs
    * server_cert.pem
    * server_key.pem
    * ca_key.pem
    * (generates full_chain.pem for you)


## Long term things

* Security time
  * invesitate ntp in ipxe, and make it so we can go back to https for all stage server (last holdout)
  * take a look at database connection. can we do ssl with the same cert/key we already have?
  * is there any benefit to doing pub/private keypair auth for broker, database instead of user/password?
  * we need a "re-generate security tokens" script
  * we should actually generate the docker-compose.yml at deploy time, but all contents derived from config.ini
    * config.ini should hold ALL the important info of this manner, including answers in first-time setup wizard
  * add more helper functions with inline python code
    * we can probably write config.ini in a better way (tho heredoc is workin fine)
  * ok how about htis
    * redo deploy as a python script
    * read everything from config.ini
    * if missing, generate passwords.ini
    * generate docker-compose.yml as a temp file, only need it for this deploy
    * if you feel like cycling password, just delte passwords.ini and they will regenerate new next deploy
      * need to store config.ini and passwords.ini somehwere else

* new folder structure
  * /opt/NetbootStudio_bin/ - program_dir
  * /opt/NetbootStudio/
    * local/ - not allowed to be a mounted share or git repo or anything like that. strictly local
      * creds/ - server_cert, server_key, ca_cert, full_chain
      * config/ - config.ini, passwords.ini
      * broker/ - mosquitto.conf and persistence
      * database/ - mariadb persistence
    * share/ - this is the nfs share you provided
      * boot_images/ - this is the only thing we export via our nfs server
      * unattended_configs/
      * ipxe_builds/
      * stage1_files/
      * stage4/
      * uboot_scripts/
      * wimboot_builds/
      * iso/
      * 


## Crazy Ideas

### Appliance Manager
create a very low-requirements appliance manager that can hande deploying NetbootStudio, updating it, and managing certs/

some musings:


* should we move tasks into containers?
  * each task type gets its own container that we build with only exactly the software needed to compile or whatever
  * we need a service running on the host, mqtt client, which is the taskmanger
    * tasks can be run on any host in the swarm!
    * just need to put the resulting files in the shared folder
  * once we have a service on the host which manages tasks, can build containers and manage lifecycles...
    * we could use that to manage Netboot Studio itself!
    * Create another service that acts as the appliance manager webui, and from there you can manage all teh things
  * an appliance manager could ALSO manage the NFS server.
    * in systemd, disable the autostart for NFS server and NFS client
    * our service mounts the nfs mount (no fstab entry anymore)
    * our service manages the NFS server (start it after the client, always)
    * we *could* move SMB to the host for the sake of consistency, but its not necessary
    * same for broker, but again, not necesary
      * but wait, yes it is!
      * broker lives on the host, and appliance manager uses it to communicate with webui and netboot studio
    * should we also move the sql server to the host?
      * leaning toward no
  * appliance manager uses self-signed cert, gives you an easy place to drag-and-drop upload your own certs (and will use them itself)
  * this is where we do updates, and backups
  * 

* Appliance Management Interface
  * yes baby, we're doing it
  * bare minimal webserver/websocket https with self-signed certificate
    * we need to generate our own certificate on first run
  * simple cooperative on asyncio config
  * serve only a single dynamically rendered page, and the contents of one js file
  * it owns host configuration
    * 

* The better bootstrapping process
  * Ignore that noise below, wrong rabbit hole
  * Joe has been talking about the whole portainer deploy thing with a json file at url, git repo, etc
  * lets see if we can use that, and then we just need to make a simple "install docker and portainer" script, let that thing do the rest

* Thinking about the bootstraping process
  * user installs debian 11, go gui, with ssh server
  * user dials in
    * no sudo or git yet. need to su, then install git
  * user clones our repo
  * user runs bootstrap.sh as root (we dont care about sudo anymore)
    * install the appliance manager
      * /opt/local/appliance_manager
        * server.py
        * requirements.txt
        * mkenv.sh
        * venv - virtualenv
        * server.sh - this is what systemd is setup to run at boot
      * runs as root (user sets the password)
      * at first run, will generate self-signed key
  * user goes to appliance manager web page, accepts self-signed cert
    * user upload new certificate and key, and ca cert, hits save. the service restarts itself, using new valid certs
    * upon restart with new certs (check checksums of the user-provided files) re-generate more certificates and chain
      * our own ca, somehow granted authority via the validity of user-provided certs
      * idk this may be pointless
    * ok service is running with valid certs, great. Now we use those certs while deploying netboot studio itself
    * service is now in first-run setup mode, it will go thru all the tasks until complete or error
    * once done, we can deploy
    * deploy is git clone, build image, deploy stack (everything we're doing now)
    * we already have the right separation of concerns
      * first_time_setup.sh is already the run-once script that is everything we need on the base system
      * deploy.sh is already the re-do-everything script that you can run a millino times
    * user can click update, to do a git pull and redeploy
    * 

