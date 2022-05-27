* thanksgiving, want to demo it for joe and get input
  * want tasks pane and some boot image tasks working
  * need windows image from iso task
* add create boot image wizard
  * debian netinstall
  * ubuntu netinstall
  * debian liveimage
  * ubuntu liveimage?
  * windows from iso
  * vmware from iso
  * gparted from iso?
* add stage 4 support for 
  * windows
  * vmware
* render unattended files on-demand for:
  * debian
  * windows
  * vmware
* add notifications system
  * email, slack, mattermost, matrix, curl, mqtt (on another broker, not ours)
* add support for more os
  * mint?
  * red hat / fedora / centos
  * freebsd
  * pfsense
  * freenas
* add support for more weird stuff 
  * natively booting an iso file
  * extracting an iso, detecing isolinux/syslinux/efi and converting to boot image
    * in theory this should be totally do-able
  * redhat / fedora / centos live image
  * freebsd / openbsd live image
  * clonezilla
  * windows live image
  * veeam bare metal restore 
    * create windows restore image with drivers
  * reverse engineer that site for downloading latest windows image from their servers. we want that
* Add support for common automation stuff
  * munki
  * jamf
  * ansible
  * salt
  * puppet
* integrate well with WDS?