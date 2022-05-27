// NSModal
//      manage the pop-up modal


function change_modal_page(pagenum) {
	let page_carousel = $('#modal-page-carousel');
	let nextbutton = document.getElementById('modal-next-button');
	let prevbutton = document.getElementById('modal-prev-button');
	let page_width = 1000;  // TODO this should be a global var somewhere else
	console.log('showing page: ' + pagenum);
	page_carousel.animate({
		left:  ((page_width * pagenum) * -1 ) + 'px',
	});
	MODAL_CURRENT_PAGE = pagenum;
	if (MODAL_CURRENT_PAGE === 0) {
		// first page, hide previous button
		prevbutton.classList.add('disabled');
		// prevbutton.style.display = 'none';
	} else {
		prevbutton.classList.remove('disabled');
		// prevbutton.style.display =  'inline-block';
	}
	if (MODAL_CURRENT_PAGE === MODAL_NUM_PAGES - 1) {
		// last page, hide next button
		nextbutton.classList.add('disabled');
		// nextbutton.style.display = 'none';
	} else {
		nextbutton.classList.remove('disabled');
		// nextbutton.style.display = 'inline-block';
	}
}

function next_modal_page() {
	let newpage = MODAL_CURRENT_PAGE + 1;
	change_modal_page(newpage);
}

function prev_modal_page() {
	let newpage = MODAL_CURRENT_PAGE - 1;
	change_modal_page(newpage);
}

function showModal_Wizard(wizard_config){
	try {
		console.info('showing wizard modal');
		MODAL_VISIBLE = true;
		MODAL.open();
		let modal_div = document.querySelector('#common-modal');
		let modal_content_div = document.querySelector('#common-modal-content');
		let title = document.querySelector('#modal-title');
		let subtitle = document.querySelector('#modal-subtitle');
		let content = document.querySelector('#modal-content');
		let footer = document.querySelector('#modal-footer');
		// store metadata
		MODAL_METADATA = wizard_config.metadata;
		MODAL_NUM_PAGES = wizard_config.pages;
		// setup title and subtitle
		title.textContent = wizard_config['title'];
		subtitle.textContent = wizard_config['subtitle'];
		// populate buttons
		let cancel_button = createButton('Cancel');
		cancel_button.setAttribute('id', 'modal-cancel-button');
		cancel_button.style.margin = '5px';
		cancel_button.addEventListener('click', function() {
			hideModal();
		});
		footer.appendChild(cancel_button);
		if (MODAL_NUM_PAGES > 1) {
			// we have more than one page, show the prev and next buttons
			let prevbutton = createButton('Back');
			prevbutton.setAttribute('id', 'modal-prev-button')
			prevbutton.setAttribute('title', 'go to previous page')
			prevbutton.style.margin = '5px';
			let nextbutton = createButton('Next');
			nextbutton.setAttribute('id', 'modal-next-button')
			nextbutton.setAttribute('title', 'go to next page')
			nextbutton.style.margin = '5px';
			if (MODAL_CURRENT_PAGE === 0) {
				// first page, hide previous button
				prevbutton.classList.add('disabled');
				// prevbutton.style.display = 'none';
			}
			if (MODAL_CURRENT_PAGE === MODAL_NUM_PAGES - 1) {
				// last page, hide next button
				nextbutton.classList.add('disabled');
				// nextbutton.style.display = 'inline-block';
			}
			nextbutton.addEventListener('click', function(event){
				next_modal_page();
			})
			prevbutton.addEventListener('click', function(event) {
				prev_modal_page();
			})
			footer.appendChild(prevbutton);
			footer.appendChild(nextbutton);
			let paddingspan = document.createElement('span');
			paddingspan.style.width = '30px';
			footer.appendChild(paddingspan);
		}
		// only add a save button if wizard_config provided an onclick for it
		if(wizard_config.button_onclicks.hasOwnProperty('save')){
			let save_button = createButton('Save');
			save_button.setAttribute('id', 'modal-save-button');
			save_button.style.margin = '5px';
			save_button.addEventListener('click', function () {
				let data = {};
				wizard_config.inputs.forEach(function (input_desc) {
					if (input_desc.type === 'select' || input_desc.type === 'text') {
						data[input_desc.name] = MODAL_WIZARD_INPUTS[input_desc.name].value;
					} else if (input_desc.type === 'checkbox') {
						data[input_desc.name] = MODAL_WIZARD_INPUTS[input_desc.name].checked;
					} else {
						console.error('dont know how to get value from input_desc.type: ' + input_desc.type);
					}
				})
				wizard_config.button_onclicks.save(data);
				hideModal();
			});
			footer.appendChild(save_button);
		}
		// generate the actual form
		let content_width = 1000;
		let modal_content_div_width = 1020;
		let modal_div_width = 1040;
		let content_top_pad = 30;  // space between subtitle and content
		content.style['overflow-y'] = 'hidden';
		content.style['overflow-x'] = 'hidden';
		content.style.height = wizard_config.height + 'px';
		content.style.width = content_width + 'px';
		modal_content_div.style.width = modal_content_div_width + 'px';
		modal_div.style.width = modal_div_width + 'px';
		// NOTE flex-container on carousel, and flex-child on pages, with pages flex =1.
		//	with this, pages occupy equal-sized columns left to right within carousel
		//	only set width of the carousel to match number of pages, flex takes care of the rest
		//    https://coder-coder.com/display-divs-side-by-side/
		let page_carousel = document.createElement('div');
		page_carousel.setAttribute('id', 'modal-page-carousel')
		page_carousel.style.width = (MODAL_NUM_PAGES * content_width) + 'px';
		page_carousel.classList.add('flex-container')
		page_carousel.style.display = 'flex';
		page_carousel.style.position = 'relative';
		page_carousel.style.top = content_top_pad + 'px';
		page_carousel.style.left = '0px';
		page_carousel.style.margin = '0px';
		page_carousel.style.padding = '0px';
		for (let page_number = 0; page_number < MODAL_NUM_PAGES; page_number++) {
			console.log('creating page: '+ page_number);
			let page_div = document.createElement('div');
			page_div.setAttribute('id', 'modal_page_' + page_number);
			page_div.classList.add('modal-page');
			page_div.classList.add('flex-child')
			page_div.style['overflow-x'] = 'scroll';
			page_div.style.flex = '1';
			page_div.style.position = 'relative';
			page_div.style.top = '0px';
			page_div.style.padding = '0px';
			page_div.style.margin = '0px';
			page_carousel.appendChild(page_div);
			MODAL_PAGES.push(page_div);
		}
		content.appendChild(page_carousel);
		wizard_config.inputs.forEach(function (input_desc) {
			let page_number = 0;  // inputs without page number default to page 0
			let page_div = null;  // handle for this page div
			try {
				if (wizard_config.data.hasOwnProperty(input_desc.name)) {
					if (input_desc.hasOwnProperty('page')) {
						page_number = input_desc.page;
					}
					page_div = document.getElementById('modal_page_' + page_number);
					const inputdiv = document.createElement('div');
					const label = document.createElement('label');
					label.textContent = input_desc.label;
					let input = null;
					let input_id = input_desc.name + '_' + uuid4();
					if (input_desc.type === 'select') {
						// select needs to log its instances so they can be cleaned up
						// selects are populated by a data source
						input = document.createElement('select');
						input_desc['input_element'] = input;
						input_desc['input_element_id'] = input_id;
						let data_source_object = new NSDataSource(MQTT_CLIENT, input_desc.options, input_desc, function (data_source_value, input_desc) {
							let input = input_desc['input_element']
							let should_update_selection = true;
							input.setAttribute('id', input_id);
							input.setAttribute('title', input_desc.tooltip);
							// first remove any options no longer in data source value
							if (input.options !== null) {
								if (input.options.length > 0) {
									// only update selection if we started out with zero options
									should_update_selection = false;
									Array.from(input.options).forEach(function (option_element) {
										let ok_to_keep = false;
										data_source_value.forEach(function (option_desc) {
											if (option_element.value === option_desc[input_desc.key_value]) {
												ok_to_keep = true;
											}
										});
										if (ok_to_keep === false) {
											let existing_option_index = getSelectBoxOptionIndexFromValue(input, option_element.value);
											if (input.options[existing_option_index].selected) {
												should_update_selection = true;  // we removed the selected option, lets hope the current value can be selected
											}
											input.remove(existing_option_index);
										}
									});
								}
							}
							data_source_value.forEach(function (option_desc) {
								const existing_option_index = getSelectBoxOptionIndexFromValue(input, option_desc[input_desc.key_value]);
								let option;
								if (existing_option_index != null) {
									// already exists lets update details
									let existing_option_index = getSelectBoxOptionIndexFromValue(input, option_desc[input_desc.key_value])
									option = input.options[existing_option_index];
								} else {
									// this option does not already exist
									option = document.createElement('option');
								}
								option.value = option_desc[input_desc.key_value];
								let option_display = '';
								let item_num = 0;
								input_desc.keys_display.forEach(function (keyname) {
									// we want it like this: thing1 [ thing2 - thing3 thingN ]
									item_num++;
									if (item_num === 1) {
										//	this is thing1
										option_display = option_desc[keyname];
									} else if (item_num === 2) {
										// this is thing2
										if (item_num === input_desc.keys_display.length) {
											// also the last item
											option_display += ' [ ' + option_desc[keyname] + ' ]';
										} else {
											// not last item tho
											option_display += ' [ ' + option_desc[keyname];
										}

									} else if (item_num === input_desc.keys_display.length) {
										// this is the last thing
										option_display += ', ' + option_desc[keyname] + ' ]';
									} else {
										// this is thing3 - thing(N-1)
										option_display += ', ' + option_desc[keyname];
									}
								})
								option.textContent = option_display;
								if (existing_option_index === null) {
									input.add(option);
								}
							});
							if (should_update_selection) {
								setSelectBoxByValue(input, wizard_config.data[input_desc.name]);
							}
							let select_elems = document.querySelectorAll('#' + input_desc['input_element_id']);
							try {
								console.info('initializing select instance named: ' + input_desc.name);
								MODAL_M_INSTANCES[input_desc.name] = M.FormSelect.init(select_elems)[0];
							} catch (e) {
								console.error('error while init select instance named: ' + input_desc.name + ' , :' + e);
							}
						});

						inputdiv.appendChild(input);
						inputdiv.appendChild(label);
						inputdiv.classList.add('input-field');
						page_div.appendChild(inputdiv);
					}
					else if (input_desc.type === 'checkbox') {
						//	checkbox needs to be wrapped inside a label, with a span acting as the internal label element
						//		also remember the checkbox needs 30px padding or it will render on top of other things
						input = document.createElement('input');
						input.setAttribute('type', 'checkbox');
						input.setAttribute('id', input_id);
						input.classList.add('filled-in');
						let checkvalue = true;
						checkvalue = wizard_config.data[input_desc.name] === 'true' || wizard_config.data[input_desc.name] === 'True' || wizard_config.data[input_desc.name] === true;
						// just setting the checked attribute will not fire the change event, instead call .click() if the value isnt already what you want it to be
						// https://stackoverflow.com/questions/8206565/check-uncheck-checkbox-with-javascript
						if (input.checked !== checkvalue) {
							input.click();
						}
						input.setAttribute('title', input_desc.tooltip);
						const checkboxwrapper = document.createElement('label');
						const checkboxlabel = document.createElement('span');
						checkboxlabel.setAttribute('for', input_id);
						checkboxlabel.textContent = input_desc.label;
						checkboxwrapper.appendChild(input)
						checkboxwrapper.appendChild(checkboxlabel)
						inputdiv.appendChild(checkboxwrapper);
						inputdiv.style.padding = '30px';
						inputdiv.classList.add('input-field');
						page_div.appendChild(inputdiv);
					}
					else if (input_desc.type === 'text') {
						input = document.createElement('input');
						input.setAttribute('type', 'text');
						input.setAttribute('id', input_id);
						input.value = wizard_config.data[input_desc.name];
						const textlabel = document.createElement('label');
						textlabel.setAttribute('for', input_id);
						textlabel.textContent = input_desc.label;
						inputdiv.appendChild(input);
						inputdiv.appendChild(textlabel);
						inputdiv.classList.add('input-field');
						page_div.appendChild(inputdiv);
					}
					else if (input_desc.type === 'upload') {
						// input is needed for rest of logic, but with uplaoder it wont actually appended to any parent object
						input = document.createElement('input');
						input.setAttribute('id', input_id);
						let uploader_id = 'uploader_' + uuid4();
						let upload_div = document.createElement('div');
						upload_div.setAttribute('id', uploader_id);
						inputdiv.appendChild(upload_div);
						page_div.appendChild(inputdiv);
						SetupUploader(uploader_id, input_desc.destination, function (file_id, file_name, status, progress, description) {
							ShowUploadStatus(file_id, file_name, status, progress, description);
						});
					}
					else {
						console.error('dont know how to render input of type: ' + input_desc.type);
					}
					MODAL_WIZARD_INPUTS[input_desc.name] = input;
					const inter_input_padding_div = document.createElement('div');
					inter_input_padding_div.style.height = '7px';
					page_div.appendChild(inter_input_padding_div);
				}
				else {
					console.error('found input description for:' + input_desc.name + ' but no corresponding key in data');
				}
			} catch (e) {
				console.error('unexpected exception while creating wizard inputs: ' + e);
			}
		})
		M.updateTextFields();  // this fixes labels overlapping content on dynamically generated text input fields
	} catch (ex) {
		console.error('exception while showing modal: ', ex);
	}
}

function hideModal(){
	// hide the modal, clearing its content and footer
	console.info('hiding the modal');
	MODAL.close();
	MODAL_VISIBLE = false;
	MODAL_M_INSTANCES.forEach(function (instance){
		// clean up any Materialize instances
		try {
			instance.destroy();
		} catch (ex) {
			console.warn('error while destroying an m instance: ', ex);
		}

	})
	let content = document.querySelector('#modal-content')
	let footer = document.querySelector('#modal-footer')
	content.innerHTML = '';
	footer.innerHTML = '';
	MODAL_M_INSTANCES = [];
	MODAL_WIZARD_INPUTS = {};
	MODAL_PAGES = [];
	MODAL_CURRENT_PAGE = 0;
	MODAL_NUM_PAGES = 1;
}
