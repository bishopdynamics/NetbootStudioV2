# Netboot Studio V2

Netboot Studio is a network booting and deployment automation platform. This is the second major version.

## License

This project makes use of the following packages (from PIP):
* websockets (MIT)
* yattag (GPL)
* aiohttp (Apache v2)
* aiohttp_tus (BSD)
* aiohttp-middlewares (BSD)
* cryptography (BSD)
* attr (MIT)
* pyyaml (MIT)
* py3tftp (MIT)
* mysql-connector-python (GPLv2)
* scapy (GPLv2)
* paho-mqtt (Eclipse Public License v2.0 / Eclipse Distribution License v1.0)
* Sphinx (BSD)
* rinohtype (AGPLv3)
* watchdog (Apache v2)

Everything else is GPLv3 license, [license.txt](license.txt)

## Disclaimer

This project attempts to use SSL and HTTPS to provide a vague sense of security, but it is not ideally implemented. 
Credentials are hardcoded (`admin:admin`) in [config-default.ini](config-default.ini).
For a home lab setup, this is fine, but if you want to use this for a project where security actually matters then you should take a real critical look at my implementation of all this, and probably overhaul it.

This project is NOT actively maintained. Please feel free to fork it and run with it! Drop me a line if you are proud of your changes, I will be genuinely interested to see what you've done with it!

If I am to be perfectly honest, the change to docker stack architecture added unnecessary complexity, 
and if I were to reboot this project again I would not repeat that decision. 
Of course, if one were to combine all the services back into a single Python module, there would be some significant performance issues related to GIL, which is the primary reason I split it up in the first place.
I'm sure all the threading could be done in a far more efficient and "correct" manner.

Finally, I did a little cleanup to publish this in May 2022, but I am not 100% certain of the current state of things 
because I stopped actually using or working on it in late 2021. 
I remember having trouble getting it working correctly on an arm64 host, and I don't think I ever resolved that issue.

Happy Hacking!

## DHCP Server

You must provide your own DHCP server, and have it configured to provide `tftp-server` and `next-server` as the IP of your netboot server, and the filename `/ipxe.efi` for all architectures (including default bios) 
Netboot Studio does not support traditional pcbios pxe booting, only UEFI, but it will try anyway!
Our TFTP Server will take care of providing the correct build of ipxe, per architecture, and in the webui you can build your own binary and select it in client config

## Note About File Shares

Netboot Studio first-time setup will ask you for an NFS share to mount at `/opt/NetbootStudio`; this is the preferred way to store files. 
You must not make `/opt/local` or anything under it any kind of mounted share; the purpose of `/opt/local` is to keep separate the things which would become corrupt if on a share (like the database)


## Setup

Netboot Studio operates as a docker stack, but there are still special requirements that make it necessary to dedicate a specific host.

Right now we support a very specific setup:

* Debian 11 (Bullseye) amd64. Base install without desktop or gnome, with ssh server
  * Debian does not have sudo by default, so log in as root to install git
    * `apt-get update`
    * `apt-get install -y git`
  * logout, and login as your normal, non-root user
  * clone the repo in the home folder:
    * `git clone http://bishopdynamics.com:8094/james/NetbootStudio-V2.git`
  * log back in as root, then run first-time setup
    * `cd NetbootStudio-V2` (the repo, in non-root user's home folder)
    * `./first_time_setup.sh`
  * the wizard will prompt you for input, then ask you to confirm before it configures everything for Netboot Studio
    * this script will generate unique passwords for the database, broker, samba server, and nfs server
    * it will also generate `docker-compose.yml` which will be used to stand up everything
  * when first-time setup is complete, you will now have sudo for the non-root user, so you should log out of root and login as the non-root user for the rest of setup
  * when first-time setup is complete, it will warn you about credentials
    * You need to provide server certificate and key, and ca certificate: `server_cert.pem`, `server_key.key`, `ca_cert.pem`
    * You also need to create a `full_chain.pem` by appending ca_cert to server_cert: `cat server_cert.pem ca_cert.pem > full_chain.pem`
    * so now you have the following files:
      * `ca_cert.pem`
      * `full_chain.pem`
      * `server_cert.pem`
      * `server_key.pem`
    * Put these files in `/opt/NetbootStudio/certs/`, make sure they are owned by your non-root user
    * start Netboot Studio by running `./run.sh` (again, as non-root user)
      * this will always rebuild the docker image from spec, which should be pretty fast after the first time
    * navigate to `https://netboot-server/` where `netboot-server` is the hostname of your server
    * log in as admin, with the password you gave during first-time-setup
    * Netboot Studio does not provide any iPXE builds out-of-the-box, so your first task is to build one for each arch (amd64, arm64)
      * go to iPXE Builds tab, click "New"

* since Netboot Studio is made up of docker services, you do NOT need to start it up after every reboot, it will start on its own.
* to update, do a git pull and run `./run.sh` to rebuild and deploy the updated version

* in development we use a virtual machine with 4 cpus/cores and 2GB ram. 
* more cpus will improve performance of tasks like ipxe builds and debian liveimage builds, but wont have a significant impact on day-to-day performance.

* Setup steps average times:
  * manually installing Debian using the netinstall iso (and transparent http caching): 7 minutes
  * `./first_time_setup.sh`: 5 minutes
  * `./deploy.sh` (first time): 6 minutes
  * `./deploy.sh` (subsequent times): 10-30 seconds

## Supported Client Architectures

* amd64 (aka x86_64)
* arm64 (aka aarch64)

## Supported Client Operating Systems

* Windows 7, 8, 8.1, 10 and 11
* Windows Server 2012, 2016, 2019, 20H2?
* Debian 9,10,11,12
* Ubuntu
* Redhat
* Fedora
* Centos
* VMware ESXi 6+ (amd64 and arm64)

## A Note About Special Characters in File and Folder Names
It is important to be careful about what characters you use in the names, because the name will be used in paths and urls. 
This applies to all folders and files used by this application.

Only use  `a-Z`, `0-9`, and instead of spaces use hypen (`-`) and underscore (`_`).
For boot images, when the name is rendered in the WebUI, the hypens and underscores will be replaced with spaces to make it look nicer.

In most cases, Netboot Studio will be generating folders for you, so this only applies if you are creating custom boot images.

## Unattended Installs

Netboot Studio can perform unattended installation of an operating system if you provide it the appropriate config file.
Creating that file is an exercise left to the user, but we have provided some examples. 
Put your unattended config files in `/opt/NetbootStudio/unattended_configs/`, and you can name them whatever you'd like but there can be no subfolders

## Stage4 Deployment Configuration System

There are many deployment configuration systems out there, but we felt like rolling our own much simpler one for fun.
The examples that Netboot Studio provides with a fresh installation are intended as a basis for your own tweaking, 
it will not be updated with Netboot Studio.

#### Debian preseed file
The stage4 post-install system is designed to be executed by the late_command portion of a debian preseed file.
in your debian/ubuntu preseed file, add this to the end:
```bash
d-i preseed/late_command string \
mkdir /target/post_install; \
echo ' \
exec   > >(tee -ia /post_install/output.log); \
exec  2> >(tee -ia /post_install/output.log >& 2); \
exec 19> /post_install/output.log; \
export BASH_XTRACEFD="19"; \
set -x; \
wget -O /post_install/stage4.sh "http://james-netboot:8082/stage4.sh"; \
chmod +x /post_install/stage4.sh; \
/post_install/stage4.sh; \
' > /target/post_install/script_wrapper.sh; \
in-target bash /post_install/script_wrapper.sh; \
echo "done running late_command"
```

Remember to change `james-netboot` to the hostname of your netboot server.

stage4 scripts can call other stage4 scripts by name using `source_stage4_script`

they can also install stage4 packages using `install_package <packagename>`


#### Stage4 Packages

stage4 has a very basic packaging system. a package is a `.tar.gz` file, which must contain `package-meta/install.sh`. When the package is installed, `install.sh` will be passed a single argument, the temp folder where the package was extracted. `install.sh` is always run as root

packages can be installed from a stage4 script by `install_package "monitoring-agent"` where `monitoring-agent` is the name of the package to be installed

#### Functions

Stage4 provides several helper functions for scripts to use. (TODO document this)


## Creating an iPXE USB boot drive

Some systems may have missing or badly implemented option roms for netbooting. Never fear, there is an
excellent solution! Download an ISO of your preferred ipxe build, and you can write it directly to a USB mass storage device.
ISO files are provided with `stage1.ipxe` embeded, and also without any embedded stage1 script.

You can then boot from the USB device, and it will act as shim to get you to the "DHCP" step of the boot process. You
can remove the usb stick as soon as you see the message `iPXE Initializing...`, and it is highly recommended that you do in order
to avoid confusing HDD selection in any automated OS installtions. 

In testing, we found most option rom netbooting implementations left something to be desired. We had the most consistent
results by always booting from a USB drive without embedded stage1 script.

## Boot Process

See [BootProcess.md](docs/BootProcess.md)

## API Documentation

See [API.md](docs/API.md)



## Customization

Netboot Studio deliberately exposes "too much" of the netbooting process for customization; in most cases, 
there will be no need to customize things. Obviously customizations will affect Netboot Studio, 
we recommend only customizing things to direct specific clients to a different deployment automation platform. 

### iPXE Stage1 Script

Netboot Studio depends on an embedded script within the iPXE binary, which chains the `/stage2.ipxe` endpoint and provides 
lots of information about the client. You can provide your own script in `/opt/NetbootStudio/ipxe_stage1/`, named `something.ipxe`, choose it when building an ipxe binary, 
and select that build in client config.

### Customize u-boot

When a u-boot client network boots, the first thing it tries to fetch is /boot.scr.uimg from the tftp server. 
This is a u-boot script packaged inside a special image file. 
While developing Netboot Studio, we built functionality to build this image file on-demand, with script content on a per-client basis. 
Netboot Studio no longer needs this functionality, so by default it returns an empty script. 
You can provide your own script in `/opt/NetbootStudio/uboot_scripts/`, named `something.scr` and select it in a client's config. 

### Custom boot images

There are two types of boot images: folder and file. As with all other files, remember to be strict with what characters you use.

Any file ending in `.ipxe` within `boot_images/` (not recursive) will be treated as a boot image, with the filename as the name of the image.
These are internally called `a-la-carte` boot images, and are meant for custom things beyond Netboot Studio. 

If you want to use unattended config files, you need to create a folder boot image. 
A folder boot image uses the name of the folder as the image name, and requires two additional files:

```bash
stage2.ipxe
metadata.yaml
```

You must provide `metadata.yaml` like this:
```yaml
created: "2021-10-26_15:38:14"
image_type: "debian-liveimage"
description: "auto-built using debian-liveimage"
release: "bullseye"
stage2_filename: "stage2.ipxe"
supports_unattended: "false"
stage2_unattended_filename: "none"
arch: "arm64"
```

all values are strings in quotes, the value of `created` must be in this format `date '+%Y-%m-%d_%H:%M:%S'`


The file `stage2.ipxe` can actually be named anything as long as it matches `stage2_filename` in metadata, and can be any ipxe script, there are some special variables that you can leverage. 
Here's how they get defined:
```bash
############## this is the preamble generated by Netboot Studio #############
set netboot-studio-server ${next-server}
set stage-server http://${netboot-studio-server}:8082
set boot-images ${stage-server}/boot_images
set boot-images-nfs-noproto ${netboot-studio-server}/opt/NetbootStudio/boot_images
set boot-images-nfs nfs://${boot-images-nfs-noproto}
set stage-2-url ${stage-server}/stage2.ipxe?mac=${mac}&buildarch=${buildarch}&platform=${platform}&manufacturer=${manufacturer}&chip=${chip}&ip=${ip}&uuid=${uuid}&serial=${serial}&product=${product}&version=${version}&unixtime=${unixtime}&asset=${asset}
set unattended-url-linux ${stage-server}/unattended.cfg
set unattended-url-windows ${stage-server}/unattend.xml
set wimboot-path ${boot-images}/wimboot
############## end preamble #############
```



## TODO
NetbootStudio is incomplete, see the current TODO list: [TODO.md](docs/TODO.md)

