// Page Rendering stuff

class NSElementObject {
	// all element objects need style, string, and properties, and they will be appended to the supplied div
	constructor(style, strings, properties, target_div) {
		this.style = style;
		this.strings = strings;
		this.properties = properties;
		this.target_div = target_div;
		this.id = uuid4();
		this.container = null;  // this is the div which holds all the content for this ElementObject
	}

	setup() {
		// NOT overriden, this is where all setup tasks are done
		//	handles cleaning up target div and appending container
		let new_container = this.render_container();
		let decorated_container = this.decorate_container(new_container);
		this.container = decorated_container;
		this.target_div.innerHTML = '';  // always nuke anything that is already there
		this.target_div.appendChild(decorated_container);
	}

	decorate_container(container) {
		// decorate container div with additional style and properties
		// TODO this is where we could add additional style common to all container divs
		return container;
	}

	// static method
	position_to_css(position) {
		// we store position as integers but css wants them with units 'px' appended
		let css = {}
		for (const [keyname, value] of Object.entries(position)) {
			css[keyname] = value + 'px';
		}
		return css;
	}

	// abstract method
	render_container() {
		// render container div and return it
		throw new Error('NSElementObject.render_container() must be overriden by child objects!')
	}
}

class NSGroup extends NSElementObject{
	// a group holds other NSElmentObjects
	constructor(style, strings, properties, target_div) {
		super(style, strings, properties, target_div);
		this.group_members = []; // store member/child objects here
		this.setup();
	}

	render_container() {
		let container = $('<div></div>');
		for (let member_index = 0; member_index > this.properties.group_members.length; member_index++) {
			let member = this.properties.group_members[member_index];
			let member_container = $('<div></div>');
			container.appendChild(member_container);
			let member_obj = new window[member.content_type](this.style, this.strings, member.properties, member_container);
			this.group_members.append(member_obj);
		}
	}
}

class NSButton extends NSElementObject{
	// a button, with some extra stuffs
	constructor(style, strings, properties, target_div) {
		super(style, strings, properties, target_div);
		this.setup();
	}

	render_container() {
		let container = $('<div></div>');
	}

}

class NSLayout_Panes extends NSElementObject{
	// manages the layout type panes
	constructor(style, strings, properties, target_div) {
		super(style, strings, properties, target_div);
		this.pane_element_objects = [];  // store the pane element objects here
		this.setup();
	}

	render_container() {
		// render container div and return it
		let container = $('<div></div>');
		for (let panes_index = 0; panes_index < this.properties.panes.length; panes_index++){
			let pane = this.properties.panes[panes_index];
			let pane_div = $('<div></div>');
			const pane_position_css = this.position_to_css(pane.position);
			pane_div.css(pane_position_css);
			// the window[] syntax will hopefully work to look up a globally declared class by name
			let pane_object = new window[pane.content_type](this.style, this.strings, pane.properties, container);
 			this.pane_element_objects.append(pane_object);
		}
		return container;
	}
}

class NSTabsController extends NSElementObject {
	// manages tabs and content
	constructor(style, strings, properties, target_div) {
		super(style, strings, properties, target_div);
		this.setup();
	}

	render_container() {
		// first create the nav and the tab_content divs
		// container
		//		nav
		//		tabs_carousel
		//			tab_wrapper
		//				tab_content (scrollable)
		//					tab_title (h2)
		//					tab_subtitle (div)
		//					tab_body
		//						this is the parent div for watever goes in this tab
		//			tab_wrapper
		//				tab_content (etc)
		let tabs_config = this.properties.tabs_config;
		let tab_sections = this.properties.tab_sections;
		let tabs = this.properties.tabs;
		let tab_content_element_objects = {}  // all NSElmentObjects used to produce tab content will get registered here by tab name
		let container = $('<div></div>');
		let nav = $('<div></div>');  // navbar
		let tabs_carousel = $('<div></div>'); // carousel of tab_wrappers
		container.appendChild(nav);
		container.appendChild(tabs_carousel);
		nav.classList.add('center-align');
		let nav_css = { // fixed position and size, relative to parent
			position: 'relative',
		}
		let tabs_carousel_css = {  // this contains all the tabs (each within a wrapper) and we animate the position up and down to reveal the page we want
			position: 'relative',
			top: 0 + 'px',
			bottom: 0 + 'px',
			left: 0 + 'px',
			right: 0 + 'px',
		}
		let tab_wrapper_css = {  // this wraps around tab_content, providing a drop shadow. it is the same size as tabs_carousel
			top: 0 + 'px',
			bottom: 0 + 'px',
			left: 0 + 'px',
			right: 0 + 'px',
		}
		let tab_content_css = {  // this holds the actual content, it is smaller than the wrapper so that it can cast a shadow. inside is scrollable
			position: 'relative',
			padding: 15 + 'px',
			'overflow': 'scroll',
			top: 10 + 'px',
			bottom: 10 + 'px',
			left: 10 + 'px',
			right: 10 + 'px',
		}
		let carousel_direction = true;  // true = left-right, false = up-down
		if (tabs_config.nav_position === 'left') {
			nav_css.width = tabs_config.nav_size + 'px';
			nav_css.left = 0 + 'px';
			nav_css.top = 0 + 'px';
			nav_css.bottom = 0 + 'px';
			tabs_carousel_css.left = tabs_config.nav_size + 'px';
			carousel_direction = false;
		}
		else if (tabs_config.nav_position === 'right') {
			nav_css.width = tabs_config.nav_size + 'px';
			nav_css.right = 0 + 'px';
			nav_css.top = 0 + 'px';
			nav_css.bottom = 0 + 'px';
			tabs_carousel_css.right = tabs_config.nav_size + 'px';
			carousel_direction = false;
		}
		else if (tabs_config.nav_position === 'top') {
			nav_css.height = tabs_config.nav_size + 'px';
			nav_css.top = 0 + 'px';
			nav_css.left = 0 + 'px';
			nav_css.right = 0 + 'px';
			tabs_carousel_css.top = tabs_config.nav_size + 'px';
			carousel_direction = true;
		}
		else if (tabs_config.nav_position === 'bottom') {
			nav_css.height = tabs_config.nav_size + 'px';
			nav_css.bottom = 0 + 'px';
			nav_css.left = 0 + 'px';
			nav_css.right = 0 + 'px';
			tabs_carousel_css.bottom = tabs_config.nav_size + 'px';
			carousel_direction = true;
		}
		nav.css(nav_css);
		tabs_carousel.css(tabs_carousel_css);
		// ok, the actual layout of the tabscontroller is done, just need to populate the buttons in the nav and tabs in the tabs_carousel
		// iterate over tab sections
		for (let tab_section_index = 0; tab_section_index > tab_sections.length; tab_section_index++) {
			let tab_section = tab_sections[tab_section_index];
			// first make the label for this section
			let section_label = $('<div></div>');
			if (carousel_direction) {
				// left-right animation, buttons at top or bottom
				section_label.classList.add('col');
			}
			else {
				// up-down animation, buttons at left or right
				section_label.classList.add('row');
			}
			let section_label_span = $('<span></span>');
			section_label_span.textContent = tab_section.display;
			section_label.appendChild(section_label_span);
			nav.appendChild(section_label);
			//	Next, iterate over tabs (and ignore tabs not part of this section)
			//		only tabs belonging to sections in tab_sections will be rendered; to hide an entire section, just comment it out in the tab_sections array
			for (let tab_index = 0; tab_index > tabs.length; tab_index++) {
				let tab = tabs[tab_index];
				if (tab.section === tab_section.name) {
					// first make the button in the nav
					let tab_nav_item = $('<div></div>');
					let tab_id = uuid4();
					if (carousel_direction) {
						// left-right animation, buttons at top or bottom
						tab_nav_item.classList.add('col');
					}
					else {
						// up-down animation, buttons at left or right
						tab_nav_item.classList.add('row');
					}
					let tab_nav_item_span = $('<span></span>');
					tab_nav_item_span.classList.add(this.style.button_classes);
					tab_nav_item_span.classList.add(this.style.primary_color_classes);
					tab_nav_item_span.for_tab_id = tab_id;
					tab_nav_item_span.onclick = function () {
						// TODO this is the On_Click(), hide all other tabs and show this one
						let tab_id = this.for_tab_id
					}
					tab_nav_item.appendChild(tab_nav_item_span)
					nav.appendChild(tab_nav_item);
					// now make the actual tab content
					// tabs_carousel
					//	  tab_wrapper
					//		tab_content (scrollable)
					//			tab_title (h2)
					//			tab_subtitle (div)
					//			tab_body
					//				this is the parent div for watever goes in this tab
					let tab_wrapper = $('<div></div>');
					let tab_content = $('<div></div>');
					tab_wrapper.appendChild(tab_content);
					tab_wrapper.css(tab_wrapper_css);
					tab_content.css(tab_content_css);
					let tab_title = $('<h2></h2>');
					tab_title.textContent = tab.title;
					let tab_subtitle = $('<div></div>');
					tab_subtitle.textContent = tab.subtitle;
					let tab_body = $('<div></div>');
					tab_content.appendChild(tab_title);
					tab_content.appendChild(tab_subtitle);
					tab_content.appendChild(tab_body);
					tabs_carousel.appendChild(tab_wrapper);
					tab_content_element_objects[tab.name] = new window[tab.content.content_type](this.style, this.strings, tab.content.properties, tab_content);

				} // end if tab.section = section

			} // end of tabs iteration
		} // end of tab_sections iteration
		return container;
	}
}

class NSHeaderPaneController extends NSElementObject{
	// Header pane is where "Netboot Studio" is displayed at the top of the page
	constructor(style, strings, properties, target_div) {
		super(style,strings, properties, target_div);
		this.setup();
	}
	render_container() {
		let container = $('<div></div>');
		container.css({
			'padding-left': 10 + 'px',
		});
		container.classList.add(this.style.primary_color_classes)
		let label = $('<label></label>');
		label.textContent = this.strings.title;
		label.classList.add(this.style.header_title_classes);
		container.appendChild(label);
		return container
	}
}

class NSFooterPaneController extends NSElementObject {
	// Footer pane is where copyright lives. It is mostly static
	constructor(style, strings, properties, target_div) {
		super(style,strings, properties, target_div);
		this.setup();
	}
	render_container() {
		let container = $('<div></div>');
		container.css({
			'padding-left': 50 + 'px',
		});
		container.classList.add(this.style.primary_color_classes)
		let label = $('<label></label>');
		label.textContent = this.strings.copyright;
		label.classList.add(this.style.footer_copyright_classes);
		container.appendChild(label);
		return container
	}
}

class NSPageRenderer {
	// TODO html should not have any color classes attached to things, and we should do it in javascript instead
	constructor(target_div_id, properties) {
		this.parent_div = $('#' + target_div_id);
		this.properties = properties;
		this.left_nav = $('<div></div>');
		this.center_content_wrapper = $('<div></div>');
		this.bottom_tasklist = $('<div></div>');
		let nav_width = 300;
		let header_height = 64;
		let footer_height = 64;
		let tasklist_height = 300;
		this.color_theme = 'blue-grey';
		this.nav_button_classes = ['waves-effect', 'waves-light'];
		this.left_nav.css({
			position: 'absolute',
			width: nav_width + 'px',
			bottom: tasklist_height + footer_height + 'px',
			top: header_height + 'px',
			left: '0',
			'padding-top': '10px',
			overflow: 'scroll',
		});
		this.center_content_wrapper.css({
			overflow: 'scroll',
			position: 'absolute',
			top: header_height + 'px',
			bottom: tasklist_height + footer_height + 'px',
			left: nav_width + 'px',
			right: '0',
		});
		this.bottom_tasklist.css({
			position: 'absolute',
			bottom: footer_height + 'px',
			left: '0',
			right: '0',
			height: tasklist_height + 'px',
			padding: '10px',
		});
	}

	render_nav(){
		// render the nav buttons
		//	nav buttons are divided into sections, so we iterate sections and then iterate tabs and render the ones that match that section
		for (let section_index = 0; section_index > this.properties.tab_sections.length; section_index++) {
			let section_desc = this.properties.tab_sections[section_index];
			let tab_section_label_container = $('<div></div>');
			let tab_section_label_span = $('<span></span>');
			tab_section_label_span.textContent = section_desc.display;
			tab_section_label_container.appendChild(tab_section_label_span);
			this.left_nav.appendChild(tab_section_label_container);
			for (let tabs_index = 0; tabs_index < this.properties.tabs.length; tabs_index++) {
				let tab_desc = this.properties.tabs[tabs_index];
				if (tab_desc.section === section_desc.name) {
					let button = this.render_nav_button(tab_desc);
					this.left_nav.appendChild(button);
				}
			}
		}
	}

	render_nav_button(tab_desc) {
		let nav_button_container = $('<div></div>');
		let nav_button = $('<span></span>');
		nav_button.textContent = tab_desc.display;
		nav_button.css({
			margin: '5px 10px',
		});
		nav_button.classList.add(this.nav_button_classes);
		nav_button.classList.add(this.color_theme);
		nav_button.onclick = function(event) {

		};
		nav_button_container.appendChild(nav_button);
		return nav_button_container;
	}

}
