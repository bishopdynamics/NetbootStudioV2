// FancyList
//      Generates a list from given spec, sortable by columns


function helper_fancylist(list_props, data_source_name, payload){
	try {
		let data_source_object = new NSDataSource(MQTT_CLIENT, data_source_name, null, function(value, static_data) {
			create_fancy_list(list_props, value);
		});
	} catch (e) {
		console.error('caught an exception while helper_fancylist: ', e);
	}
}

function create_fancy_list(properties, list_entries){
	let table_wrapper = document.getElementById(properties['parent_div'])
	let header_titles = properties['header_titles']
	let value_names = [];
	let prop_names = properties['prop_names']
	for (let prop_name of prop_names) {
		value_names.push('table-sort-' + prop_name);
	}
	let item_buttons = properties['item_buttons']
	let item_button_click = properties['item_button_click']
	let item_icon_chooser = properties['item_icon_chooser']
	let list_options = {
		valueNames: value_names,
	};
	try {
		// destroy any existing materializecss instances
		for (let [key, value] of Object.entries(FANCYLIST_M_INSTANCES)) {
			// console.info('destroying fancylist m instance: ' + key)
			for (let instance of value) {
				instance.destroy();
			}
		}
		FANCYLIST_M_INSTANCES = {};
		let tooltip_element_ids = [];
		let jsoneditors = [];  // store json editor details so we can activate them
		table_wrapper.innerHTML = '';
		let loading_text = document.createElement('span');
		loading_text.textContent = 'Loading...';
		table_wrapper.appendChild(loading_text);

		let button_wrapper = document.createElement('div');
		let list_element = document.createElement('ul');
		list_element.classList.add('list');
		list_element.classList.add('collection');
		// make sort buttons
		let i;
		for (i = 0; i < value_names.length; i++){
			let _title = header_titles[i];
			let _value_name = value_names[i];
			let _button = document.createElement('span');
			_button.textContent = 'Sort by ' + _title;
			_button.classList.add('sort');
			_button.classList.add('btn');
			_button.classList.add('blue-grey');
			_button.setAttribute('data-sort', _value_name);
			button_wrapper.appendChild(_button);
		}
		// make search bar
		let searchbar = document.createElement('input');
		searchbar.classList.add('search');
		searchbar.setAttribute('placeholder', 'Search');
		button_wrapper.appendChild(searchbar);
		// create the actual list
		if (list_entries.length > 0) {
			for (let entry of list_entries) {
				let _item = document.createElement('li');
				_item.classList.add('collection-item');
				_item.classList.add('avatar');
				let _icon = document.createElement('i');
				_icon.classList.add('material-icons');
				_icon.classList.add('circle');
				let _icon_look = item_icon_chooser(entry);
				_icon.textContent = _icon_look.icon;
				_icon.classList.add(_icon_look.color);
				_item.appendChild(_icon);
				let _title_wrap = document.createElement('span');
				_title_wrap.classList.add('title');
				let _title_text = document.createElement('span');
				_title_text.classList.add('table-sort-name');
				_title_wrap.appendChild(_title_text);
				_item.appendChild(_title_wrap);
				let j;
				for (j = 0; j < value_names.length; j++) {
					let propname = value_names[j];
					let _para = document.createElement('p');
					let _span = document.createElement('span');
					let propvalue = entry[prop_names[j]];
					_span.classList.add(propname);
					if (typeof propvalue === 'string') {
						_span.textContent = header_titles[j] + ": " + propvalue;
					} else if (typeof propvalue === 'object') {
						// TODO this is ghetto
						if (propname === 'table-sort-config'){
							let valuestring = '';
							if (propvalue['uboot_script'] !== 'default') {
								valuestring += propvalue['uboot_script'] + ' -> ';
							}
							valuestring += propvalue['boot_image']
							if (propvalue['boot_image'] === 'standby_loop' || propvalue['boot_image'] === 'menu') {
								valuestring += ' (built-in)';
							}
							else {
								if (propvalue['boot_image_once']) {
									valuestring += ' (once)';
								}
								if (propvalue['do_unattended']) {
									valuestring += ' -> ' + propvalue['unattended_config'];
									if (propvalue['stage4'] !== 'none') {
										valuestring += ' -> ' + propvalue['stage4'];
									}
								}
							}
							_span.textContent = header_titles[j] + ": " + valuestring;
						}
						else {
							let thing_id = uuid4();
							let label_container = document.createElement('div');
							let button_container = document.createElement('div');
							let label_span = document.createElement('label');
							label_span.textContent = header_titles[j];
							let show_button = createButton('Show');
							show_button.setAttribute('foreditor', thing_id);
							show_button.setAttribute('id', 'show-button-' + thing_id);
							let hide_button = createButton('Hide');
							hide_button.setAttribute('foreditor', thing_id);
							hide_button.setAttribute('id', 'hide-button-' + thing_id);
							let editorview = document.createElement('pre'); // editor docs say use a pre
							editorview.setAttribute('id', 'editor-' + thing_id);
							editorview.style.display = 'block';
							hide_button.style.display = 'none';
							show_button.style.display = 'none';
							const editor_desc = {
								editor_id: 'editor-' + thing_id,
								propvalue: JSON.parse(JSON.stringify(propvalue))
							}
							jsoneditors.push(editor_desc);
							label_container.appendChild(label_span);
							button_container.appendChild(show_button);
							button_container.appendChild(hide_button);
							label_container.appendChild(button_container);
							label_container.appendChild(editorview);
							_span.appendChild(label_container);
							let show_func = function (event) {
								console.info('showing editorview with id: ' + thing_id);
								let editorview = document.getElementById('editor-' + thing_id);
								let show_button = document.getElementById('show-button-' + thing_id);
								let hide_button = document.getElementById('hide-button-' + thing_id);
								editorview.style.display = 'block';
								show_button.style.display = 'none';
								hide_button.style.display = 'block';
							};
							let hide_func = function (event) {
								console.info('showing editorview with id: ' + thing_id);
								let editorview = document.getElementById('editor-' + thing_id);
								let show_button = document.getElementById('show-button-' + thing_id);
								let hide_button = document.getElementById('hide-button-' + thing_id);
								editorview.style.display = 'none';
								show_button.style.display = 'block';
								hide_button.style.display = 'none';
							};
							show_button.addEventListener('click', show_func);
							hide_button.addEventListener('click', hide_func);
						}
					} else {
						console.warn('dont know how to handle propvalue type: ' + typeof propvalue)
					}
					_para.appendChild(_span);
					_item.appendChild(_para);
				}
				let _button_container = document.createElement('div');

				for (let _button_info of item_buttons) {
					let _this_button = document.createElement('a');
					_this_button.classList.add('btn-floating');
					_this_button.classList.add('waves-effect');
					_this_button.classList.add('waves-light');
					_this_button.onclick = function () {
						item_button_click(_button_info.action, entry[_button_info.item_prop_arg]);
					};

					let _this_button_icon = document.createElement('i');
					_this_button_icon.classList.add('material-icons');
					_this_button_icon.textContent = _button_info.material_icon;
					_this_button.appendChild(_this_button_icon);
					_button_container.appendChild(_this_button);
					if (_button_info.hasOwnProperty('tooltip')) {
						let tooltip = _button_info.tooltip;
						let tooltip_id = 'tooltip_' + uuid4();
						_this_button_icon.setAttribute('id', tooltip_id);
						_this_button_icon.classList.add('tooltipped');
						_this_button_icon.setAttribute('data-position', 'right');
						_this_button_icon.setAttribute('data-tooltip', tooltip);
						tooltip_element_ids.push(tooltip_id);
					}
				}
				_item.appendChild(_button_container);
				list_element.appendChild(_item);
			}
		}
		table_wrapper.innerHTML = '';
		table_wrapper.appendChild(button_wrapper);
		table_wrapper.appendChild(list_element);
		if (list_entries.length > 0) {
			let logList = new List(table_wrapper, list_options);
			// cleanup our tooltips
			for (let jsoneditor of jsoneditors) {
				console.log('activating an editor');
				const editor_opts = {
					editable: false
				}
				const editor = new JsonEditor(document.getElementById(jsoneditor['editor_id']), jsoneditor['propvalue'], editor_opts);
			}
			for (let instance_id of tooltip_element_ids) {
				// console.log('activating tooltip instanceid: ' + instance_id);
				let instances = document.querySelectorAll('#' + instance_id);
				FANCYLIST_M_INSTANCES[instance_id] = M.Tooltip.init(instances, TOOLTIP_OPTIONS);
			}

		}

	} catch(e) {
		console.error('unexpected exception while creating fancy list: ', e);
		throw e;
	}

}
