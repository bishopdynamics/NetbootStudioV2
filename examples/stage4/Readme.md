# Stage4 Post-Install System

The stage4 post-install system is designed to be executed by the late_command portion of a debian preseed file. 

in your preseed file, add this to the end:
```bash
d-i preseed/late_command string \
mkdir /target/post_install; \
echo ' \
exec   > >(tee -ia /post_install/output.log); \
exec  2> >(tee -ia /post_install/output.log >& 2); \
exec 19> /post_install/output.log; \
export BASH_XTRACEFD="19"; \
set -x; \
wget -O /post_install/stage4.sh "http://192.168.1.188:6161/stage4.sh?file=stage4-entry.sh"; \
chmod +x /post_install/stage4.sh; \
/post_install/stage4.sh "x86-docker.sh"; \
' > /target/post_install/script_wrapper.sh; \
in-target bash /post_install/script_wrapper.sh; \
echo "done running late_command"
```

in the line `/post_install/stage4.sh "x86-docker.sh"; \` change `x86-docker.sh` the stage4 script you want to run. 

stage4 scripts can call other stage4 scripts by name using `source_stage4_script`

they can also install stage4 packages using `install_package <packagename>`


## Stage4 Packages

stage4 has a very basic packaging system. a package is a `.tar.gz` file, which must contain `package-meta/install.sh`. When the package is installed, `install.sh` will be passed a single argument, the temp folder where the package was extracted. `install.sh` is always run as root

packages can be installed from a stage4 script by `install_package "monitoring-agent"` where `monitoring-agent` is the name of the package to be installed


## Functions

check out `stage4-common.sh` to see what functions are provided to scripts
