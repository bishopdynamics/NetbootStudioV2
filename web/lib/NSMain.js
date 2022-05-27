// these functions are specific to the Main page

// linter options
//@ts-check 
/*jshint esversion: 6 */

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

// TODO this hack is to make testing easier on my mac pro
let URL_BROKER = null;
if (window.location.hostname === "jamess-mac-pro"){
	URL_BROKER = 'wss://' + 'james-netboot' + ':' + BROKER_PORT + '';
} else {
	URL_BROKER = 'wss://' + window.location.hostname + ':' + BROKER_PORT + '';
}

// const URL_WEBSERVER = 'https://' + window.location.hostname + ':' + WEBSERVER_PORT;

// https://materializecss.com/modals.html
const MODAL_SELECTOR = '#common-modal';  // querySelector to get modal div
let MODAL = null; // this will hold our modal instance
let MODAL_VISIBLE = false; // track visibility of modal
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
let MODAL_WIZARD_INPUTS = {}  // track input elements here so we can retrieve values
let MODAL_M_INSTANCES = [] // store instances of Materialize things, so they can be cleaned up
let MODAL_METADATA = {}  // stores metadata for use by callbacks of modal buttons
let MODAL_CURRENT_PAGE = 0 // stores the current page on modal
let MODAL_PAGES = []  // stores all the pages
let MODAL_NUM_PAGES = 1 // stores how many pages the modal has

let FANCYLIST_M_INSTANCES = {} // stores dictionary of instances of Materialize things, so they can be cleaned up

let MQTT_CLIENT = null;
let REQUEST_REGISTER = {}; // requests are stored here by id, alond with reference to callback

let DATA_SOURCE_REGISTER = [];  // data sources are stored here

// all the tab names, so we can iterate over them
const MAIN_ALL_TABNAMES = [ 'ipxe_builds', 'stage1_files', 'stage4', 'boot_images', 'unattended_configs', 'clients', 'client_status', 'uboot_scripts', 'iso', 'wimboot_builds', 'tftp_root', 'settings', 'debugging'];

// https://materializecss.com/tooltips.html
const TOOLTIP_OPTIONS = {
	exitDelay: 300,
	enterDelay: 300,
	margin: 5,
	inDuration: 500,
	outDuration: 200,
	transitionMovement: 15
};

function onPageReady(){
    // this is run at DOMContentLoaded
    console.log('onPageReady');
    try{
        M.AutoInit();
		let footer_copyright = document.getElementById('footer-copyright');
		footer_copyright.textContent = COPYRIGHT_STRING;
        document.getElementById('user_password').addEventListener('keyup', function(event){
            // this is so hitting enter in the password field causes form submit
            // older browsers dont support event.code, old way is event.keyCode === 13
            if(event.code === 'Enter'){
                document.getElementById('submit_button').click();
            }
        });
        RenewAuthToken().then(
            function(value){
                onAuth(value);
            },
            function(error){
                console.error(error);
            }
        );
    } catch(e) {
        console.warn('onPageReady had unexpected exception');
    }
}

document.addEventListener('DOMContentLoaded', onPageReady);

function SetupMQTTClient(){
	let client = null;
	let client_id = "NSWebUI-Browser-" + uuid4();
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
			password: BROKER_PASSWORD
		};
		client = mqtt.connect(URL_BROKER, options);
		client.on('reconnect', function(error){
            console.warn('Reconnected connection to broker: ' + URL_BROKER + ', error: ' + error);
        });
		client.on('connect', function(context) {
            console.info('Connected to broker: ' + URL_BROKER);
            // console.info('mqtt client context:' + JSON.stringify(context));
        });
		client.on('error', function(error){
            console.error('An error ocurred with MQTT Client: ' + error);
        });
		client.on('message', function(topic, message){
            // console.info('A message has arrived on topic: ' + topic + ', message: ' + message);
            if(topic === 'api_response') {
                try {
                    let ns_message = new NSMessage(message);
                    let content = ns_message.get_key('content');
                    if (content.id in REQUEST_REGISTER) {
                        REQUEST_REGISTER[content.id](content.api_payload.result);  // pass result to callback
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
	} catch(e) {
		console.error('failed to setup mqtt client ( ' + URL_BROKER + ' ): ' + e);
	}
	return client;
}

function main_page_default_state(){
	// set all the things to their default state for a fresh page load
	MODAL = M.Modal.init(document.querySelectorAll(MODAL_SELECTOR), MODAL_OPTIONS)[0];
	MQTT_CLIENT = SetupMQTTClient();
	setup_clients_table();
	setup_tasks_table();
	main_body_nav_onclick('clients');
}

function ShowUploadStatus(file_id, file_name, status, progress, description){
	// TODO upload status spams task status topic, which causes updates to tasks pane to get backed up, and makes the upload look like it takes longer than it does
	//		in practice, this only really matters with local testing
	const mqtt_topic = 'NetbootStudio/TaskStatus';
	try {
		let subtask = 'uploading_file';
		if (status === 'Complete') {
			subtask = '';
		}
		let message = {
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
			}
		}
		const message_json = JSON.stringify(message);
		MQTT_CLIENT.publish(mqtt_topic, message_json);
	} catch (ex) {
		console.error('exception while ShowUploadStatus: ' + ex);
	}
}


// Tabs

// TODO we can run the populate commands on page load (and show loading thing til done) and then just show and hide the tabs

function main_body_nav_onclick(tabname){
	// when a tab button is clicked, hide all others and show given one
	try {
		main_body_nav_hide_all();
		main_body_nav_show_tab(tabname);
		let elems = document.querySelectorAll('.modal');
		let options = {
			opacity: 0.5,
			dismissible: true,
		};
		let instances = M.Modal.init(elems, options);
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

function main_body_nav_hide_all(){
	// hide all tabs
	try {
		let i;
		for (i = 0; i < MAIN_ALL_TABNAMES.length; i++) {
			let tabname = MAIN_ALL_TABNAMES[i];
			main_body_nav_hide_tab(tabname);
		}
	} catch (ex) {
		console.error('exception while main_body_nav_hide_all: ' + ex);
	}
}

function main_body_nav_hide_tab(tabname){
	// hide a tab
	let tabelement = document.getElementById('main-body-content-tab-' + tabname);
	tabelement.style.display = 'none';
}

function main_body_nav_show_tab(tabname){
	// show a tab
	try {
		let tabelement = document.getElementById('main-body-content-tab-' + tabname);
		tabelement.style.display = 'block';
	} catch (ex) {
		console.error('exception while showing a tab: ' + ex);
	}
}

// populating tabs

// let fancy_list_props = {
// 		parent_div: '',
// 		header_titles: [],
// 		value_names: [],
// 		prop_names: [],
// 		item_buttons: [],
// 		item_button_click: null,
// 		item_icon_chooser: function (entry) {
// 			return {icon: 'description', color:'blue-grey'};
// 		}
// 	}

// TODO these two can be collapsed into a common populate_tab_builds(datasourcename) situation

function main_body_tab_clients_populate(){
	// TODO removed info because show/hide doesnt work
	let fancy_list_props = {
		parent_div: 'main-body-content-tab-clients-table-wrapper',
		header_titles: ['Hostname', 'MAC Address', 'IP Address', 'Architecture', 'Config'],
		prop_names: ['hostname', 'mac', 'ip', 'arch', 'config'],
		// header_titles: ['Hostname', 'MAC Address', 'IP Address', 'Architecture', 'Config', 'State', 'Information'],
		// prop_names: ['hostname', 'mac', 'ip', 'arch', 'config', 'state', 'info'],
		item_buttons: [
			{'action': 'edit',   'item_prop_arg': 'mac', 'material_icon': 'create', 'tooltip': 'Edit this client\'s config'},
			{'action': 'delete', 'item_prop_arg': 'mac', 'material_icon': 'delete', 'tooltip': 'Delete this client'},
		],
		item_button_click: function(action, client_mac){
			console.log('you clicked ' + action + ' for client with mac: ' + client_mac);
			if (action === 'edit') {
				show_modal_editclient(client_mac);
			}
			if (action === 'delete') {
				APICall('delete_client', {mac: client_mac}, function(returnitem){
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
			return {icon: 'dns', color:'blue-grey'};
		}
	}
	helper_fancylist(fancy_list_props, 'clients', {});
}

function main_body_tab_boot_images_populate(){
	let fancy_list_props = {
		parent_div: 'main-body-content-tab-boot_images-table-wrapper',
		header_titles: ['Name', 'Created', 'Image Type', 'Architecture', 'Description'],
		prop_names: ['boot_image_name', 'created', 'image_type', 'arch', 'description'],
		item_buttons: [
			// {'action': 'edit',   'item_prop_arg': 'boot_image_name', 'material_icon': 'create', 'tooltip': 'Edit this boot image'},
			{'action': 'delete', 'item_prop_arg': 'boot_image_name', 'material_icon': 'delete', 'tooltip': 'Delete this boot image'},
		],
		item_button_click: function(action, name){
			console.log('you clicked ' + action + ' for boot image with name: ' + name);
			if (action === 'delete') {
				APICall('delete_boot_image', {name: name}, function(returnitem){
					console.log(returnitem);
				})
			}
		},
		item_icon_chooser: function (entry) {
			return {icon: 'description', color:'blue-grey'};
		}
	}
	helper_fancylist(fancy_list_props, 'boot_images', {})
}

function main_body_tab_unattended_configs_populate(){
	let fancy_list_props = {
		parent_div: 'main-body-content-tab-unattended_configs-table-wrapper',
		header_titles: ['File Name', 'Last Modified'],
		prop_names: ['filename', 'modified'],
		item_buttons: [
			// {'action': 'edit',   'item_prop_arg': 'filename', 'material_icon': 'create', 'tooltip': 'edit this unatteded config'},
			{'action': 'delete', 'item_prop_arg': 'filename', 'material_icon': 'delete', 'tooltip': 'Delete this unattended config'},
		],
		item_button_click: function(action, filename){
			console.log('you clicked ' + action + ' for unattended config file: ' + filename);
			if (action === 'delete') {
				APICall('delete_unattended_config', {filename: filename}, function(returnitem){
					console.log(returnitem);
				})
			}
		},
		item_icon_chooser: function (entry) {
			return {icon: 'description', color:'blue-grey'};
		}
	}
	helper_fancylist(fancy_list_props, 'unattended_configs', {})
}


function main_body_tab_ipxe_builds_populate(){
	let fancy_list_props = {
		parent_div: 'main-body-content-tab-ipxe_builds-table-wrapper',
		header_titles: ['Name', 'Commit ID', 'Architecture', 'Build Timestamp', 'Embedded Stage1', 'Comment'],
		prop_names: ['build_name', 'commit_id', 'arch', 'build_timestamp', 'stage1', 'comment'],
		item_buttons: [
			// {'action': 'edit',   'item_prop_arg': 'build_id', 'material_icon': 'create', 'tooltip': 'Edit this ipxe build'},
			{'action': 'delete', 'item_prop_arg': 'build_id', 'material_icon': 'delete', 'tooltip': 'Delete this ipxe build'},
			{'action': 'download_iso', 'item_prop_arg': 'build_id', 'material_icon': 'file_download', 'tooltip': 'Download ipxe.iso'},
			{'action': 'download_iso_nomenu', 'item_prop_arg': 'build_id', 'material_icon': 'file_download', 'tooltip': 'Download ipxe-nomenu.iso without stage1 embedded'},
		],
		item_button_click: function(action, build_id){
			console.log('you clicked ' + action + ' for ipxe build with id: ' + build_id);
			let iso_url_base = 'https://' + window.location.host + '/ipxe_builds/' + build_id
			if (action	=== 'download_iso'){
				let download_url = iso_url_base + '/ipxe.iso';
				download_a_file(download_url, 'ipxe.iso')
			}
			if (action	=== 'download_iso_nomenu'){
				let download_url = iso_url_base + '/ipxe-nomenu.iso';
				download_a_file(download_url, 'ipxe-nomenu.iso')
			}
			if (action === 'delete') {
				APICall('delete_ipxe_build', {build_id: build_id}, function(returnitem){
					console.log(returnitem);
				})
			}
		},
		item_icon_chooser: function (entry) {
			return {icon: 'folder', color:'blue-grey'};
		}
	}
	helper_fancylist(fancy_list_props, 'ipxe_builds', {})
}

function main_body_tab_stage1_files_populate(){
	let fancy_list_props = {
		parent_div: 'main-body-content-tab-stage1_files-table-wrapper',
		header_titles: ['File Name', 'Last Modified'],
		prop_names: ['filename', 'modified'],
		item_buttons: [
			// {'action': 'edit', 'item_prop_arg': 'filename', 'material_icon': 'create', 'tooltip': 'Edit this stage1 file'},
			{'action': 'delete', 'item_prop_arg': 'filename', 'material_icon': 'delete', 'tooltip': 'Delete this stage1 file'},
		],
		item_button_click: function(action, filename){
			console.log('you clicked ' + action + ' for stage1 file: ' + filename);
			if (action === 'delete') {
				APICall('delete_stage1_file', {filename: filename}, function(returnitem){
					console.log(returnitem);
				})
			}
		},
		item_icon_chooser: function (entry){
				return {icon: 'description', color:'blue-grey'};
		},
	}
	helper_fancylist(fancy_list_props, 'stage1_files', {})
}

function main_body_tab_stage4_populate(){
	let fancy_list_props = {
		parent_div: 'main-body-content-tab-stage4-table-wrapper',
		header_titles: ['Script Name', 'Last Modified'],
		prop_names: ['filename', 'modified'],
		item_buttons: [
			// {'action': 'edit', 'item_prop_arg': 'filename', 'material_icon': 'create', 'tooltip': 'Edit this stage4 script'},
			{'action': 'delete', 'item_prop_arg': 'filename', 'material_icon': 'delete', 'tooltip': 'Delete this stage4 script'},
		],
		item_button_click: function(action, filename){
			console.log('you clicked ' + action + ' for stage4 script: ' + filename);
			if (action === 'delete') {
				APICall('delete_stage4', {filename: filename}, function(returnitem){
					console.log(returnitem);
				})
			}
		},
		item_icon_chooser: function (entry){
				return {icon: 'description', color:'blue-grey'};
		},
	}
	helper_fancylist(fancy_list_props, 'stage4', {})
}


function main_body_tab_wimboot_builds_populate(){
	let fancy_list_props = {
		parent_div: 'main-body-content-tab-wimboot_builds-table-wrapper',
		header_titles: ['Name', 'Commit ID', 'Architecture', 'Build Timestamp', 'Comment'],
		prop_names: ['name', 'commit_id', 'arch', 'build_timestamp', 'comment'],
		item_buttons: [
			// {'action': 'edit',   'item_prop_arg': 'build_id', 'material_icon': 'create', 'tooltip': 'Edit this wimboot build'},
			{'action': 'delete', 'item_prop_arg': 'build_id', 'material_icon': 'delete', 'tooltip': 'Delete this wimboot build'},
			{'action': 'download_file', 'item_prop_arg': 'build_id', 'material_icon': 'file_download', 'tooltip': 'Download this wimboot build'},
		],
		item_button_click: function(action, build_id){
			console.log('you clicked ' + action + ' for wimboot build with id: ' + build_id);
			let iso_url_base = 'https://' + window.location.host + '/wimboot_builds/' + build_id
			if (action	=== 'download_file'){
				let download_url = iso_url_base + '/wimboot';
				download_a_file(download_url, 'wimboot')
			}
			if (action === 'delete') {
				APICall('delete_wimboot_build', {build_id: build_id}, function(returnitem){
					console.log(returnitem);
				})
			}
		},
		item_icon_chooser: function (entry) {
			return {icon: 'folder', color:'blue-grey'};
		}
	}
	helper_fancylist(fancy_list_props, 'wimboot_builds', {})
}

function main_body_tab_uboot_scripts_populate(){
	let fancy_list_props = {
		parent_div: 'main-body-content-tab-uboot_scripts-table-wrapper',
		header_titles: ['File Name', 'Last Modified'],
		prop_names: ['filename', 'modified'],
		item_buttons: [
			{'action': 'edit',   'item_prop_arg': 'filename', 'material_icon': 'create', 'tooltip': 'Edit this u-boot script'},
			{'action': 'delete', 'item_prop_arg': 'filename', 'material_icon': 'delete', 'tooltip': 'Delete this u-boot script'},
		],
		item_button_click: function(action, filename){
			console.log('you clicked ' + action + ' for uboot script: ' + filename);
			if (action === 'delete') {
				APICall('delete_uboot_script', {filename: filename}, function(returnitem){
					console.log(returnitem);
				})
			}
		},
		item_icon_chooser: function (entry) {
			return {icon: 'description', color:'blue-grey'};
		}
	}
	helper_fancylist(fancy_list_props, 'uboot_scripts', {})
}

// TODO all the filename-modified-description populate functions can be reduced to populate_tab_datasource_files(datasourcename)

function main_body_tab_iso_populate(){
	let fancy_list_props = {
		parent_div: 'main-body-content-tab-iso-table-wrapper',
		header_titles: ['File Name', 'Last Modified'],
		prop_names: ['filename', 'modified'],
		item_buttons: [
			{'action': 'delete', 'item_prop_arg': 'filename', 'material_icon': 'delete', 'tooltip': 'Delete this iso file'},
		],
		item_button_click: function(action, filename){
			console.log('you clicked ' + action + ' for iso: ' + filename);
			if (action === 'delete') {
				APICall('delete_iso', {filename: filename}, function(returnitem){
					console.log(returnitem);
				})
			}
		},
		item_icon_chooser: function (entry) {
			return {icon: 'description', color:'blue-grey'};
		}
	}
	helper_fancylist(fancy_list_props, 'iso', {})
}

function main_body_tab_tftp_root_populate(){
	let fancy_list_props = {
		parent_div: 'main-body-content-tab-tftp_root-table-wrapper',
		header_titles: ['File Name', 'Last Modified', 'Description'],
		prop_names: ['filename', 'modified', 'description'],
		item_buttons: [
			{'action': 'delete', 'item_prop_arg': 'filename', 'material_icon': 'delete', 'tooltip': 'Delete this tftp file'},
		],
		item_button_click: function(action, filename){
			console.log('you clicked ' + action + ' for iso: ' + filename);
		},
		item_icon_chooser: function (entry) {
			return {icon: 'description', color:'blue-grey'};
		}
	}
	helper_fancylist(fancy_list_props, 'tftp_root', {})
}

// wizards

function gen_wiz_config_newbuild(){
	return {
		title: 'New Build',
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
				type: 'select',
				options: 'ipxe_commit_ids',
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
			commit_id: 'e6f9054',
			arch: 'amd64',
			stage1_file: 'default',
			name: '',
			comment: '',
		},
		button_onclicks: {
			save: function (data) {
				create_task('build_ipxe', data);
			},
		},
	};
}

function gen_wiz_config_upload(target_path){
	return {
		title: 'Upload File',
		subtitle: 'Upload a file to: ' + target_path,
		height: 480,
		pages: 1,
		inputs: [
			{
				name: 'upload',
				label: 'Upload',
				tooltip: 'Upload a file',
				type: 'upload',
				destination: target_path
			},
		],
		metadata: {
			comment: 'these will be stored in global MODAL_METADATA so you can access them from within onclick functions later',
			target_path: target_path
		},
		data: {
			upload: '',
		},
		button_onclicks: {},
	};
}

function gen_wiz_config_editclient(client_mac, current_client_entry){
	return {
		title: 'Edit Client: ' + current_client_entry['hostname'],
		subtitle: 'IP Address: ' + current_client_entry['ip'] + ', MAC Address: ' + client_mac + ', Architecture: ' + current_client_entry['arch'],
		height: 550,
		pages: 2,
		inputs: [
			{
				name: 'uboot_script',
				label: 'u-boot script',
				tooltip: 'Select a u-boot script file',
				type: 'select',
				options: 'uboot_scripts',
				keys_display: ['filename', 'description'],
				key_value: 'filename',
				page: 1,
			},
			{
				name: 'ipxe_build',
				label: 'iPXE Build',
				tooltip: 'Select the build of iPXE to serve to this client',
				type: 'select',
				options: 'ipxe_builds',
				keys_display: ['build_name', 'arch', 'stage1'],
				key_value: 'build_id',
				page: 1,
			},
			{
				name: 'boot_image',
				label: 'Boot Image',
				tooltip: 'Select the boot image to serve to this client',
				type: 'select',
				options: 'boot_images',
				keys_display: ['boot_image_name', 'arch', 'description'],
				key_value: 'boot_image_name',
			},
			{
				name: 'boot_image_once',
				label: 'Serve this Boot Image only once?',
				tooltip: 'Should we reset this client to standby_loop after the next time it completes a boot cycle?',
				type: 'checkbox',
			},
			{
				name: 'do_unattended',
				label: 'Perform Unattended Install?',
				tooltip: 'Should this client perform an unattended installation?',
				type: 'checkbox',
			},
			{
				name: 'unattended_config',
				label: 'Unattended Config File',
				tooltip: 'Select an unattended installation config file',
				type: 'select',
				options: 'unattended_configs',
				keys_display: ['filename'],
				key_value: 'filename',
			},
			{
				name: 'stage4',
				label: 'Stage4 Script',
				tooltip: 'Select the Stage4 script to serve to this client',
				type: 'select',
				options: 'stage4',
				keys_display: ['filename'],
				key_value: 'filename',
			},
		],
		metadata: {
			comment: 'these will be stored in global MODAL_METADATA so you can access them from within onclick functions later',
			mac: client_mac,
		},
		data: current_client_entry['config'],
		button_onclicks: {
			save: function (data) {
				let payload = {
					mac: MODAL_METADATA.mac,
					config: data,
				}
				// console.info(data);
				APICall('set_client_config', payload, function (value) {
					console.debug('set client config');
				});
			},
		},
	};
}


// default_settings = {
//         'boot_image': 'standby_loop',
//         'boot_image_once': False,
//         'unattended_config': 'blank.cfg',
//         'uboot_script': 'default',
//         'do_unattended': False,
//         'ipxe_build_arm64': '',
//         'ipxe_build_amd64': '',
//         'stage4': 'none',
//     }

function gen_wiz_config_settings(current_settings){
	return {
		title: 'Settings ',
		subtitle: 'These settings affect how new clients behave by default',
		height: 850,
		pages: 2,
		inputs: [
			{
				name: 'uboot_script',
				label: 'Default u-boot script',
				tooltip: 'Select a u-boot script file to serve u-boot clients by default',
				type: 'select',
				options: 'uboot_scripts',
				keys_display: ['filename', 'description'],
				key_value: 'filename',
				page: 1,
			},
			{
				name: 'boot_image',
				label: 'Default Boot Image',
				tooltip: 'Select the boot image to serve to clients by default',
				type: 'select',
				options: 'boot_images',
				keys_display: ['boot_image_name', 'arch', 'description'],
				key_value: 'boot_image_name',
				page: 0,
			},
			{
				name: 'boot_image_once',
				label: 'By default, serve boot image once?',
				tooltip: 'By default, should we reset clients to standby_loop after it completes a boot cycle?',
				type: 'checkbox',
				page: 1,
			},
			{
				name: 'do_unattended',
				label: 'By default, perform Unattended Install?',
				tooltip: 'By default, should clients perform an unattended installation?',
				type: 'checkbox',
				page: 1,
			},
			{
				name: 'unattended_config',
				label: 'Default Unattended Config File',
				tooltip: 'Select an unattended installation config file to serve to clients by default',
				type: 'select',
				options: 'unattended_configs',
				keys_display: ['filename'],
				key_value: 'filename',
				page: 0,
			},
			{
				name: 'stage4',
				label: 'Default Stage4 Script',
				tooltip: 'Select the Stage4 script to serve to clients by default',
				type: 'select',
				options: 'stage4',
				keys_display: ['filename'],
				key_value: 'filename',
				page: 1,
			},
			{
				name: 'ipxe_build_arm64',
				label: 'Default iPXE Build for arm64',
				tooltip: 'Select the build of iPXE to serve to arm64 clients by default',
				type: 'select',
				options: 'ipxe_builds',
				keys_display: ['build_name', 'arch', 'stage1'],
				key_value: 'build_id',
				page: 0,
			},
			{
				name: 'ipxe_build_amd64',
				label: 'Default iPXE Build for amd64',
				tooltip: 'Select the build of iPXE to serve to amd64 clients by default',
				type: 'select',
				options: 'ipxe_builds',
				keys_display: ['build_name', 'arch', 'stage1'],
				key_value: 'build_id',
				page: 0,
			},
			{
				name: 'debian_mirror',
				label: 'Debian Mirror',
				tooltip: 'url to the debian mirror you want to use for clients',
				type: 'text',
				page: 0,
			},
			{
				name: 'ubuntu_mirror',
				label: 'Ubuntu Mirror',
				tooltip: 'url to the ubuntu mirror you want to use for clients',
				type: 'text',
				page: 0,
			},
		],
		metadata: {
			comment: 'these will be stored in global MODAL_METADATA so you can access them from within onclick functions later',
		},
		data: current_settings,
		button_onclicks: {
			save: function (data) {
				let payload = {
					settings: data,
				}
				// console.info(data);
				APICall('set_settings', payload, function (value) {
					console.debug('set settings');
				});
			},
		},
	};
}


function show_modal_newbuild(){
	let wizard_config = gen_wiz_config_newbuild();
	console.log(wizard_config);
	showModal_Wizard(wizard_config);
}

function show_modal_editclient(client_mac){
	APICall('get_client', {mac: client_mac}, function (client) {
		let wizard_config = gen_wiz_config_editclient(client_mac, client);
		console.log(wizard_config);
		showModal_Wizard(wizard_config);
	});
}

function show_modal_settings(){
	APICall('get_settings', {}, function (current_settings) {
		let wizard_config = gen_wiz_config_settings(current_settings);
		console.log(wizard_config);
		showModal_Wizard(wizard_config);
	});
}

function show_modal_upload(target_path){
	let wizard_config = gen_wiz_config_upload(target_path);
	console.log(wizard_config);
	showModal_Wizard(wizard_config);
}

// other


function create_task(task_type, task_payload={}){
	APICall('create_task', {
		task_type: task_type,
		task_payload: task_payload,
	}, function(response){
		console.info('created a task')
	});
}


function subscribe_to_datasource(data_source_name, on_change) {
	console.info('subscribing to data source: ' + data_source_name);
	let anon_thing = new NSDataSource(MQTT_CLIENT, data_source_name, null, function(value, static_data) {
		on_change(value, static_data);
	});
}

// DataSourceTables
function setup_tasks_table () {
	let table_config = {
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
			entry.task_progress += '%';  // percent sign is what tells NSDataSourceTable to create a progress bar
			return entry;
		}
	};
	let dst = new NSDataSourceTable(table_config);
}

function setup_clients_table() {
	//	client.state.state
	let table_config = {
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
			// 	width: 15,
			// 	display: 'Expiration',
			// },
			// state_expiration_action: {
			// 	width: 10,
			// 	display: 'Expiration Action',
			// },
		},
		filter_function: function(entry) {
			console.info('filtering: ', entry)
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
			}
		},
	};
	let dst = new NSDataSourceTable(table_config);
}
