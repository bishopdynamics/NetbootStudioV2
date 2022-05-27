# NetbootStudio Boot Process

1. UEFI
   1. On a PC, using the ipv4 network boot option of the UEFI firmware, or an iPXE USB boot drive
   2. On an arm64-based device using u-boot, interrupt the boot and run `run bootcmd_dhcp`
2. DHCP
   1. Client broadcasts a dhcp discover packet
   2. NetbootStudio tftp server sees discover packet
      1. if a client entry does not exist yet, a stub entry is created. This is where arch info originates
      2. the new client entry will have ipxe_build set to the default for this client's arch
   3. DHCP server responds, including the address of the tftp server, and a filename to request (always `ipxe.efi`)
   4. Client requests the given filename from the given tftp server
3. TFTP (stage0)
   1. TFTP server uses the Client's IP Address to query ARP to get MAC address, then uses MAC to get lookup client info from SQL table: netbootstudio/clients
      1. This includes `ipxe_build` which determines which set of prebuilt ipxe binaries to use
   2. The client entry is updated with this IP Address
   3. The TFTP server will respond with `ipxe.efi` from whatever build is specified
      1. if a file other than `ipxe.efi` was requested, it will look for it in tftp_root/
4. iPXE (with embedded script, aka stage1)
   1. request `stage2.ipxe` from the Stage2 service, including a bunch of client information in the request
      1. if this fails, fall back to a troubleshooting menu
   2. Stage2 service uses the Client's MAC Address to lookup a record from SQL table: netbootstudio/clients
      1. this includes `boot_image` and `do_unattended`
   3. if `boot_image` is `standby_loop` or if no entry  was found
      1. an internally rendered script is returned, which places the client in a 10s loop requesting stage2 until a different script is returned
      2. this is helpful if you boot up a device that is not in the list, it will wait until you have configured an entry for it
   4. if `boot_image` is `menu`
      1. an internally rendered script will present an interactive menu, allowing you to choose from available images and unattended files
   5. if `boot_image` is something else
      1. find a boot image matching that name
      2. if its a file type boot image, return it
      3. if it is a folder type boot image, load its `metadata.yaml`, which includes `supports_unattended`, `stage2_filename`, and `stage2_unattended_filename`
      4. if `do_unattended` is true and `supports_unattended` is true:
         1. return `stage2_filename`
      5. if `do_unattended` is false
         1. return `stage2_unattended_filename`
5. Boot Image (aka stage2)
   1. this is where an actual operating system is booted
   2. actual steps vary, but the general steps are
      1. fetch kernel
      2. fetch initrd
      3. boot kernel with initrd and some arguments (and if applicable, arguments for unattended.cfg)
      4. at some point the installer requests unattended.cfg and uses it to automate an installation
6. Unattended (aka stage3)
   1. varies per os and distribution but general steps are
      1. install the os to local storage
      2. configure users and permissions
      3. configure additional packages
   2. Some unattended may also request `stage4.sh`
7. Post-Install (aka Stage4)
   1. very open ended, this is literally any script to setup the system further, to be run within the initial system as root
   2. Netboot Studio's Stage4 system is a set of bash scripts with various helper functions to make post-install easy to configure

