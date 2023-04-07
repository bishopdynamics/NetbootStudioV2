// NSViewController - manage entire app view

// TODO rewrite fancylist to use our new unified button parser

VIEW_CONTROLLER_CONFIG = {
    settings: {},
    layout: {
        layout_type: 'tabbed_pages_left',
        layout_description: 'collection of pages with grouped nav buttons on the left side',
        comment: 'layout_type exists to leave the option open for different layouts later',
        layout_data: {
            pages: {
                clients: {
                    title: 'Manage Clients',
                    description: 'Manage how individual clients should behave when they boot from network',
                    buttons: {},
                    content_type: 'fancylist',
                    content_data: {
                        header_titles: ['Hostname', 'MAC Address', 'IP Address', 'Architecture', 'Config'],
                        prop_names: ['hostname', 'mac', 'ip', 'arch', 'config'],
                        item_icon_chooser: function(entry) {
                            return {icon: 'dns', color: 'blue-grey'};
                        },
                        item_buttons: {
                            edit: {
                                button_type: 'icon',
                                tooltip: 'Edit this client\'s config',
                                icon: 'create',
                                click_type: 'show_modal_item',
                                click_data: {
                                    modal_name: 'edit_client',
                                    id_prop: 'mac',
                                },
                            },
                            delete: {
                                button_type: 'icon',
                                tooltip: 'Delete this client',
                                icon: 'delete',
                                click_type: 'show_modal_item',
                                click_data: {
                                    modal_name: 'delete_item',
                                    item_type: 'client',
                                    id_prop: 'mac',
                                },
                            },
                        },
                    },
                },
                client_status: {
                    title: 'Client Status',
                    description: 'Any clients that are in the process of netbooting will show their status here',
                    buttons: {},
                    content_type: 'datasource_table',
                    content_data: {
                        target_div_id: 'client_status_content',
                        data_source_name: 'clients',
                        header_height: 10,
                        item_height: 10,
                        headers: {
                            client: {
                                width: 20,
                                display: 'Client',
                            },
                            state_text: {
                                width: 30,
                                display: 'State',
                            },
                            description: {
                                width: 50,
                                display: 'Description',
                            },
                            // state_expiration: {
                            //     width: 15,
                            //     display: 'Expiration',
                            // },
                            // state_expiration_action: {
                            //     width: 10,
                            //     display: 'Expiration Action',
                            // },
                        },
                        filter_function: function(entry) {
                            console.info('filtering: ', entry);
                            const stateobj = entry.state.state;
                            let hostname;
                            if (entry.hostname === 'unknown' || entry.hostname === 'Unknown') {
                                hostname = entry.mac;
                            } else {
                                hostname = entry.hostname;
                            }
                            return {
                                client: hostname,
                                state_text: stateobj.state_text,
                                description: stateobj.description,
                                // state_expiration: stateobj.state_expiration,
                                // state_expiration_action: stateobj.state_expiration_action,
                            };
                        },
                    },
                },
                boot_images: {
                    title: 'Manage Boot Images',
                    description: 'Boot Images hold everything needed to boot a specific operating system, in most cases an installer. Boot Images can also create live environments for diskless workstations',
                    buttons: {
                        new: {
                            button_type: 'text',
                            tooltip: '',
                            label: 'New',
                            click_type: 'show_modal',
                            click_data: {
                                modal_name: 'new_boot_image',
                                modal_data: {},
                            },
                        },
                    },
                    content_type: 'fancylist',
                    content_data: {
                        header_titles: ['Name', 'Created', 'Image Type', 'Architecture', 'Description'],
                        prop_names: ['boot_image_name', 'created', 'image_type', 'arch', 'description'],
                        item_icon_chooser: function(entry) {
                            return {icon: 'description', color: 'blue-grey'};
                        },
                        item_buttons: {
                            delete: {
                                button_type: 'icon',
                                tooltip: 'Delete this boot image',
                                icon: 'delete',
                                click_type: 'show_modal_item',
                                click_data: {
                                    modal_name: 'delete_item',
                                    item_type: 'boot_image',
                                    id_prop: 'boot_image_name',
                                },
                            },
                        },
                    },
                },
                unattended_configs: {
                    title: 'Manage Unattended Installation Configurations',
                    description: 'When combined with a Boot Image which supports unattended installation, an unattended config file can completely automate the installation of an operating system. Note that for most operating systems, any needed config that is not addressed by your config file, will cause it to prompt for user input, so you really need to specify answers to all configuration options',
                    buttons: {
                        new: {
                            button_type: 'text',
                            tooltip: '',
                            label: 'New',
                            click_type: 'show_modal',
                            click_data: {
                                modal_name: 'editor',
                                modal_data: {
                                    file_category: 'unattended_configs',
                                    file_new: true,
                                    file_allowed_extensions: ['.cfg', '.xml'],
                                },
                            },
                        },
                        upload: {
                            button_type: 'text',
                            tooltip: '',
                            label: 'Upload',
                            click_type: 'show_modal',
                            click_data: {
                                modal_name: 'upload',
                                modal_data: {
                                    upload_category: 'unattended_configs',
                                    upload_allowed_extensions: ['.cfg', '.xml'],
                                },
                            },
                        },
                    },
                    content_type: 'fancylist',
                    content_data: {
                        header_titles: ['File Name', 'Last Modified'],
                        prop_names: ['filename', 'modified'],
                        item_buttons: {
                            edit: {
                                button_type: 'icon',
                                tooltip: 'Edit this unattended config',
                                icon: 'create',
                                click_type: 'show_modal_item',
                                click_data: {
                                    modal_name: 'edit_file',
                                    id_prop: 'filename',
                                },
                            },
                            delete: {
                                button_type: 'icon',
                                tooltip: 'Delete this unattended config',
                                icon: 'delete',
                                click_type: 'show_modal_item',
                                click_data: {
                                    modal_name: 'delete_item',
                                    item_type: 'unattended_configs',
                                    id_prop: 'filename',
                                },
                            },
                        },
                        item_icon_chooser: function(entry) {
                            return {icon: 'description', color: 'blue-grey'};
                        },
                    },
                },
                stage4: {
                    title: 'Manage Stage4 Files',
                    description: 'Stage4 is a post-installation config system, based on simple shell scripts on unix-like systems, and batch scripts on windows systems.',
                    buttons: {
                        new: {
                            button_type: 'text',
                            tooltip: '',
                            label: 'New',
                            click_type: 'show_modal',
                            click_data: {
                                modal_name: 'editor',
                                modal_data: {
                                    file_category: 'stage4',
                                    file_new: true,
                                    file_allowed_extensions: ['.sh', '.bat'],
                                },
                            },
                        },
                        upload: {
                            button_type: 'text',
                            tooltip: '',
                            label: 'Upload',
                            click_type: 'show_modal',
                            click_data: {
                                modal_name: 'upload',
                                modal_data: {
                                    upload_category: 'stage4',
                                    upload_allowed_extensions: ['.sh', '.bat'],
                                },
                            },
                        },
                    },
                    content_type: 'fancylist',
                    content_data: {},
                },
                ipxe_builds: {
                    title: 'Manage iPXE Builds',
                    description: 'iPXE is a network bootloader, and the first executable in our netbooting chain. You need at least one build with the default stage1 file for each client architecture you intend to boot.',
                    buttons: {
                        new: {
                            button_type: 'text',
                            tooltip: '',
                            label: 'New',
                            click_type: 'show_modal',
                            click_data: {
                                modal_name: 'new_ipxe_build',
                                modal_data: {},
                            },
                        },
                    },
                    content_type: 'fancylist',
                    content_data: {},
                },
                stage1_files: {
                    title: 'Manage iPXE Stage1 Files',
                    description: 'Stage1 files are embedded into iPXE builds, and provide the foundation for fetching Boot Images. In most cases, the built-in default Stage1 file is all that is needed.',
                    buttons: {
                        new: {
                            button_type: 'text',
                            tooltip: '',
                            label: 'New',
                            click_type: 'show_modal',
                            click_data: {
                                modal_name: 'editor',
                                modal_data: {
                                    file_category: 'stage1_files',
                                    file_new: true,
                                    file_allowed_extensions: ['.ipxe'],
                                },
                            },
                        },
                        upload: {
                            button_type: 'text',
                            tooltip: '',
                            label: 'Upload',
                            click_type: 'show_modal',
                            click_data: {
                                modal_name: 'upload',
                                modal_data: {
                                    upload_category: 'stage1_files',
                                    upload_allowed_extensions: ['.ipxe'],
                                },
                            },
                        },
                    },
                    content_type: 'fancylist',
                    content_data: {},
                },
                uboot_scripts: {
                    title: 'Manage Custom u-boot Scripts',
                    description: 'When a u-boot client tries to netboot, the first thing it fetches is boot.scr.uimg from tftp server. This is a great place to setup environment variables for these clients. Netboot Studio does not use this feature (the default is a blank script) but you can specify a custom script here.',
                    buttons: {
                        new: {
                            button_type: 'text',
                            tooltip: '',
                            label: 'New',
                            click_type: 'show_modal',
                            click_data: {
                                modal_name: 'editor',
                                modal_data: {
                                    file_category: 'uboot_scripts',
                                    file_new: true,
                                    file_allowed_extensions: ['.scr'],
                                },
                            },
                        },
                        upload: {
                            button_type: 'text',
                            tooltip: '',
                            label: 'Upload',
                            click_type: 'show_modal',
                            click_data: {
                                modal_name: 'upload',
                                modal_data: {
                                    upload_category: 'uboot_scripts',
                                    upload_allowed_extensions: ['.scr'],
                                },
                            },
                        },
                    },
                    content_type: 'fancylist',
                    content_data: {},
                },
                iso: {
                    title: 'ISO Files',
                    description: 'For some boot image creation tasks (like Windows), an original ISO file is needed as input',
                    buttons: {
                        upload: {
                            button_type: 'text',
                            tooltip: '',
                            label: 'Upload',
                            click_type: 'show_modal',
                            click_data: {
                                modal_name: 'upload',
                                modal_data: {
                                    upload_category: 'iso',
                                    upload_allowed_extensions: ['.iso'],
                                },
                            },
                        },
                    },
                    content_type: 'fancylist',
                    content_data: {},
                },
                tftp_root: {
                    title: 'Manage files in TFTP root',
                    description: 'Place other files you need available via TFTP here, such as switch configs and images, and dtb files for arm-based clients. Keep in mind that boot.scr.uimg and ipxe.bin are reserved filenames and will be ignored if you place them here.',
                    buttons: {
                        upload: {
                            button_type: 'text',
                            tooltip: '',
                            label: 'Upload',
                            click_type: 'show_modal',
                            click_data: {
                                modal_name: 'upload',
                                modal_data: {
                                    upload_category: 'tftp_root',
                                    upload_allowed_extensions: null,
                                },
                            },
                        },
                    },
                    content_type: '',
                    content_data: {},
                },
                settings: {
                    title: 'Settings',
                    description: '',
                    buttons: {
                        edit_settings: {
                            button_type: 'text',
                            tooltip: '',
                            label: 'Edit Settings',
                            click_type: 'show_modal',
                            click_data: {
                                modal_name: 'settings',
                                modal_data: {},
                            },
                        },
                    },
                    content_type: '',
                    content_data: {},
                },
                debugging: {
                    title: '',
                    description: 'This page should not normally be visible',
                    buttons: {},
                    content_type: '',
                    content_data: {},
                },
            },
            page_groups: {
                basic: {
                    label: 'Basic',
                    members: [
                        'clients', 'client_status', 'boot_images', 'unattended_configs', 'stage4',
                    ],
                },
                advanced: {
                    label: 'Advanced',
                    members: [
                        'ipxe_builds', 'stage1_files', 'uboot_scripts', 'iso', 'tftp_root', 'settings',
                    ],
                },
            },
        },
    },
};

class NSViewController {
    constructor(target_div_id, config) {
        this.target_div_id = target_div_id;
        this.config = config;
        this.render();
    }

    render() {
        // render the entire view from config

    }
}

