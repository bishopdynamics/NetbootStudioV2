// these functions are specific to Wizards

// New iPXE Build
function show_modal_new_build_ipxe() {
    const wizard_config = {
        title: 'New iPXE Build',
        subtitle: 'Compile an iPXE binary with specific settings',
        height: 480,
        pages: 1,
        inputs: [
            {
                name: 'name',
                label: 'Name',
                tooltip: 'Give this build a name',
                type: 'text',
            },
            {
                name: 'comment',
                label: 'Comment',
                tooltip: 'Provide additional details about this build',
                type: 'text',
            },
            {
                name: 'commit_id',
                label: 'iPXE Commit ID',
                tooltip: 'Select the git Commit ID to build iPXE from',
                type: 'select_static',
                options: [
                    {
                        commit_id: '1d1cf74',
                        name: 'Latest Commit (Mar 30, 2023)',
                    },
                    {
                        commit_id: 'bf25e23',
                        name: 'Latest Commit (Mar 14, 2023)',
                    },
                    {
                        commit_id: 'f24a279',
                        name: 'Previous Latest Commit (Oct 28, 2021)',
                    },
                    {
                        commit_id: 'e6f9054',
                        name: 'Last Stable (Oct 20, 2020)',
                    },
                    {
                        commit_id: '988d2c1',
                        name: 'Latest Tag 1.21.1 (Dec 31, 2020)',
                    },
                    {
                        commit_id: '8f1514a',
                        name: 'Next Latest Tag 1.20.1 (Jan 2, 2020)',
                    },
                    {
                        commit_id: '13a6d17',
                        name: 'Previous one we marked stable in old netbootstudio (Nov 29, 2020)',
                    },
                    {
                        commit_id: '53e9fb5',
                        name: 'Very old Tag v 1.0.0 (Feb 2, 2010)',
                    },
                ],
                keys_display: ['commit_id', 'name'],
                key_value: 'commit_id',
            },
            {
                name: 'arch',
                label: 'Architecture',
                tooltip: 'Select the architecture to build',
                type: 'select',
                options: 'architectures',
                keys_display: ['name', 'description'],
                key_value: 'name',
            },
            {
                name: 'stage1_file',
                label: 'Embeded Stage1 ipxe script',
                tooltip: 'Select the stage1 ipxe script to embed in the binary',
                type: 'select',
                options: 'stage1_files',
                keys_display: ['filename', 'modified'],
                key_value: 'filename',
            },
        ],
        metadata: {
            comment: 'these will be stored in global MODAL_METADATA so you can access them from within onclick functions later',
        },
        data: {
            commit_id: '',
            arch: '',
            stage1_file: 'default',
            name: '',
            comment: '',
        },
        button_onclicks: {
            save: function(data) {
                create_task('build_ipxe', data);
            },
        },
    };
    console.log(wizard_config);
    showModal_Wizard(wizard_config);
}

// config for all Boot Image wizards
const wizards_config_boot_image = {
    'windows-installer-from-iso': {
        title: 'Windows Installer from ISO',
        subtitle: 'Create a boot image from a Windows 7/8/10/11 ISO file',
        height: 480,
        pages: 1,
        inputs: [
            {
                name: 'name',
                label: 'Name',
                tooltip: 'Give this boot image a name',
                type: 'text',
            },
            {
                name: 'comment',
                label: 'Comment',
                tooltip: 'Provide additional details about this boot image',
                type: 'text',
            },
            {
                name: 'arch',
                label: 'Architecture',
                tooltip: 'Select the architecture',
                type: 'select',
                options: 'architectures',
                keys_display: ['name', 'description'],
                key_value: 'name',
            },
            {
                name: 'iso_file',
                label: 'Source ISO File',
                tooltip: 'Select the ISO file to use as source',
                type: 'select',
                options: 'iso',
                keys_display: ['filename', 'modified'],
                key_value: 'filename',
            },
            {
                name: 'create_unattended',
                label: 'Create unattended files?',
                tooltip: 'Create files to support unattended installation?',
                type: 'checkbox',
            },
        ],
        metadata: {
            comment: 'these will be stored in global MODAL_METADATA so you can access them from within onclick functions later',
        },
        data: {
            name: '',
            comment: '',
            arch: '',
            iso_file: '',
            create_unattended: true,
        },
        button_onclicks: {
            save: function(data) {
                console.log('Going to build windows image using: ' + data['iso_file']);
                create_task('image_windows_installer_from_iso', data);
            },
        },
    },
    'esxi-installer-from-iso': {
        title: 'VMware ESXi Installer from ISO',
        subtitle: 'Create a boot image from a VMware ESXi 5/6/7/8 Installer ISO',
        height: 480,
        pages: 1,
        inputs: [
            {
                name: 'name',
                label: 'Name',
                tooltip: 'Give this boot image a name',
                type: 'text',
            },
            {
                name: 'comment',
                label: 'Comment',
                tooltip: 'Provide additional details about this boot image',
                type: 'text',
            },
            {
                name: 'arch',
                label: 'Architecture',
                tooltip: 'Select the architecture',
                type: 'select',
                options: 'architectures',
                keys_display: ['name', 'description'],
                key_value: 'name',
            },
            {
                name: 'iso_file',
                label: 'Source ISO File',
                tooltip: 'Select the ISO file to use as source',
                type: 'select',
                options: 'iso',
                keys_display: ['filename', 'modified'],
                key_value: 'filename',
            },
            {
                name: 'create_unattended',
                label: 'Create unattended files?',
                tooltip: 'Create files to support unattended installation?',
                type: 'checkbox',
            },
        ],
        metadata: {
            comment: 'these will be stored in global MODAL_METADATA so you can access them from within onclick functions later',
        },
        data: {
            name: '',
            comment: '',
            arch: '',
            iso_file: '',
            create_unattended: true,
        },
        button_onclicks: {
            save: function(data) {
                console.log('Going to build ESXi image using: ' + data['iso_file']);
                create_task('image_esx_installer_from_iso', data);
            },
        },
    },
    'debian-webinstaller': {
        title: 'Debian Webinstaller',
        subtitle: 'Create a minimal, arch-independent, boot image to fetch and install Debian from the web',
        height: 580,
        pages: 1,
        inputs: [
            {
                name: 'name',
                label: 'Name',
                tooltip: 'Give this boot image a name',
                type: 'text',
            },
            {
                name: 'comment',
                label: 'Comment',
                tooltip: 'Provide additional details about this boot image',
                type: 'text',
            },
            {
                name: 'debian_release',
                label: 'Debian Release',
                tooltip: 'Select a release of Debian',
                type: 'select_static',
                options: [
                    {
                        name: 'Debian 12 (Bookworm)',
                        value: 'bookworm',
                    },
                    {
                        name: 'Debian 11 (Bullseye)',
                        value: 'bullseye',
                    },
                    {
                        name: 'Debian 10 (Buster)',
                        value: 'buster',
                    },
                    {
                        name: 'Debian 9 (Stretch)',
                        value: 'stretch',
                    },
                    {
                        name: 'Debian 8 (Jessie)',
                        value: 'jessie',
                    },
                    {
                        name: 'Debian Stable',
                        value: 'stable',
                    },
                    {
                        name: 'Debian Testing',
                        value: 'testing',
                    },
                    {
                        name: 'Debian Sid',
                        value: 'sid',
                    },
                ],
                keys_display: ['name'],
                key_value: 'value',
            },
            {
                name: 'kernel_args',
                label: 'Kernel arguments',
                tooltip: 'Provide arguments to pass to the kernel',
                type: 'text',
            },
            {
                name: 'create_unattended',
                label: 'Create unattended files?',
                tooltip: 'Create files to support unattended installation?',
                type: 'checkbox',
            },
        ],
        metadata: {
            comment: 'these will be stored in global MODAL_METADATA so you can access them from within onclick functions later',
        },
        data: {
            name: '',
            comment: '',
            debian_release: '',
            kernel_args: 'ipv6.disable=1 IPV6_DISABLE=1 net.ifnames=0 biosdevname=0',
            create_unattended: true,
        },
        button_onclicks: {
            save: function(data) {
                console.log('Going to build Debian image using: ' + data['debian_release']);
                create_task('image_debian_webinstaller', data);
            },
        },
    },
    'ubuntu-webinstaller': {
        title: 'Ubuntu Webinstaller',
        subtitle: 'Create a minimal, arch-independent, boot image to fetch and install Ubuntu from the web',
        height: 580,
        pages: 1,
        inputs: [
            {
                name: 'name',
                label: 'Name',
                tooltip: 'Give this boot image a name',
                type: 'text',
            },
            {
                name: 'comment',
                label: 'Comment',
                tooltip: 'Provide additional details about this boot image',
                type: 'text',
            },
            {
                name: 'ubuntu_release',
                label: 'Ubuntu Release',
                tooltip: 'Select a release of Ubuntu',
                type: 'select_static',
                options: [
                    {
                        name: 'Ubuntu 23.04 (Lunar Lobster)',
                        value: 'lunar',
                    },
                    {
                        name: 'Ubuntu 22.10 (Kinetic Kudu)',
                        value: 'kinetic',
                    },
                    {
                        name: 'Ubuntu 22.04 (Jammy Jellyfish)',
                        value: 'jammy',
                    },
                    {
                        name: 'Ubuntu 21.10 (Impish Indri)',
                        value: 'impish',
                    },
                    {
                        name: 'Ubuntu 21.04 (Hirsute Hippo)',
                        value: 'hirsute',
                    },
                    {
                        name: 'Ubuntu 20.10 (Groovy Gorilla)',
                        value: 'groovy',
                    },
                    {
                        name: 'Ubuntu 20.04 (Focal Fossa)',
                        value: 'focal',
                    },
                    {
                        name: 'Ubuntu 19.10 (Eoam Ermine)',
                        value: 'eoam',
                    },
                    {
                        name: 'Ubuntu 19.04 (Disco Dingo)',
                        value: 'groovy',
                    },
                    {
                        name: 'Ubuntu 18.10 (Cosmic Cuttlefish)',
                        value: 'cosmic',
                    },
                    {
                        name: 'Ubuntu 18.04 (Bionic Beaver)',
                        value: 'bionic',
                    },
                    {
                        name: 'Ubuntu 17.10 (Artful Aardvark)',
                        value: 'artful',
                    },
                    {
                        name: 'Ubuntu 17.04 (Zesty Zapus)',
                        value: 'zesty',
                    },
                    {
                        name: 'Ubuntu 16.10 (Yakkety Yak)',
                        value: 'yakkety',
                    },
                    {
                        name: 'Ubuntu 16.04 (Xenial Xerus)',
                        value: 'xenial',
                    },
                ],
                keys_display: ['name'],
                key_value: 'value',
            },
            {
                name: 'kernel_args',
                label: 'Kernel arguments',
                tooltip: 'Provide arguments to pass to the kernel',
                type: 'text',
            },
            {
                name: 'create_unattended',
                label: 'Create unattended files?',
                tooltip: 'Create files to support unattended installation?',
                type: 'checkbox',
            },
        ],
        metadata: {
            comment: 'these will be stored in global MODAL_METADATA so you can access them from within onclick functions later',
        },
        data: {
            name: '',
            comment: '',
            ubuntu_release: '',
            kernel_args: '',
            create_unattended: true,
        },
        button_onclicks: {
            save: function(data) {
                console.log('Going to build Ubuntu image using: ' + data['ubuntu_release']);
                create_task('image_ubuntu_webinstaller', data);
            },
        },
    },
    'debian-liveimage': {
        title: 'Debian Live Image',
        subtitle: 'Create a live Debian environment that can be booted without installation',
        height: 860,
        pages: 1,
        inputs: [
            {
                name: 'name',
                label: 'Name',
                tooltip: 'Give this boot image a name',
                type: 'text',
            },
            {
                name: 'comment',
                label: 'Comment',
                tooltip: 'Provide additional details about this boot image',
                type: 'text',
            },
            {
                name: 'mirror',
                label: 'Debian mirror',
                tooltip: 'Which Debian mirror to fetch packages from, without trailing slash. ex: http://deb.debian.org/debian',
                type: 'text',
            },
            {
                name: 'debian_release',
                label: 'Debian Release',
                tooltip: 'Select a release of Debian',
                type: 'select_static',
                options: [
                    {
                        name: 'Debian 12 (Bookworm)',
                        value: 'bookworm',
                    },
                    {
                        name: 'Debian 11 (Bullseye)',
                        value: 'bullseye',
                    },
                    {
                        name: 'Debian 10 (Buster)',
                        value: 'buster',
                    },
                    {
                        name: 'Debian 9 (Stretch)',
                        value: 'stretch',
                    },
                    {
                        name: 'Debian 8 (Jessie)',
                        value: 'jessie',
                    },
                    {
                        name: 'Debian Stable',
                        value: 'stable',
                    },
                    {
                        name: 'Debian Testing',
                        value: 'testing',
                    },
                    {
                        name: 'Debian Sid',
                        value: 'sid',
                    },
                ],
                keys_display: ['name'],
                key_value: 'value',
            },
            {
                name: 'debian_installer',
                label: 'Debian Installer Type',
                tooltip: 'What type of Debian Installer should be included',
                type: 'select_static',
                options: [
                    {
                        name: 'False',
                        value: 'false',
                    },
                    {
                        name: 'True',
                        value: 'true',
                    },
                    {
                        name: 'CDROM',
                        value: 'cdrom',
                    },
                    {
                        name: 'NetInstall',
                        value: 'netinst',
                    },
                    {
                        name: 'NetBoot',
                        value: 'netboot',
                    },
                    {
                        name: 'BusinessCard',
                        value: 'businesscard',
                    },
                    {
                        name: 'Live',
                        value: 'live',
                    },
                ],
                keys_display: ['name'],
                key_value: 'value',
            },
            {
                name: 'arch',
                label: 'Architecture',
                tooltip: 'Select the architecture',
                type: 'select',
                options: 'architectures',
                keys_display: ['name', 'description'],
                key_value: 'name',
            },
            {
                name: 'kernel_args',
                label: 'Kernel arguments',
                tooltip: 'Provide arguments to pass to the kernel',
                type: 'text',
            },
            {
                name: 'include_xfce',
                label: 'Include XFCE Desktop',
                tooltip: 'Include minimal XFCE desktop GUI?',
                type: 'checkbox',
            },
            {
                name: 'packages',
                label: 'Packages to install',
                tooltip: 'Provide additional packages to install',
                type: 'text',
            },
            {
                name: 'archive_areas',
                label: 'Repo Archive Areas',
                tooltip: 'add "contrib" and "non-free" here if desired',
                type: 'text',
            },
        ],
        metadata: {
            comment: 'these will be stored in global MODAL_METADATA so you can access them from within onclick functions later',
        },
        data: {
            name: '',
            comment: '',
            arch: '',
            debian_release: '',
            debian_installer: 'false', // not a bool
            mirror: 'http://deb.debian.org/debian', // no trailing slash
            kernel_args: 'ipv6.disable=1 IPV6_DISABLE=1 net.ifnames=0 biosdevname=0',
            packages: '',
            include_xfce: false,
            archive_areas: 'main',
        },
        button_onclicks: {
            save: function(data) {
                console.log('Going to build Debian Live Image using: ' + data['debian_release'] + ' ' + data['arch']);
                create_task('image_debian_liveimage', data);
            },
        },
    },
    'generic-from-iso': {
        title: 'Generic ISO Parser',
        subtitle: 'Try to parse the contents of an ISO and create a boot image',
        height: 480,
        pages: 1,
        inputs: [
            {
                name: 'name',
                label: 'Name',
                tooltip: 'Give this boot image a name',
                type: 'text',
            },
            {
                name: 'comment',
                label: 'Comment',
                tooltip: 'Provide additional details about this boot image',
                type: 'text',
            },
            {
                name: 'arch',
                label: 'Architecture',
                tooltip: 'Select the architecture',
                type: 'select',
                options: 'architectures',
                keys_display: ['name', 'description'],
                key_value: 'name',
            },
            {
                name: 'extra_kernel_args',
                label: 'Extra kernel arguments',
                tooltip: 'Provide extra arguments to pass to the kernel',
                type: 'text',
            },
            {
                name: 'iso_file',
                label: 'Source ISO File',
                tooltip: 'Select the ISO file to use as source',
                type: 'select',
                options: 'iso',
                keys_display: ['filename', 'modified'],
                key_value: 'filename',
            },
        ],
        metadata: {
            comment: 'these will be stored in global MODAL_METADATA so you can access them from within onclick functions later',
        },
        data: {
            name: '',
            comment: '',
            arch: '',
            extra_kernel_args: '',
            iso_file: '',
        },
        button_onclicks: {
            save: function(data) {
                console.log('Going to create a generic boot image using: ' + data['iso_file']);
                console.log(data);
            },
        },
    },
};

// New Boot Image - Select a Wizard
function show_modal_boot_image_wizard() {
    const wizard_config = {
        title: 'New Boot Image',
        subtitle: 'Create a new Boot Image',
        height: 400,
        pages: 1,
        inputs: [
            {
                name: 'selected_wizard',
                label: 'Wizard',
                tooltip: 'Select a wizard to create a new boot image',
                type: 'select_static',
                options: [
                    {
                        name: 'Windows Installer from ISO',
                        wizard_id: 'windows-installer-from-iso',
                        description: 'Create a boot image from a Windows 7/8/10/11 ISO file',
                    },
                    {
                        name: 'VMware ESXi installer from ISO',
                        wizard_id: 'esxi-installer-from-iso',
                        description: 'Create a boot image from a VMware ESXi 5/6/7/8 Installer ISO',
                    },
                    {
                        name: 'Debian Webinstaller',
                        wizard_id: 'debian-webinstaller',
                        description: 'Create a minimal boot image to fetch and install Debian from the web',
                    },
                    {
                        name: 'Ubuntu Webinstaller',
                        wizard_id: 'ubuntu-webinstaller',
                        description: 'Create a minimal boot image to fetch and install Ubuntu from the web',
                    },
                    {
                        name: 'Debian Live Image',
                        wizard_id: 'debian-liveimage',
                        description: 'Create a live Debian environment that can be booted without installation',
                    },
                    // {
                    //     name: 'Generic ISO Parser',
                    //     wizard_id: 'generic-from-iso',
                    //     description: 'Try to parse the contents of an ISO and create a boot image',
                    // },
                ],
                keys_display: ['name', 'description'],
                key_value: 'wizard_id',
            },
        ],
        metadata: {
            comment: 'these will be stored in global MODAL_METADATA so you can access them from within onclick functions later',
        },
        data: {
            selected_wizard: 'windows-installer-from-iso',
        },
        button_onclicks: {
            next: function(data) {
                console.log('Chosen wizard: ' + data['selected_wizard']);
                try {
                    const wiz_config = wizards_config_boot_image[data['selected_wizard']];
                    showModal_Wizard(wiz_config);
                } catch (ex) {
                    console.error('Error while showing wizard');
                    console.error(ex);
                }
            },
        },
    };
    console.log(wizard_config);
    showModal_Wizard(wizard_config);
}

// config for all unattended wizards
const wizards_config_unattended = {
    'none': 'none',
};

// New Unattended Config file - Select a Wizard
function show_modal_unattended_wizard() {
    const wizard_config = {
        title: 'New Unattended config',
        subtitle: 'Create a new Unattended config',
        height: 400,
        pages: 1,
        inputs: [
            {
                name: 'selected_wizard',
                label: 'Wizard',
                tooltip: 'Select a wizard to create a new unattended config',
                type: 'select_static',
                options: [
                    {
                        name: 'Windows 10/11',
                        wizard_id: 'windows-10',
                        description: 'Create an unattended config for Windows 10/11',
                    },
                    {
                        name: 'VMware ESXi',
                        wizard_id: 'esxi',
                        description: 'Create an unattended config VMware ESXi 5/6/7/8',
                    },
                    {
                        name: 'Debian',
                        wizard_id: 'debian',
                        description: 'Create an unattended config for Debian',
                    },
                ],
                keys_display: ['name', 'description'],
                key_value: 'wizard_id',
            },
        ],
        metadata: {
            comment: 'these will be stored in global MODAL_METADATA so you can access them from within onclick functions later',
        },
        data: {
            selected_wizard: 'windows-10',
        },
        button_onclicks: {
            next: function(data) {
                console.log('Chosen wizard: ' + data['selected_wizard']);
                // try {
                //     let wiz_config = wizards_config_unattended[data['selected_wizard']];
                //     showModal_Wizard(wiz_config);
                // } catch (ex) {
                //     console.error('Error while showing wizard');
                //     console.error(ex);
                // }
            },
        },
    };
    console.log(wizard_config);
    showModal_Wizard(wizard_config);
}

