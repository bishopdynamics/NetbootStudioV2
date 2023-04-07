# Changelog

* 0.2.110 - April 7 2023 update
  * Implemented wizards and tasks for creating some boot_images, but you will still need to create unatteded configs by hand.
    * Windows 8+ Installer from ISO
    * Debian/Ubuntu Webinstaller
    * VMware ESXi from ISO
    * Debian LiveImage (using squashfs)
  * Improved architecture detection
    * If architecture is detected wrong, you can override ipxe build, and architecture will be updated to match
    * Added experimental support for bios32 and bios64 clients, not really supported but fun to tinker with
    * Some 32bit BIOS virtual machines will be detected as bios64, but most physical 32bit BIOS machines should detect correctly
  * Overhauled the setup script, changed folder ownership. Everything now owned and runs as user "netboot", but you should run `build-image.sh` `./update.sh`, and `./deploy.sh` as root.
  * Changed most `test-*.sh` scripts to run inside container, to more closely match real environment
  * Moved a few unnecessary DataSource instances to static values, improving startup time of API service
  * Some big changes to tasks
    * tasks now create standardized scratch and workspace folders within `/opt/NetbootStudio/temp/`
      * scratch is for temporary files
      * workspace is where the task creates files and folders. Last step of task is to copy workspace to final location.
    * successful tasks cleanup scratch and workspace automatically
      * only stopped/failed tasks leave scratch and workspace around for troubleshooting
    * tasks now run in separate thread
  * Tasks pane in webui now has buttons!
    * view the log file (not live, close and click again to update)
    * stop a running task, which causes it to fail
    * clear a non-running task, which will cleanup any remaining scratch and workspace
  * Added webui text editor for certain categories of files
  * Added VSCode Server instance to docker stack, to make it easier to edit other files, available at `https://netboot-server:8443/`
* 0.2.104 - moved task status to tasks pane, moved client state to own tab, lots of tiny tweaks
* 0.2.103 - fleshed out first_time_setup.sh with wizard 
* 0.2.102 - when boot_image_once, reset when client state next becomes inactive; clear stray client state toast on client delete
* 0.2.101 - this is the MVP, everything after that is gravy. if we have trouble, put joe on this version
* 0.2.0   - prior to changelog, from scratch rewrite of Netboot Studio v1 