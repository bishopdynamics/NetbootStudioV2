// NSDataSourceTable - create and maintain a table from a Data Source

class NSDataSourceTable {
	constructor(table_config) {
		this.target_div_id = table_config.target_div_id;
		this.target_div = document.getElementById(this.target_div_id);
		this.table_config = table_config;
		this.filter_function = table_config.filter_function;
		this.instance_id = 'DataSourceTable_' + uuid4();
		if(this.target_div === null) {
			console.error('target div with id: ' + this.target_div + ' does not exist!');
		}
		else {
			this.setup();
		}
	}

	setup() {
		console.log('setting up an NSDataSourceTable for:' + this.table_config.data_source_name);
		this.target_div.innerHTML = '';  // just in case, clean it out
		// create everything we can ahead of time
		this.container = document.createElement('div');  // everything goes in this, we attach this to the target div
		this.container.height = '100%';
		// create the header first
		this.header_div = document.createElement('div');  // for holding our header which is static
		this.header_div.style.position = 'sticky';
		this.header_div.style.top = '0';
		this.header_div['z-index'] = 1;
		this.header_table = document.createElement('table');  // header lives in its own table
		this.header = document.createElement('thead');
		this.header.classList.add('blue-grey');
		this.header.classList.add('lighten-3');
		this.header_row = document.createElement('tr');
		for (const [keyname, keyconfig] of Object.entries(this.table_config.headers)) {
			let some_td = document.createElement('td');
			some_td.textContent = keyconfig.display;
			some_td.style.width = keyconfig.width + '%';
			this.header_row.appendChild(some_td);
		}
		this.header_row.style.height = this.table_config.header_height;
		this.header.appendChild(this.header_row);
		this.header_table.appendChild(this.header);
		this.header_div.appendChild(this.header_table);
		// now lets create the rows div
		this.rows_div = document.createElement('div');  // rows go inside here, and this can scroll
		this.rows_div.position = 'relative';
		this.rows_div.style.left = '5px';
		this.rows_div.style.right = '5px';
		// this.rows_div.style.height = '100%';
		this.rows_div.style['overflow-y'] = 'scroll';
		this.rows_table = document.createElement('table');  // this is the actual table where rows go
		this.rows_table.classList.add('striped');
		this.rows_table.classList.add('blue-grey');
		this.rows_table.classList.add('lighten-5');
		this.rows_div.appendChild(this.rows_table);
		this.container.appendChild(this.header_div);
		this.container.appendChild(this.rows_div);
		this.target_div.appendChild(this.container);
		this.rows_div.style.height = (this.target_div.clientHeight - this.table_config.header_height) - 68 + 'px';
		this.data_source = new NSDataSource(MQTT_CLIENT, this.table_config.data_source_name, {owner_object: this}, function(value, static_data) {
			console.log(static_data.owner_object.instance_id + ' tied to "' + static_data.owner_object.table_config.data_source_name + '" has an updated value');
			static_data.owner_object.handle_data_source_change(value, static_data);
		});
	}

	handle_data_source_change(value, static_data) {
		// render the rows for the table from scratch every time
		try {
			static_data.owner_object.rows_table.innerHTML = '';  // wipe out the rows table completely
			if (value.length > 0) {
				value.forEach(function(entry, index) {
					let newentry = static_data.owner_object.filter_function(value[index]);
					static_data.owner_object.create_row(newentry, static_data.owner_object);
				});
			}
		} catch(ex) {
			console.error('error in handle_data_source_change: ', ex);
		}
	}

	create_row(item_data, owner_object) {
		console.log('createrow: ', item_data);
		try {
			let new_row = document.createElement('tr');
			for (const [keyname, config] of Object.entries(owner_object.table_config.headers)) {
				let keyvalue = item_data[keyname];
				let new_td = document.createElement('td');
				if (typeof keyvalue === 'string') {
					if (keyvalue.endsWith('%')) {
						// if the value is a string ending in percent sign, presume it is a progress percentage and turn it into a progress bar
						let progress = Number(keyvalue.replace('%', ''));
						let progressbar = document.createElement('div');
						progressbar.classList.add('progress');
						progressbar.classList.add('tasklist-progressbar');
						let progressbar_inner = document.createElement('div');
						if (progress > 0) {
							progressbar_inner.classList.add('determinate');
							progressbar_inner.style.width = progress + '%';
						} else {
							progressbar_inner.classList.add('indeterminate');
						}
						progressbar.style.height = '10px';
						progressbar.appendChild(progressbar_inner);
						new_td.appendChild(progressbar);
					} else {
						new_td.textContent = keyvalue;
					}
				} else {
					new_td.textContent = JSON.stringify(keyvalue);
				}
				new_td.style.width = config.width + '%';
				new_row.appendChild(new_td);
			}
			this.rows_table.appendChild(new_row);
		} catch(ex) {
			console.error('error in create_row: ', ex);
		}
	}
}
