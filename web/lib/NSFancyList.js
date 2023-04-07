// FancyList
//      Generates a list from given spec, sortable by columns

let FANCYLIST_M_INSTANCES = {}; // stores dictionary of instances of Materialize things, so they can be cleaned up

function helper_fancylist(list_props, data_source_name, payload) {
    try {
        const data_source_object = new NSDataSource(MQTT_CLIENT, data_source_name, null, function(value, static_data) {
            create_fancy_list(list_props, value);
        });
    } catch (e) {
        console.error('caught an exception while helper_fancylist: ', e);
    }
}

function create_fancy_list(properties, list_entries) {
    const table_wrapper = document.getElementById(properties['parent_div']);
    const header_titles = properties['header_titles'];
    const value_names = [];
    const prop_names = properties['prop_names'];
    for (const prop_name of prop_names) {
        value_names.push('table-sort-' + prop_name);
    }
    const item_buttons = properties['item_buttons'];
    const item_button_click = properties['item_button_click'];
    const item_icon_chooser = properties['item_icon_chooser'];
    const list_options = {
        valueNames: value_names,
    };
    try {
        // destroy any existing materializecss instances
        for (const [key, value] of Object.entries(FANCYLIST_M_INSTANCES)) {
            // console.info('destroying fancylist m instance: ' + key)
            for (const instance of value) {
                instance.destroy();
            }
        }
        FANCYLIST_M_INSTANCES = {};
        const tooltip_element_ids = [];
        const jsoneditors = []; // store json editor details so we can activate them
        table_wrapper.innerHTML = '';
        const loading_text = document.createElement('span');
        loading_text.textContent = 'Loading...';
        table_wrapper.appendChild(loading_text);

        const button_wrapper = document.createElement('div');
        const list_element = document.createElement('ul');
        list_element.classList.add('list');
        list_element.classList.add('collection');
        // make sort buttons
        let i;
        for (i = 0; i < value_names.length; i++) {
            const _title = header_titles[i];
            const _value_name = value_names[i];
            const _button = document.createElement('span');
            _button.textContent = 'Sort by ' + _title;
            _button.classList.add('sort');
            _button.classList.add('btn');
            _button.classList.add('blue-grey');
            _button.setAttribute('data-sort', _value_name);
            button_wrapper.appendChild(_button);
        }
        // make search bar
        const searchbar = document.createElement('input');
        searchbar.classList.add('search');
        searchbar.setAttribute('placeholder', 'Search');
        button_wrapper.appendChild(searchbar);
        // create the actual list
        if (list_entries.length > 0) {
            for (const entry of list_entries) {
                const _item = document.createElement('li');
                _item.classList.add('collection-item');
                _item.classList.add('avatar');
                const _icon = document.createElement('i');
                _icon.classList.add('material-icons');
                _icon.classList.add('circle');
                const _icon_look = item_icon_chooser(entry);
                _icon.textContent = _icon_look.icon;
                _icon.classList.add(_icon_look.color);
                _item.appendChild(_icon);
                const _title_wrap = document.createElement('span');
                _title_wrap.classList.add('title');
                const _title_text = document.createElement('span');
                _title_text.classList.add('table-sort-name');
                _title_wrap.appendChild(_title_text);
                _item.appendChild(_title_wrap);
                let j;
                for (j = 0; j < value_names.length; j++) {
                    const propname = value_names[j];
                    const _para = document.createElement('p');
                    const _span = document.createElement('span');
                    const propvalue = entry[prop_names[j]];
                    _span.classList.add(propname);
                    if (typeof propvalue === 'string') {
                        _span.textContent = header_titles[j] + ': ' + propvalue;
                    } else if (typeof propvalue === 'object') {
                        // TODO this is ghetto
                        if (propname === 'table-sort-config') {
                            let valuestring = '';
                            if (propvalue['uboot_script'] !== 'default') {
                                valuestring += propvalue['uboot_script'] + ' -> ';
                            }
                            valuestring += propvalue['boot_image'];
                            if (propvalue['boot_image'] === 'standby_loop' || propvalue['boot_image'] === 'menu') {
                                valuestring += ' (built-in)';
                            } else {
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
                            _span.textContent = header_titles[j] + ': ' + valuestring;
                        } else {
                            const thing_id = uuid4();
                            const label_container = document.createElement('div');
                            const button_container = document.createElement('div');
                            const label_span = document.createElement('label');
                            label_span.textContent = header_titles[j];
                            const show_button = createButton('Show');
                            show_button.setAttribute('foreditor', thing_id);
                            show_button.setAttribute('id', 'show-button-' + thing_id);
                            const hide_button = createButton('Hide');
                            hide_button.setAttribute('foreditor', thing_id);
                            hide_button.setAttribute('id', 'hide-button-' + thing_id);
                            const editorview = document.createElement('pre'); // editor docs say use a pre
                            editorview.setAttribute('id', 'editor-' + thing_id);
                            editorview.style.display = 'block';
                            hide_button.style.display = 'none';
                            show_button.style.display = 'none';
                            const editor_desc = {
                                editor_id: 'editor-' + thing_id,
                                propvalue: JSON.parse(JSON.stringify(propvalue)),
                            };
                            jsoneditors.push(editor_desc);
                            label_container.appendChild(label_span);
                            button_container.appendChild(show_button);
                            button_container.appendChild(hide_button);
                            label_container.appendChild(button_container);
                            label_container.appendChild(editorview);
                            _span.appendChild(label_container);
                            const show_func = function(event) {
                                console.info('showing editorview with id: ' + thing_id);
                                const editorview = document.getElementById('editor-' + thing_id);
                                const show_button = document.getElementById('show-button-' + thing_id);
                                const hide_button = document.getElementById('hide-button-' + thing_id);
                                editorview.style.display = 'block';
                                show_button.style.display = 'none';
                                hide_button.style.display = 'block';
                            };
                            const hide_func = function(event) {
                                console.info('showing editorview with id: ' + thing_id);
                                const editorview = document.getElementById('editor-' + thing_id);
                                const show_button = document.getElementById('show-button-' + thing_id);
                                const hide_button = document.getElementById('hide-button-' + thing_id);
                                editorview.style.display = 'none';
                                show_button.style.display = 'block';
                                hide_button.style.display = 'none';
                            };
                            show_button.addEventListener('click', show_func);
                            hide_button.addEventListener('click', hide_func);
                        }
                    } else {
                        console.warn('dont know how to handle propvalue type: ' + typeof propvalue);
                    }
                    _para.appendChild(_span);
                    _item.appendChild(_para);
                }
                const _button_container = document.createElement('div');

                for (const _button_info of item_buttons) {
                    const _this_button = document.createElement('a');
                    _this_button.classList.add('btn-floating');
                    _this_button.classList.add('waves-effect');
                    _this_button.classList.add('waves-light');
                    _this_button.onclick = function() {
                        item_button_click(_button_info.action, entry[_button_info.item_prop_arg]);
                    };

                    const _this_button_icon = document.createElement('i');
                    _this_button_icon.classList.add('material-icons');
                    _this_button_icon.textContent = _button_info.material_icon;
                    _this_button.appendChild(_this_button_icon);
                    _button_container.appendChild(_this_button);
                    if (_button_info.hasOwnProperty('tooltip')) {
                        const tooltip = _button_info.tooltip;
                        const tooltip_id = 'tooltip_' + uuid4();
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
            const logList = new List(table_wrapper, list_options);
            // cleanup our tooltips
            for (const jsoneditor of jsoneditors) {
                console.log('activating an editor');
                const editor_opts = {
                    editable: false,
                };
                const editor = new JsonEditor(document.getElementById(jsoneditor['editor_id']), jsoneditor['propvalue'], editor_opts);
            }
            for (const instance_id of tooltip_element_ids) {
                // console.log('activating tooltip instanceid: ' + instance_id);
                const instances = document.querySelectorAll('#' + instance_id);
                FANCYLIST_M_INSTANCES[instance_id] = M.Tooltip.init(instances, TOOLTIP_OPTIONS);
            }
        }
    } catch (e) {
        console.error('unexpected exception while creating fancy list: ', e);
        throw e;
    }
}
