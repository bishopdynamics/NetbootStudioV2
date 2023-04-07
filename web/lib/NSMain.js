// these functions are specific to the Main page


//  will be defined by backend /variables.js
// _BROKER_PORT
// _BROKER_USER
// _BROKER_PASSWORD
// WEBSERVER_PORT
// APISERVER_PORT
// UPLOADSERVER_PORT
// WEBSERVER_UPLOAD_CHUNK_SIZE


const BROKER_PORT = _BROKER_PORT;
const BROKER_USER = _BROKER_USER;
const BROKER_PASSWORD = _BROKER_PASSWORD;
const COPYRIGHT_STRING =_COPYRIGHT_STRING;

// This check lets you run the server locally while connected to backend on host: james-netboot
let URL_BROKER = 'wss://' + window.location.hostname + ':' + BROKER_PORT + '';
if (window.location.hostname === 'localhost') {
    URL_BROKER = 'wss://' + 'james-netboot' + ':' + BROKER_PORT + '';
}

// https://materializecss.com/modals.html
const MODAL_SELECTOR = '#common-modal'; // querySelector to get modal div
let MODAL = null; // this will hold our modal instance

const MODAL_OPTIONS = {
    opacity: 0.7,
    inDuration: 250,
    outDuration: 250,
    preventScrolling: true,
    dismissible: true,
    startingTop: '4%',
    endingTop: '10%',
    onOpenStart: null,
    onOpenEnd: null,
    onCloseStart: null,
    onCloseEnd: null,
};

let MQTT_CLIENT = null;

const REQUEST_REGISTER = {}; // requests are stored here by id, alond with reference to callback

const DATA_SOURCE_REGISTER = []; // data sources are stored here

// all the tab names, so we can iterate over them
const MAIN_ALL_TABNAMES = ['ipxe_builds', 'stage1_files', 'stage4', 'boot_images', 'unattended_configs', 'clients', 'client_status', 'uboot_scripts', 'iso', 'wimboot_builds', 'tftp_root', 'settings', 'debugging'];

// https://materializecss.com/tooltips.html
const TOOLTIP_OPTIONS = {
    exitDelay: 300,
    enterDelay: 300,
    margin: 5,
    inDuration: 500,
    outDuration: 200,
    transitionMovement: 15,
};

function onPageReady() {
    // this is run at DOMContentLoaded
    console.log('onPageReady');
    try {
        M.AutoInit();
        const footer_copyright = document.getElementById('footer-copyright');
        footer_copyright.textContent = COPYRIGHT_STRING;
        document.getElementById('user_password').addEventListener('keyup', function(event) {
            // this is so hitting enter in the password field causes form submit
            // older browsers dont support event.code, old way is event.keyCode === 13
            if (event.code === 'Enter') {
                document.getElementById('submit_button').click();
            }
        });
        RenewAuthToken().then(
            function(value) {
                onAuth(value);
            },
            function(error) {
                console.error(error);
            },
        );
    } catch (e) {
        console.warn('onPageReady had unexpected exception');
    }
}

function onPageReady_new() {
    // new version, runs at DOMContentLoaded
    try {
        view_controller = new NSViewController('view_controller_root', VIEW_CONTROLLER_CONFIG);
    } catch (e) {
        console.warn('onPageReady had unexpected exception');
    }
}

document.addEventListener('DOMContentLoaded', onPageReady);

function SetupMQTTClient() {
    let client = null;
    const client_id = 'NSWebUI-Browser-' + uuid4();
    console.debug('attempting to connect to broker: ' + URL_BROKER);
    try {
        // connect, reconnect, close, disconnect, offline, error, message
        const options = {
            clean: true,
            keepalive: 60,
            connectTimeout: 4000,
            reconnectPeriod: 1000,
            protocolId: 'MQTT',
            protocolVersion: 4,
            clientId: client_id,
            username: BROKER_USER,
            password: BROKER_PASSWORD,
        };
        client = mqtt.connect(URL_BROKER, options);
        client.on('reconnect', function(error) {
            console.warn('Reconnected connection to broker: ' + URL_BROKER + ', error: ' + error);
        });
        client.on('connect', function(context) {
            console.info('Connected to broker: ' + URL_BROKER);
            // console.info('mqtt client context:' + JSON.stringify(context));
        });
        client.on('error', function(error) {
            console.error('An error ocurred with MQTT Client: ' + error);
        });
        client.on('message', function(topic, message) {
            // console.info('A message has arrived on topic: ' + topic + ', message: ' + message);
            if (topic === 'api_response') {
                try {
                    const ns_message = new NSMessage(message);
                    const content = ns_message.get_key('content');
                    if (content.id in REQUEST_REGISTER) {
                        REQUEST_REGISTER[content.id](content.api_payload.result); // pass result to callback
                        delete REQUEST_REGISTER[content.id]; // clean up
                    } else {
                        console.warn('ignoring reqponse to unregistered request id: ' + content.id);
                    }
                } catch (ex) {
                    console.error('failed to handle mqtt message on topic: api_response: ' + ex);
                }
            } else if (topic.includes('NetbootStudio/DataSources/')) {
                DATA_SOURCE_REGISTER.forEach(function(data_source) {
                    if (topic === 'NetbootStudio/DataSources/' + data_source['name']) {
                        data_source['object'].handle_message(message);
                    }
                });
            } else {
                console.info('ignoring message on topic: ' + topic);
            }
        });
        client.subscribe('api_response');
        client.subscribe('task_status');
    } catch (e) {
        console.error('failed to setup mqtt client ( ' + URL_BROKER + ' ): ' + e);
    }
    return client;
}

function main_page_default_state() {
    // set all the things to their default state for a fresh page load
    if (MQTT_CLIENT === null) {
        // use existence of mqtt client as indicator that we already set thse things up
        MQTT_CLIENT = SetupMQTTClient();
        MODAL = M.Modal.init(document.querySelectorAll(MODAL_SELECTOR), MODAL_OPTIONS)[0];
        main_body_nav_onclick('clients');
        setup_clients_table();
        setup_tasks_table();
    }
}

function ShowUploadStatus(file_id, file_name, status, progress, description) {
    // TODO upload status spams task status topic, which causes updates to tasks pane to get backed up, and makes the upload look like it takes longer than it does
    //      in practice, this only really matters with local testing
    const mqtt_topic = 'NetbootStudio/TaskStatus';
    try {
        let subtask = 'uploading_file';
        if (status === 'Complete') {
            subtask = '';
        }
        const message = {
            task_status: {
                'task_id': 'fileupload_' + file_id,
                'task_name': 'Upload: ' + file_name,
                'task_description': 'Uploading file: ' + file_name,
                'task_type': 'file_upload',
                'task_status': status,
                'task_progress': progress,
                'task_progress_description': description,
                'task_current_subtask': subtask,
                'task_subtask_descriptions': {},
            },
        };
        const message_json = JSON.stringify(message);
        MQTT_CLIENT.publish(mqtt_topic, message_json);
    } catch (ex) {
        console.error('exception while ShowUploadStatus: ' + ex);
    }
}


// Tabs

// TODO we can run the populate commands on page load (and show loading thing til done) and then just show and hide the tabs

function main_body_nav_onclick(tabname) {
    // when a tab button is clicked, hide all others and show given one
    try {
        main_body_nav_hide_all();
        main_body_nav_show_tab(tabname);
        const elems = document.querySelectorAll('.modal');
        const options = {
            opacity: 0.5,
            dismissible: true,
        };
        M.Modal.init(elems, options);
        if (tabname === 'ipxe_builds') {
            main_body_tab_ipxe_builds_populate();
        }
        if (tabname === 'wimboot_builds') {
            main_body_tab_wimboot_builds_populate();
        }
        if (tabname === 'stage1_files') {
            main_body_tab_stage1_files_populate();
        }
        if (tabname === 'clients') {
            main_body_tab_clients_populate();
        }
        if (tabname === 'unattended_configs') {
            main_body_tab_unattended_configs_populate();
        }
        if (tabname === 'boot_images') {
            main_body_tab_boot_images_populate();
        }
        if (tabname === 'uboot_scripts') {
            main_body_tab_uboot_scripts_populate();
        }
        if (tabname === 'iso') {
            main_body_tab_iso_populate();
        }
        if (tabname === 'tftp_root') {
            main_body_tab_tftp_root_populate();
        }
        if (tabname === 'stage4') {
            main_body_tab_stage4_populate();
        }
    } catch (ex) {
        console.error('exception while main_body_nav_onclick: ' + ex);
    }
}

function main_body_nav_hide_all() {
    // hide all tabs
    try {
        let i;
        for (i = 0; i < MAIN_ALL_TABNAMES.length; i++) {
            const tabname = MAIN_ALL_TABNAMES[i];
            main_body_nav_hide_tab(tabname);
        }
    } catch (ex) {
        console.error('exception while main_body_nav_hide_all: ' + ex);
    }
}

function main_body_nav_hide_tab(tabname) {
    // hide a tab
    const tabelement = document.getElementById('main-body-content-tab-' + tabname);
    tabelement.style.display = 'none';
}

function main_body_nav_show_tab(tabname) {
    // show a tab
    try {
        const tabelement = document.getElementById('main-body-content-tab-' + tabname);
        tabelement.style.display = 'block';
    } catch (ex) {
        console.error('exception while showing a tab: ' + ex);
    }
}

// populating tabs

// TODO these two can be collapsed into a common populate_tab_builds(datasourcename) situation

function main_body_tab_clients_populate() {
    // TODO removed info because show/hide doesnt work
    const fancy_list_props = {
        parent_div: 'main-body-content-tab-clients-table-wrapper',
        header_titles: ['Hostname', 'MAC Address', 'IP Address', 'Architecture', 'Config'],
        prop_names: ['hostname', 'mac', 'ip', 'arch', 'config'],
        // header_titles: ['Hostname', 'MAC Address', 'IP Address', 'Architecture', 'Config', 'State', 'Information'],
        // prop_names: ['hostname', 'mac', 'ip', 'arch', 'config', 'state', 'info'],
        item_buttons: [
            {'action': 'edit', 'item_prop_arg': 'mac', 'material_icon': 'create', 'tooltip': 'Edit this client\'s config'},
            {'action': 'delete', 'item_prop_arg': 'mac', 'material_icon': 'delete', 'tooltip': 'Delete this client'},
        ],
        item_button_click: function(action, client_mac) {
            console.log('you clicked ' + action + ' for client with mac: ' + client_mac);
            if (action === 'edit') {
                show_modal_editclient(client_mac);
            }
            if (action === 'delete') {
                APICall('delete_client', {mac: client_mac}, function(returnitem) {
                    console.log(returnitem);
                });
                const client_id = client_mac.replace(/:/g, '-');
                const toast_class = 'toast_client_state_' + client_id;
                const toast_instance = M.Toast.getInstance(document.querySelector('.' + toast_class));
                // TODO dunno why linter cant find the method, its there, maybe its not public?
                toast_instance.dismiss();
            }
        },
        item_icon_chooser: function(entry) {
            return {icon: 'dns', color: 'blue-grey'};
        },
    };
    helper_fancylist(fancy_list_props, 'clients', {});
}

function main_body_tab_boot_images_populate() {
    const fancy_list_props = {
        parent_div: 'main-body-content-tab-boot_images-table-wrapper',
        header_titles: ['Name', 'Created', 'Image Type', 'Architecture', 'Description'],
        prop_names: ['boot_image_name', 'created', 'image_type', 'arch', 'description'],
        item_buttons: [
            // {'action': 'edit',   'item_prop_arg': 'boot_image_name', 'material_icon': 'create', 'tooltip': 'Edit this boot image'},
            {'action': 'delete', 'item_prop_arg': 'boot_image_name', 'material_icon': 'delete', 'tooltip': 'Delete this boot image'},
        ],
        item_button_click: function(action, name) {
            console.log('you clicked ' + action + ' for boot image with name: ' + name);
            if (action === 'delete') {
                APICall('delete_boot_image', {name: name}, function(returnitem) {
                    console.log(returnitem);
                });
            }
        },
        item_icon_chooser: function(entry) {
            return {icon: 'description', color: 'blue-grey'};
        },
    };
    helper_fancylist(fancy_list_props, 'boot_images', {});
}

function main_body_tab_unattended_configs_populate() {
    const fancy_list_props = {
        parent_div: 'main-body-content-tab-unattended_configs-table-wrapper',
        header_titles: ['File Name', 'Last Modified'],
        prop_names: ['filename', 'modified'],
        item_buttons: [
            {'action': 'edit', 'item_prop_arg': 'filename', 'material_icon': 'create', 'tooltip': 'edit this unatteded config'},
            {'action': 'delete', 'item_prop_arg': 'filename', 'material_icon': 'delete', 'tooltip': 'Delete this unattended config'},
        ],
        item_button_click: function(action, filename) {
            console.log('you clicked ' + action + ' for unattended config file: ' + filename);
            if (action === 'delete') {
                APICall('delete_unattended_config', {filename: filename}, function(returnitem) {
                    console.log(returnitem);
                });
            }
            if (action === 'edit') {
                APICall('get_file', {file_name: filename, file_category: 'unattended_configs'}, function(returnitem) {
                    console.log(returnitem);
                    show_modal_fileeditor(returnitem);
                });
            }
        },
        item_icon_chooser: function(entry) {
            return {icon: 'description', color: 'blue-grey'};
        },
    };
    helper_fancylist(fancy_list_props, 'unattended_configs', {});
}

function main_body_tab_ipxe_builds_populate() {
    const fancy_list_props = {
        parent_div: 'main-body-content-tab-ipxe_builds-table-wrapper',
        header_titles: ['Name', 'Commit ID', 'Architecture', 'Build Timestamp', 'Embedded Stage1', 'Comment'],
        prop_names: ['build_name', 'commit_id', 'arch', 'build_timestamp', 'stage1', 'comment'],
        item_buttons: [
            // {'action': 'edit',   'item_prop_arg': 'build_id', 'material_icon': 'create', 'tooltip': 'Edit this ipxe build'},
            {'action': 'delete', 'item_prop_arg': 'build_id', 'material_icon': 'delete', 'tooltip': 'Delete this ipxe build'},
            {'action': 'download_iso', 'item_prop_arg': 'build_id', 'material_icon': 'file_download', 'tooltip': 'Download ipxe.iso'},
            {'action': 'download_iso_nomenu', 'item_prop_arg': 'build_id', 'material_icon': 'file_download', 'tooltip': 'Download ipxe-nomenu.iso without stage1 embedded'},
        ],
        item_button_click: function(action, build_id) {
            console.log('you clicked ' + action + ' for ipxe build with id: ' + build_id);
            const iso_url_base = 'https://' + window.location.host + '/ipxe_builds/' + build_id;
            if (action === 'download_iso') {
                const download_url = iso_url_base + '/ipxe.iso';
                download_a_file(download_url, 'ipxe.iso');
            }
            if (action === 'download_iso_nomenu') {
                const download_url = iso_url_base + '/ipxe-nomenu.iso';
                download_a_file(download_url, 'ipxe-nomenu.iso');
            }
            if (action === 'delete') {
                APICall('delete_ipxe_build', {build_id: build_id}, function(returnitem) {
                    console.log(returnitem);
                });
            }
        },
        item_icon_chooser: function(entry) {
            return {icon: 'folder', color: 'blue-grey'};
        },
    };
    helper_fancylist(fancy_list_props, 'ipxe_builds', {});
}

function main_body_tab_stage1_files_populate() {
    const fancy_list_props = {
        parent_div: 'main-body-content-tab-stage1_files-table-wrapper',
        header_titles: ['File Name', 'Last Modified'],
        prop_names: ['filename', 'modified'],
        item_buttons: [
            {'action': 'edit', 'item_prop_arg': 'filename', 'material_icon': 'create', 'tooltip': 'Edit this stage1 file'},
            {'action': 'delete', 'item_prop_arg': 'filename', 'material_icon': 'delete', 'tooltip': 'Delete this stage1 file'},
        ],
        item_button_click: function(action, filename) {
            console.log('you clicked ' + action + ' for stage1 file: ' + filename);
            if (action === 'delete') {
                APICall('delete_stage1_file', {filename: filename}, function(returnitem) {
                    console.log(returnitem);
                });
            }
            if (action === 'edit') {
                APICall('get_file', {file_name: filename, file_category: 'stage1_files'}, function(returnitem) {
                    console.log(returnitem);
                    show_modal_fileeditor(returnitem);
                });
            }
        },
        item_icon_chooser: function(entry) {
            return {icon: 'description', color: 'blue-grey'};
        },
    };
    helper_fancylist(fancy_list_props, 'stage1_files', {});
}

function main_body_tab_stage4_populate() {
    const fancy_list_props = {
        parent_div: 'main-body-content-tab-stage4-table-wrapper',
        header_titles: ['Script Name', 'Last Modified'],
        prop_names: ['filename', 'modified'],
        item_buttons: [
            {'action': 'edit', 'item_prop_arg': 'filename', 'material_icon': 'create', 'tooltip': 'Edit this stage4 script'},
            {'action': 'delete', 'item_prop_arg': 'filename', 'material_icon': 'delete', 'tooltip': 'Delete this stage4 script'},
        ],
        item_button_click: function(action, filename) {
            console.log('you clicked ' + action + ' for stage4 script: ' + filename);
            if (action === 'delete') {
                APICall('delete_stage4', {filename: filename}, function(returnitem) {
                    console.log(returnitem);
                });
            }
            if (action === 'edit') {
                APICall('get_file', {file_name: filename, file_category: 'stage4'}, function(returnitem) {
                    console.log(returnitem);
                    show_modal_fileeditor(returnitem);
                });
            }
        },
        item_icon_chooser: function(entry) {
            return {icon: 'description', color: 'blue-grey'};
        },
    };
    helper_fancylist(fancy_list_props, 'stage4', {});
}

function main_body_tab_wimboot_builds_populate() {
    const fancy_list_props = {
        parent_div: 'main-body-content-tab-wimboot_builds-table-wrapper',
        header_titles: ['Name', 'Commit ID', 'Architecture', 'Build Timestamp', 'Comment'],
        prop_names: ['name', 'commit_id', 'arch', 'build_timestamp', 'comment'],
        item_buttons: [
            // {'action': 'edit',   'item_prop_arg': 'build_id', 'material_icon': 'create', 'tooltip': 'Edit this wimboot build'},
            {'action': 'delete', 'item_prop_arg': 'build_id', 'material_icon': 'delete', 'tooltip': 'Delete this wimboot build'},
            {'action': 'download_file', 'item_prop_arg': 'build_id', 'material_icon': 'file_download', 'tooltip': 'Download this wimboot build'},
        ],
        item_button_click: function(action, build_id) {
            console.log('you clicked ' + action + ' for wimboot build with id: ' + build_id);
            const iso_url_base = 'https://' + window.location.host + '/wimboot_builds/' + build_id;
            if (action === 'download_file') {
                const download_url = iso_url_base + '/wimboot';
                download_a_file(download_url, 'wimboot');
            }
            if (action === 'delete') {
                APICall('delete_wimboot_build', {build_id: build_id}, function(returnitem) {
                    console.log(returnitem);
                });
            }
        },
        item_icon_chooser: function(entry) {
            return {icon: 'folder', color: 'blue-grey'};
        },
    };
    helper_fancylist(fancy_list_props, 'wimboot_builds', {});
}

function main_body_tab_uboot_scripts_populate() {
    const fancy_list_props = {
        parent_div: 'main-body-content-tab-uboot_scripts-table-wrapper',
        header_titles: ['File Name', 'Last Modified'],
        prop_names: ['filename', 'modified'],
        item_buttons: [
            {'action': 'edit', 'item_prop_arg': 'filename', 'material_icon': 'create', 'tooltip': 'Edit this u-boot script'},
            {'action': 'delete', 'item_prop_arg': 'filename', 'material_icon': 'delete', 'tooltip': 'Delete this u-boot script'},
        ],
        item_button_click: function(action, filename) {
            console.log('you clicked ' + action + ' for uboot script: ' + filename);
            if (action === 'delete') {
                APICall('delete_uboot_script', {filename: filename}, function(returnitem) {
                    console.log(returnitem);
                });
            }
            if (action === 'edit') {
                APICall('get_file', {file_name: filename, file_category: 'uboot_scripts'}, function(returnitem) {
                    console.log(returnitem);
                    show_modal_fileeditor(returnitem);
                });
            }
        },
        item_icon_chooser: function(entry) {
            return {icon: 'description', color: 'blue-grey'};
        },
    };
    helper_fancylist(fancy_list_props, 'uboot_scripts', {});
}

// TODO all the filename-modified-description populate functions can be reduced to populate_tab_datasource_files(datasourcename)

function main_body_tab_iso_populate() {
    const fancy_list_props = {
        parent_div: 'main-body-content-tab-iso-table-wrapper',
        header_titles: ['File Name', 'Last Modified'],
        prop_names: ['filename', 'modified'],
        item_buttons: [
            {'action': 'delete', 'item_prop_arg': 'filename', 'material_icon': 'delete', 'tooltip': 'Delete this iso file'},
        ],
        item_button_click: function(action, filename) {
            console.log('you clicked ' + action + ' for iso: ' + filename);
            if (action === 'delete') {
                APICall('delete_iso', {filename: filename}, function(returnitem) {
                    console.log(returnitem);
                });
            }
        },
        item_icon_chooser: function(entry) {
            return {icon: 'description', color: 'blue-grey'};
        },
    };
    helper_fancylist(fancy_list_props, 'iso', {});
}

function main_body_tab_tftp_root_populate() {
    const fancy_list_props = {
        parent_div: 'main-body-content-tab-tftp_root-table-wrapper',
        header_titles: ['File Name', 'Last Modified', 'Description'],
        prop_names: ['filename', 'modified', 'description'],
        item_buttons: [
            {'action': 'delete', 'item_prop_arg': 'filename', 'material_icon': 'delete', 'tooltip': 'Delete this tftp file'},
        ],
        item_button_click: function(action, filename) {
            console.log('you clicked ' + action + ' for iso: ' + filename);
        },
        item_icon_chooser: function(entry) {
            return {icon: 'description', color: 'blue-grey'};
        },
    };
    helper_fancylist(fancy_list_props, 'tftp_root', {});
}

// other


function create_task(task_type, task_payload={}) {
    APICall('create_task', {
        task_type: task_type,
        task_payload: task_payload,
    }, function(response) {
        console.info('created a task');
    });
}


function subscribe_to_datasource(data_source_name, on_change) {
    console.info('subscribing to data source: ' + data_source_name);
    const anon_thing = new NSDataSource(MQTT_CLIENT, data_source_name, null, function(value, static_data) {
        on_change(value, static_data);
    });
}

// DataSourceTables
function setup_tasks_table() {
    const table_config = {
        target_div_id: 'main-tasklist',
        data_source_name: 'tasks',
        header_height: 10,
        item_height: 10,
        headers: {
            // task_id: {
            //     width: 10,
            //     display: 'Task ID',
            // },
            task_name: {
                width: 20,
                display: 'Name',
            },
            task_description: {
                width: 20,
                display: 'Description',
            },
            // task_type: {
            //     width: 10,
            //     display: 'Task Type',
            // },
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
            // task_current_subtask: {
            //    width: 10,
            //    display: 'Current Subtask',
            // },
            buttons: {
                width: 10,
                display: 'Actions',
                buttons: [
                    {
                        id: 'log',
                        text: 'Log',
                        tooltip: 'View log file',
                        icon: 'description',
                        enable_key: 'task_status', // check value of this key to decide if this button is visible/enabled
                        enable_status: [ // values of key above where button should be visible/enabled
                            'Starting',
                            'Running',
                            'Stopping',
                            'Complete',
                            'Failed',
                        ],
                    },
                    {
                        id: 'stop',
                        text: 'Stop',
                        tooltip: 'Stop this task',
                        icon: 'stop',
                        enable_key: 'task_status',
                        enable_status: [
                            'Starting',
                            'Running',
                        ],
                    },
                    {
                        id: 'retry',
                        text: 'Retry',
                        tooltip: 'Retry this task',
                        icon: 'undo',
                        enable_key: 'task_status',
                        enable_status: [
                            'Failed',
                        ],
                    },
                    {
                        id: 'clear',
                        text: 'Clear',
                        tooltip: 'Clear this task',
                        icon: 'delete_forever',
                        enable_key: 'task_status',
                        enable_status: [
                            'Complete',
                            'Failed',
                        ],
                    },
                ],
            },
        },
        filter_function: function(entry) {
            // entry = {
            //     'task_id': self.task_id,
            //     'task_name': self.task_name,
            //     'task_description': self.task_description,
            //     'task_type': self.task_type,
            //     'task_status': status,
            //     'task_progress': progress,
            //     'task_progress_description': description,
            //     'task_current_subtask': self.current_subtask_name,
            //     'task_subtask_descriptions': self.subtask_descriptions
            // }
            entry.task_progress += '%'; // percent sign is what tells NSDataSourceTable to create a progress bar
            return entry;
        },
        button_function: function(action, task_id) {
            // console.info('You clicked the ' + action + ' button for item ' + task_id);
            if (action === 'stop' || action === 'clear') {
                // console.info('calling task_action ' + action);
                APICall('task_action', {task_id: task_id, action: action}, function(returnitem) {
                    console.log(returnitem);
                });
            } else if (action === 'log') {
                // console.info('calling task_action ' + action);
                APICall('task_action', {task_id: task_id, action: 'log'}, function(returnitem) {
                    show_modal_logviewer(returnitem);
                });
            } else if (action === 'retry') {
                console.log('retrying not implemented yet');
                // TODO get original task payload, then open the appropriate task wizard populated with that data, let user change it, then submit new task with new payload
                //   problem: we dont have original payload stored anyhere right now, may need to create an endpoint to get that from the task object in the index
                //     or simpler to track all tasks locally in a global object, pop them on successful clear?
                // APICall('task_action', {task_id: task_id, action: 'retry'}, function(returnitem){
                //   console.log(returnitem);
                // })
            }
        },
    };
    const dst = new NSDataSourceTable(table_config);
}

function setup_clients_table() {
    // client.state.state
    const table_config = {
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
    };
    const dst = new NSDataSourceTable(table_config);
}
