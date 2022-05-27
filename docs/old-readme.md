# Netboot Studio

## Requirements
* server running Debian 11 amd64
* docker and mosquitto installed
  * mosquitto is only needed to provide the command: mosquitto_passwd
* if AppArmor is enabled on the host (probably yes), install package: apparmor-utils

Netboot Studio is broken into 8 services, all designed to operate as a docker stack on a single host (your netboot server)

* API
* Stage
* TFTP
* WebUI
* FileWatcher
* Database (mariadb)
* Broker (mosquitto)
* NFS Server (running on docker host, not container)

Additionally, Netboot Studio v2 relies on a DHCP server, which you must provide.
  * respond to clients with tfp server address, and filename (always `/ipxe.efi`)

## A Note About Security
Netboot Studio is expected to be hosted on-premises, on an internal network secured to your own liking.
As such, the security design of Netboot Studio is practically nonexistent. 

## Setup

1. On a machine running Debian 11 (bullseye) x86_64, 
   1. install docker and docker-compose, as well as mosquitto. 
   2. install mosquitto and mosquitto-clients (we need the tools), but disable the service: `systemctl disable mosquitto`
2. clone this repo (I like to do it in the service user's home folder).
3. create `/opt/NetbootStudio/` (and chown it as your service user)
4. copy your certificates into `/opt/NetbootStudio/certs/`
   1. See [Certificates](#certificates)
5. from within the repo folder, run `./run.sh`
   1. this will:
      1. stop and remove any already running containers
      2. generate latest docker image from source
      3. if `config.ini` does not exist, copy `config-default.ini` to `/opt/NetbootStudio/config.ini`
      4. create subfolders in `/opt/NetbootStudio/`
      5. create `/opt/local/database` for database persistence
      6. create `/opt/local/broker` for broker persistence
      7. start all services for NetbootStudio

You can now access Netboot Studio WebUI at: `https://<netboot-server>:8080/`

### Note about file shares

You can make `/opt/NetbootStudio` a mounted NFS share, that's how we do it. 
You must not make `/opt/local` or anything under it any kind of mounted share; the purpose of `/opt/local` is to keep separate the things which would become corrupt if on a share (like the database)

### DHCP Server

You must provide your own DHCP server, and have it configured to provide the filename `/ipxe.efi` for all architectures (including default bios) 
NetbootStudio does not support traditional pcbios pxe booting, only UEFI, but it will try anyway!
Our TFTP Server will take care of providing the correct build of ipxe, per architecture, and in the webui you can build your own binary and select it in client config

### Certificates

SSL for everything, need a server certificate and key, plus we need a "full chain" certificate

In your certificate authority (I use pfSense for this), first create a new certificate authority (or use an existing one). 
Next create a server certificate issued by that authority, then download both the certificate and the key. 
Name them `server_cert.pem` and `server_key.pem`. 

Also download the cert for the ca itself, you will need this to create the full chain certificate. 
Do this by appending ca_cert to server_cert: `cat server_cert.pem ca_cert.pem > full_chain.pem`

so now you have the following files:
```bash
ca_cert.pem
full_chain.pem
server_cert.pem
server_key.pem
```

put all four of these files into `/opt/NetbootStudio/certs/` on the host

When testing, you will need to import the CA cert and the server cert into your keyring and trust them. 
When testing with Firefox, make sure to import the CA cert in Firefox settings, it will not care about system keychain

## Creating an iPXE USB boot drive

Some systems may have missing or badly implemented option roms for netbooting. Never fear! there is an
excellent solution. Download an ISO of your preferred ipxe build, and you can write it directly to a USB mass storage device.
ISO files are provided with `stage1.ipxe` embeded, and without any embedded ipxe script.

You can then boot from the USB device, and it will act as shim to get you to the "DHCP" step of the boot process. You
can remove the usb stick as soon as you see the message `iPXE Initializing...`, and it is highly recommended that you do in order
to avoid confusing HDD selection in any automated OS installtions. 

In testing, we found most option rom netbooting implementations left something to be desired. We had the most consistent
results by always booting from a USB drive.



## Boot Process

See [BootProcess.md](docs/BootProcess.md)

## API Documentation

See [API.md](docs/API.md)

## Special tftp file: boot.scr.uimg

See [UBoot.md](docs/UBoot.md)

## TODO
NetbootStudio is still in development, see the current TODO list: [TODO.md](docs/TODO.md)
