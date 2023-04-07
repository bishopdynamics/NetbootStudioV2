# Special file: boot.scr.uimg

For systems which use u-boot, you may see an error in the NetbootStudio logs: `ERROR - File "/opt/NetbootStudio/tftp_root/boot.scr.uimg" does not exist!`, this is normal. 

u-boot will al


Here is an example of `boot.cmd`, please note that it is NOT `bash` syntax exactly, only similar. 
If you are using a modern IDE you can set your syntax to `bash` or `Shell Script` for servicable highlighting:
```bash
echo ""
echo "#######################################################################"
echo "               Start of NetbootStudio boot.scr.uimg"
echo ""

# - vendor=rockchip
# - arch=arm
# - board=evb_rk3399
# - board_name=evb_rk3399
# - cpu=armv8
# - soc=rk3399

# we could look for image specific to vendor and board, next try generic for cpu, then just try arm64 generic
#       for now, the standard arm64 ipxe binary works fine for everything we are doing
# setenv board_specific_bootfile /ipxe/ipxe-${cpu}-${vendor}-${board}.efi
# setenv cpu_type_bootfile /ipxe/ipxe-${cpu}-efi.efi
#setenv generic_bootfile /ipxe.bin
#setenv bootfile ${generic_bootfile}

# dump a bunch of vars for fun
echo "arch: ${arch}"
echo "board: ${board}"
echo "cpu: ${cpu}"
echo "soc: ${soc}"
echo "fdtfile: ${fdtfile}"
echo "ethaddr: ${ethaddr}"
echo "bootfile: ${bootfile}"

setenv bootp_vci PXEClient:Arch:00011:UNDI:003000;
setenv bootp_arch 0xb;

echo "bootp_vci: ${bootp_vci}"
echo "bootp_arch: ${bootp_arch}"
echo ""

## fetching bootfile first will cause a new client entry (if none exists) to be made, with the correct arch
##   this can be abused to send more information
#tftpboot ${kernel_addr_r} ${bootfile}
#
#if dhcp ${kernel_addr_r}; then
#    tftpboot ${kernel_addr_r} ${bootfile}
#    tftpboot ${fdt_addr_r} dtb/${fdtfile};
#    if fdt addr ${fdt_addr_r}; then
#        bootefi ${kernel_addr_r} ${fdt_addr_r};
#    else
#        bootefi ${kernel_addr_r} ${fdtcontroladdr};
#    fi;
#fi;

# a lot more could be done here, but all that is needed is to set the bootfile

echo ""
echo "               End of NetbootStudio boot.scr.uimg"
echo "#######################################################################"

```

And to compile that into `boot.scr.uimg` here is a real bash script (you need `mkimage`, from the pkg `u-boot-tools`):
```bash
#!/usr/bin/env bash

# generate boot.scr.uimg from boot.cmd
#   presumes that boot.cmd is in the current folder, 
#   and will overwrite any existing boot.scr.uimg in the current folder and the TARGET_PATH

# for Netboot Studio
TARGET_PATH="/opt/NetbootStudio/tftp_root"

echo ""
echo " turning boot.cmd into boot.scr.uimg for clients using u-boot"
mkimage -A arm -O linux -T script -C none -d boot.cmd boot.scr.uimg || {
  echo "failed to build boot.scr.uimg"
  exit 1
}


echo "deploying it to ${TARGET_PATH}/boot.scr.uimg"

# remove the existing one first, if one exists
if [ -f "${TARGET_PATH}/boot.scr.uimg" ]; then
	rm "${TARGET_PATH}/boot.scr.uimg" || {
	  # if this fails, we probably cant write there anyway
	  echo "failed to remove existing boot.scr.uimg"
	  exit 1
	}
fi

# copy the one we built into place
cp boot.scr.uimg "${TARGET_PATH}/boot.scr.uimg" || {
  echo "failed to deploy boot.scr.uimg to $TARGET_PATH"
  exit 1
}

# we did it!
echo "success"

```