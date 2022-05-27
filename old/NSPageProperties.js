// Page properties for all pages

//  user primary_color_classes,then additional from color_modifiers[]
//

let PAGE_PROPERTIES = {
        main: {
            style: {
                comment: 'this is where we define the colors for things, via classes. remember all values should be arrays',
                primary_color_classes: ['blue-grey'],
                color_modifiers: {
                    'tab_content_wrapper': ['lighten-2'],
                },
                button_classes: ['waves-effect', 'waves-light'],
                header_title_classes: ['brand-logo'],  // for Netboot Studio in header
                footer_copyright_classes: [],  // for copyright and version in footer
            },
            strings: {
                comment: 'store static text here, so that its not repeated all over the place',
                title: 'Netboot Studio',
                copyright: COPYRIGHT_STRING,
            },
            layout: {
                comment: 'we only have one layout right now, panes.',
                layout_type: 'NSLayout_Panes',
                properties: {
                    comment: [
                        'panes have absolute positioning. you must supply top, bottom, left, right. Instead of top or bottom you can supply height. instead of left or right supply width.',
                        'remember all position values are numbers, in pixels (not string like "25px")',
                        'all entries in position will be appended with "px", and used as a css property. you can use any css property that can take a value in px'
                    ],
                    panes: [
                        {
                            name: 'pane_header',
                            position: {
                                top: 0,
                                height: 64,
                                left: 0,
                                right: 0,
                            },
                            content_type: 'NSHeaderPaneController',
                            properties: {},  // header doesnt need any properties
                        },
                        {
                            name: 'pane_tabs',
                            position: {
                                top: 64,
                                bottom: 364,
                                left: 5,
                                right: 5,
                            },
                            content_type: 'NSTabsController',
                            properties: {
                                comment: [
                                    'tab sections are iterated first, and then each tab that belongs in that section'
                                ],
                                tabs_config: {
                                    comment: [
                                        'position can be left, right, top, bottom',
                                        'if position left/right then tabs carousel will animate left right',
                                        'when tabs are built, they will be in a single row or column and animated along that axis',
                                    ],
                                    nav_size: 300,
                                    nav_position: 'left',
                                },
                                tab_sections: [
                                    {
                                        name: 'basic',
                                        display: 'Basic'
                                    },
                                    {
                                        name: 'advanced',
                                        display: 'Advanced'
                                    }
                                ],
                                tabs: [
                                    {
                                        name: 'clients',
                                        section: 'basic',
                                        display: 'Clients',
                                        title: 'Manage Clients',
                                        subtitle: 'Manage how individual clients will behave when they boot from network.',
                                        content: {
                                            content_type: 'FancyList',
                                            properties: {
                                                header_titles: ['Hostname', 'MAC Address', 'IP Address', 'Architecture', 'Config'],
                                                prop_names: ['hostname', 'mac', 'ip', 'arch', 'config'],
                                                // header_titles: ['Hostname', 'MAC Address', 'IP Address', 'Architecture', 'Config', 'State', 'Information'],
                                                // prop_names: ['hostname', 'mac', 'ip', 'arch', 'config', 'state', 'info'],
                                                item_buttons: [
                                                    {
                                                        'action': 'edit',
                                                        'item_prop_arg': 'mac',
                                                        'material_icon': 'create',
                                                        'tooltip': 'Edit this client\'s config'
                                                    },
                                                    {
                                                        'action': 'delete',
                                                        'item_prop_arg': 'mac',
                                                        'material_icon': 'delete',
                                                        'tooltip': 'Delete this client'
                                                    },
                                                ],
                                                item_button_click: function (action, client_mac) {
                                                    console.log('you clicked ' + action + ' for client with mac: ' + client_mac);
                                                    if (action === 'edit') {
                                                        show_modal_editclient(client_mac);
                                                    }
                                                    if (action === 'delete') {
                                                        APICall('delete_client', {mac: client_mac}, function (returnitem) {
                                                            console.log(returnitem);
                                                        });
                                                        let client_id = client_mac.replace(/:/g, '-');
                                                        let toast_class = 'toast_client_state_' + client_id;
                                                        let toast_instance = M.Toast.getInstance(document.querySelector('.' + toast_class));
                                                        // TODO dunno why linter cant find the method, its there, maybe its not public?
                                                        toast_instance.dismiss();
                                                    }
                                                },
                                                item_icon_chooser: function (entry) {
                                                    return {icon: 'dns', color: 'blue-grey'};
                                                }
                                            }
                                        }
                                    },
                                    {
                                        name: 'client_status',
                                        section: 'basic',
                                        display: 'Client Status',
                                        title: 'Monitor Client Status',
                                        subtitle: 'When clients boot using Netboot Studio, their progress will be tracked here.',
                                        content: {
                                            content_type: 'DataSourceTable',
                                            properties: {
                                                target_div_id: 'client_status_content',
                                                data_source_name: 'clients',
                                                header_height: 10,
                                                item_height: 10,
                                                headers: {
                                                    state: {
                                                        width: 15,
                                                        display: 'State',
                                                    },
                                                    state_text: {
                                                        width: 25,
                                                        display: 'State',
                                                    },
                                                    description: {
                                                        width: 25,
                                                        display: 'Description',
                                                    },
                                                },
                                                filter_function: function (entry) {
                                                    console.info('filtering: ', entry)
                                                    const stateobj = entry.state.state;
                                                    return {
                                                        state: stateobj.state,
                                                        state_text: stateobj.state_text,
                                                        description: stateobj.description,
                                                    }
                                                },
                                            },
                                        }
                                    },
                                    {
                                        name: 'boot_images',
                                        section: 'basic',
                                        display: 'Boot Images',
                                        title: 'Manage Boot Images',
                                        subtitle: 'Boot Images hold everything needed to boot a specific operating system, in most cases an installer. Boot Images can also create live environments for diskless workstations.',
                                        content: {
                                            content_type: 'FancyList',
                                            properties: {
                                                header_titles: ['Name', 'Created', 'Image Type', 'Architecture', 'Description'],
                                                prop_names: ['boot_image_name', 'created', 'image_type', 'arch', 'description'],
                                                item_buttons: [
                                                    // {'action': 'edit',   'item_prop_arg': 'boot_image_name', 'material_icon': 'create', 'tooltip': 'Edit this boot image'},
                                                    {
                                                        'action': 'delete',
                                                        'item_prop_arg': 'boot_image_name',
                                                        'material_icon': 'delete',
                                                        'tooltip': 'Delete this boot image'
                                                    },
                                                ],
                                                item_button_click: function (action, name) {
                                                    console.log('you clicked ' + action + ' for boot image with name: ' + name);
                                                    if (action === 'delete') {
                                                        APICall('delete_boot_image', {name: name}, function (returnitem) {
                                                            console.log(returnitem);
                                                        })
                                                    }
                                                },
                                                item_icon_chooser: function (entry) {
                                                    return {icon: 'description', color: 'blue-grey'};
                                                }
                                            },
                                        }
                                    },
                                    {
                                        name: 'unattended_configs',
                                        section: 'basic',
                                        display: 'Unattended Configs',
                                        title: 'Manage Unattended Installation Configurations',
                                        subtitle: 'When combined with a Boot Image which supports unattended installation, an unattended config file can completely automate the installation of an operating system. Note that for most operating systems, any needed config that is not addressed by your config file, will cause it to prompt for user input, so you really need to specify answers to all configuration options.',
                                        content: {
                                            content_type: 'FancyList',
                                            properties: {
                                                header_titles: ['File Name', 'Last Modified'],
                                                prop_names: ['filename', 'modified'],
                                                item_buttons: [
                                                    // {'action': 'edit',   'item_prop_arg': 'filename', 'material_icon': 'create', 'tooltip': 'edit this unatteded config'},
                                                    {
                                                        'action': 'delete',
                                                        'item_prop_arg': 'filename',
                                                        'material_icon': 'delete',
                                                        'tooltip': 'Delete this unattended config'
                                                    },
                                                ],
                                                item_button_click: function (action, filename) {
                                                    console.log('you clicked ' + action + ' for unattended config file: ' + filename);
                                                    if (action === 'delete') {
                                                        APICall('delete_unattended_config', {filename: filename}, function (returnitem) {
                                                            console.log(returnitem);
                                                        })
                                                    }
                                                },
                                                item_icon_chooser: function (entry) {
                                                    return {icon: 'description', color: 'blue-grey'};
                                                }
                                            },
                                        }
                                    },
                                    {
                                        name: 'stage4',
                                        section: 'basic',
                                        display: 'Stage4 Scripts',
                                        title: 'Manage Stage4 Scripts',
                                        subtitle: 'Stage4 is a post-installation config system, based on simple shell scripts on unix-like systems, and batch scripts on windows systems.',
                                        content: {
                                            content_type: 'FancyList',
                                            properties: {
                                                header_titles: ['Script Name', 'Last Modified'],
                                                prop_names: ['filename', 'modified'],
                                                item_buttons: [
                                                    // {'action': 'edit', 'item_prop_arg': 'filename', 'material_icon': 'create', 'tooltip': 'Edit this stage4 script'},
                                                    {
                                                        'action': 'delete',
                                                        'item_prop_arg': 'filename',
                                                        'material_icon': 'delete',
                                                        'tooltip': 'Delete this stage4 script'
                                                    },
                                                ],
                                                item_button_click: function (action, filename) {
                                                    console.log('you clicked ' + action + ' for stage4 script: ' + filename);
                                                    if (action === 'delete') {
                                                        APICall('delete_stage4', {filename: filename}, function (returnitem) {
                                                            console.log(returnitem);
                                                        })
                                                    }
                                                },
                                                item_icon_chooser: function (entry) {
                                                    return {icon: 'description', color: 'blue-grey'};
                                                },
                                            },
                                        }
                                    },
                                    {
                                        name: 'ipxe_builds',
                                        section: 'advanced',
                                        display: 'iPXE Builds',
                                        title: 'Manage iPXE Builds',
                                        subtitle: 'iPXE is a network bootloader, and Netboot Studio uses it to kick off the whole process. It is the first binary that the client executes. You need to have at least one build for each client architecture.',
                                        content: {
                                            content_type: 'FancyList',
                                            properties: {
                                                header_titles: ['Name', 'Commit ID', 'Architecture', 'Build Timestamp', 'Embedded Stage1', 'Comment'],
                                                prop_names: ['build_name', 'commit_id', 'arch', 'build_timestamp', 'stage1', 'comment'],
                                                item_buttons: [
                                                    // {'action': 'edit',   'item_prop_arg': 'build_id', 'material_icon': 'create', 'tooltip': 'Edit this ipxe build'},
                                                    {
                                                        'action': 'delete',
                                                        'item_prop_arg': 'build_id',
                                                        'material_icon': 'delete',
                                                        'tooltip': 'Delete this ipxe build'
                                                    },
                                                    {
                                                        'action': 'download_iso',
                                                        'item_prop_arg': 'build_id',
                                                        'material_icon': 'file_download',
                                                        'tooltip': 'Download ipxe.iso'
                                                    },
                                                    {
                                                        'action': 'download_iso_nomenu',
                                                        'item_prop_arg': 'build_id',
                                                        'material_icon': 'file_download',
                                                        'tooltip': 'Download ipxe-nomenu.iso without stage1 embedded'
                                                    },
                                                ],
                                                item_button_click: function (action, build_id) {
                                                    console.log('you clicked ' + action + ' for ipxe build with id: ' + build_id);
                                                    let iso_url_base = 'https://' + window.location.host + '/ipxe_builds/' + build_id
                                                    if (action === 'download_iso') {
                                                        let download_url = iso_url_base + '/ipxe.iso';
                                                        download_a_file(download_url, 'ipxe.iso')
                                                    }
                                                    if (action === 'download_iso_nomenu') {
                                                        let download_url = iso_url_base + '/ipxe-nomenu.iso';
                                                        download_a_file(download_url, 'ipxe-nomenu.iso')
                                                    }
                                                    if (action === 'delete') {
                                                        APICall('delete_ipxe_build', {build_id: build_id}, function (returnitem) {
                                                            console.log(returnitem);
                                                        })
                                                    }
                                                },
                                                item_icon_chooser: function (entry) {
                                                    return {icon: 'folder', color: 'blue-grey'};
                                                }
                                            },
                                        }
                                    },
                                    {
                                        name: 'stage1_files',
                                        section: 'advanced',
                                        display: 'Stage1 Files',
                                        title: 'Manage iPXE Stage1 Files',
                                        subtitle: 'Stage1 files are embedded into iPXE builds, and provide the foundation for fetching Boot Images. In most cases, the built-in default Stage1 file is all that is needed.',
                                        content: {
                                            content_type: 'FancyList',
                                            properties: {
                                                header_titles: ['File Name', 'Last Modified'],
                                                prop_names: ['filename', 'modified'],
                                                item_buttons: [
                                                    // {'action': 'edit', 'item_prop_arg': 'filename', 'material_icon': 'create', 'tooltip': 'Edit this stage1 file'},
                                                    {
                                                        'action': 'delete',
                                                        'item_prop_arg': 'filename',
                                                        'material_icon': 'delete',
                                                        'tooltip': 'Delete this stage1 file'
                                                    },
                                                ],
                                                item_button_click: function (action, filename) {
                                                    console.log('you clicked ' + action + ' for stage1 file: ' + filename);
                                                    if (action === 'delete') {
                                                        APICall('delete_stage1_file', {filename: filename}, function (returnitem) {
                                                            console.log(returnitem);
                                                        })
                                                    }
                                                },
                                                item_icon_chooser: function (entry) {
                                                    return {icon: 'description', color: 'blue-grey'};
                                                },
                                            },
                                        }
                                    },
                                    {
                                        name: 'uboot_scripts',
                                        section: 'advanced',
                                        display: 'Custom U-Boot Scripts',
                                        title: 'Manage Custom U-Boot Scripts',
                                        subtitle: 'When a u-boot client tries to netboot, the first thing it fetches is boot.scr.uimg from tftp server. This is a great place to setup environment variables for these clients. Netboot Studio does not use this feature (the default is a blank script) but you can specify a custom script here.',
                                        content: {
                                            content_type: 'FancyList',
                                            properties: {
                                                header_titles: ['File Name', 'Last Modified'],
                                                prop_names: ['filename', 'modified'],
                                                item_buttons: [
                                                    {
                                                        'action': 'edit',
                                                        'item_prop_arg': 'filename',
                                                        'material_icon': 'create',
                                                        'tooltip': 'Edit this u-boot script'
                                                    },
                                                    {
                                                        'action': 'delete',
                                                        'item_prop_arg': 'filename',
                                                        'material_icon': 'delete',
                                                        'tooltip': 'Delete this u-boot script'
                                                    },
                                                ],
                                                item_button_click: function (action, filename) {
                                                    console.log('you clicked ' + action + ' for uboot script: ' + filename);
                                                    if (action === 'delete') {
                                                        APICall('delete_uboot_script', {filename: filename}, function (returnitem) {
                                                            console.log(returnitem);
                                                        })
                                                    }
                                                },
                                                item_icon_chooser: function (entry) {
                                                    return {icon: 'description', color: 'blue-grey'};
                                                }
                                            },
                                        }
                                    },
                                    {
                                        name: 'iso',
                                        section: 'advanced',
                                        display: 'ISO Files',
                                        title: 'Manage ISO Files',
                                        subtitle: 'For some boot image creation tasks (like Windows), one needs to start with an ISO file. Custom boot images can also attempt to boot an ISO file directly.',
                                        content: {
                                            content_type: 'FancyList',
                                            properties: {
                                                header_titles: ['File Name', 'Last Modified'],
                                                prop_names: ['filename', 'modified'],
                                                item_buttons: [
                                                    {
                                                        'action': 'delete',
                                                        'item_prop_arg': 'filename',
                                                        'material_icon': 'delete',
                                                        'tooltip': 'Delete this iso file'
                                                    },
                                                ],
                                                item_button_click: function (action, filename) {
                                                    console.log('you clicked ' + action + ' for iso: ' + filename);
                                                    if (action === 'delete') {
                                                        APICall('delete_iso', {filename: filename}, function (returnitem) {
                                                            console.log(returnitem);
                                                        })
                                                    }
                                                },
                                                item_icon_chooser: function (entry) {
                                                    return {icon: 'description', color: 'blue-grey'};
                                                }
                                            },
                                        }
                                    },
                                    {
                                        name: 'wimboot_builds',
                                        section: 'advanced',
                                        display: 'Wimboot Builds',
                                        title: 'Manage Wimboot Builds',
                                        subtitle: 'Wimboot is a utility used to make it easier to load Windows images, brought to you by the fine people at iPXE.',
                                        content: {
                                            content_type: 'FancyList',
                                            properties: {
                                                header_titles: ['Name', 'Commit ID', 'Architecture', 'Build Timestamp', 'Comment'],
                                                prop_names: ['name', 'commit_id', 'arch', 'build_timestamp', 'comment'],
                                                item_buttons: [
                                                    // {'action': 'edit',   'item_prop_arg': 'build_id', 'material_icon': 'create', 'tooltip': 'Edit this wimboot build'},
                                                    {
                                                        'action': 'delete',
                                                        'item_prop_arg': 'build_id',
                                                        'material_icon': 'delete',
                                                        'tooltip': 'Delete this wimboot build'
                                                    },
                                                    {
                                                        'action': 'download_file',
                                                        'item_prop_arg': 'build_id',
                                                        'material_icon': 'file_download',
                                                        'tooltip': 'Download this wimboot build'
                                                    },
                                                ],
                                                item_button_click: function (action, build_id) {
                                                    console.log('you clicked ' + action + ' for wimboot build with id: ' + build_id);
                                                    let iso_url_base = 'https://' + window.location.host + '/wimboot_builds/' + build_id
                                                    if (action === 'download_file') {
                                                        let download_url = iso_url_base + '/wimboot';
                                                        download_a_file(download_url, 'wimboot')
                                                    }
                                                    if (action === 'delete') {
                                                        APICall('delete_wimboot_build', {build_id: build_id}, function (returnitem) {
                                                            console.log(returnitem);
                                                        })
                                                    }
                                                },
                                                item_icon_chooser: function (entry) {
                                                    return {icon: 'folder', color: 'blue-grey'};
                                                }
                                            },
                                        }
                                    },
                                    {
                                        name: 'tftp_root',
                                        section: 'advanced',
                                        display: 'TFTP Root',
                                        title: 'Manage Files in TFTP Root',
                                        subtitle: 'Place other files you need available via TFTP here, such as switch configs and images, and dtb files for arm-based clients. Keep in mind that boot.scr.uimg and ipxe.efi are reserved filenames and will be ignored if you place them here.',
                                        content: {
                                            content_type: 'FancyList',
                                            properties: {
                                                header_titles: ['File Name', 'Last Modified', 'Description'],
                                                prop_names: ['filename', 'modified', 'description'],
                                                item_buttons: [
                                                    {
                                                        'action': 'delete',
                                                        'item_prop_arg': 'filename',
                                                        'material_icon': 'delete',
                                                        'tooltip': 'Delete this tftp file'
                                                    },
                                                ],
                                                item_button_click: function (action, filename) {
                                                    console.log('you clicked ' + action + ' for iso: ' + filename);
                                                },
                                                item_icon_chooser: function (entry) {
                                                    return {icon: 'description', color: 'blue-grey'};
                                                }
                                            },
                                        }
                                    },
                                    {
                                        name: 'debugging',
                                        section: 'advanced',
                                        display: 'Debugging',
                                        title: 'Debugging Page',
                                        subtitle: 'This should be hidden',
                                        content: {
                                            content_type: 'NSGroup',
                                            group_members: [
                                                {
                                                    title: 'Buttons',
                                                    subtitle: 'Trigger various events',
                                                    content_type: 'NSButton',
                                                    properties: {
                                                        'label': 'Fake Long Task',
                                                        'on_click': function (event) {
                                                            create_task('fake_longtask');
                                                        }
                                                    }
                                                },
                                                {
                                                    title: 'Client States',
                                                    subtitle: 'View all client state info',
                                                    content_type: 'NSDataSourceTable',
                                                    properties: {
                                                        data_source_name: 'clients',
                                                        header_height: 10,
                                                        item_height: 10,
                                                        headers: {
                                                            active: {
                                                                width: 15,
                                                                display: 'Active',
                                                            },
                                                            state: {
                                                                width: 15,
                                                                display: 'State',
                                                            },
                                                            state_text: {
                                                                width: 25,
                                                                display: 'State Text',
                                                            },
                                                            description: {
                                                                width: 25,
                                                                display: 'Description',
                                                            },
                                                            state_expiration: {
                                                                width: 15,
                                                                display: 'Expiration',
                                                            },
                                                            state_expiration_action: {
                                                                width: 10,
                                                                display: 'Expiration Action',
                                                            },
                                                            error: {
                                                                width: 15,
                                                                display: 'Error',
                                                            },
                                                            error_short: {
                                                                width: 15,
                                                                display: 'Error Short',
                                                            },
                                                        },
                                                        filter_function: function (entry) {
                                                            console.info('filtering: ', entry)
                                                            const stateobj = entry.state.state;

                                                            return {
                                                                active: stateobj.active,
                                                                state: stateobj.state,
                                                                state_text: stateobj.state_text,
                                                                description: stateobj.description,
                                                                state_expiration: stateobj.state_expiration,
                                                                state_expiration_action: stateobj.state_expiration_action,
                                                                error: stateobj.error,
                                                                error_short: stateobj.error_short,
                                                            }
                                                        },
                                                    },
                                                },
                                                {
                                                    title: 'Client Information',
                                                    subtitle: 'View information discovered about clients',
                                                    content_type: 'DataSourceTable',
                                                    properties: {
                                                        data_source_name: 'clients',
                                                        header_height: 10,
                                                        item_height: 10,
                                                        headers: {
                                                            dhcp: {
                                                                width: 15,
                                                                display: 'From DHCP Sniffer Discovery',
                                                            },
                                                            ipxe: {
                                                                width: 25,
                                                                display: 'From iPXE Stage2 Invocation',
                                                            },
                                                        },
                                                        filter_function: function (entry) {
                                                            console.info('filtering: ', entry)
                                                            return entry.info;
                                                        },
                                                    },
                                                }
                                            ],
                                        }
                                    },
                                    {
                                        name: 'settings',
                                        section: 'basic',
                                        display: 'Settings',
                                        title: 'Netboot Studio Settings',
                                        subtitle: '',
                                        content: {
                                            content_type: '',
                                            properties: {},
                                        }
                                    },
                                ],
                            },
                        },
                        {
                            name: 'pane_tasks',
                            position: {
                                bottom: 64,
                                height: 300,
                                left: 5,
                                right: 5,
                            },
                            content_type: 'NSTasksPaneController',
                            properties: {
                                    target_div_id: 'main-tasklist',
                                    data_source_name: 'tasks',
                                    header_height: 10,
                                    item_height: 10,
                                    headers: {
                                        // task_id: {
                                        // 	width: 10,
                                        // 	display: 'Task ID',
                                        // },
                                        task_name: {
                                            width: 10,
                                            display: 'Name',
                                        },
                                        task_description: {
                                            width: 20,
                                            display: 'Description',
                                        },
                                        task_type: {
                                            width: 10,
                                            display: 'Task Type',
                                        },
                                        task_status: {
                                            width: 10,
                                            display: 'Status',
                                        },
                                        task_progress: {
                                            width: 10,
                                            display: 'Progress',
                                        },
                                        task_progress_description: {
                                            width: 20,
                                            display: 'Progress Description',
                                        },
                                        task_current_subtask: {
                                            width: 10,
                                            display: 'Current Subtask',
                                        },
                                    },
                                    filter_function: function (entry) {
                                        entry.task_progress += '%';
                                        return entry;
                                    }
                                },
                        },
                        {
                            name: 'pane_footer',
                            position: {
                                bottom: 0,
                                height: 64,
                                left: 0,
                                right: 0,
                            },
                            content_type: 'NSFooterPaneController',
                            properties: {},  // footer doesnt need any properties
                        }
                    ],
                },
            },
        }
}

