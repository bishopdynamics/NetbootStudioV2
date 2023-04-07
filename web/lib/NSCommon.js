// utility functions


function navigate_to_url(url) {
    // abstraction, so that we can change approach later if desired
    window.location.href = url;
}

function download_a_file(url, filename) {
    // given url and filename, cause that url to be downloaded as that filename, as if the user had clicked a link
    const link = document.createElement('a');
    link.setAttribute('download', filename);
    link.href = url;
    document.body.appendChild(link);
    link.click();
    link.remove();
}

function uuid4() {
    // generate a uuid4 string for use as ids
    // matches format used in backend
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        // const r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

/**
 * check if string is valid json
 * @param  {string} str
 * @return {boolean}
 */
function validateJSON(str) {
    try {
        JSON.parse(str);
    } catch (e) {
        return false;
    }
    return true;
}

/**
 * turn a string into Camelcase
 * @param  {string} str
 * @return {string} new string
 */
function camelCase(str) {
    return str.replace(/(\w)(\w*)/g,
        function(g0, g1, g2) {
            return g1.toUpperCase() + g2.toLowerCase();
        });
}

/**
 * returns an array of strings, corresponding to the first level key names in given object
 * @param  {object} thisobject
 * @return {Array} an array of key names
 */
function getKeyNames(thisobject) {
    // returns an array of strings, corresponding to the first level key names in given object
    const options = [];
    for (const key in thisobject) {
        if (Object.prototype.hasOwnProperty.call(thisobject, key)) {
            options.push(key);
        }
    }
    return options;
}

/**
 * sets the selected option of a select element, by option value
 * @param  {HTMLSelectElement} select_element
 * @param   {Object} value
 */
function setSelectBoxByValue(select_element, value) {
    let found_option = false;
    for (let i = 0; i < select_element.options.length; ++i) {
        if (select_element.options[i].value === value) {
            select_element.options[i].selected = true;
            found_option = true;
        }
    }
    if (found_option !== true) {
        // if we cant find that option, just select the first one
        console.warn('could not find option with value: ' + value + ', defaulting to first option')
        select_element.options[0].selected = true;
    }
}
// get index from value name
function getSelectBoxOptionIndexFromValue(select_element, value) {
    let found_value = null;
    if (select_element.options !== null) {
        if (select_element.options.length > 0) {
            for (let i = 0; i < select_element.options.length; ++i) {
                if (select_element.options[i].value === value) {
                    found_value = i;
                    break;
                }
            }
        }
    }
    return found_value;
}

// strip slashes from input string
function strip_slashes(inputstring) {
    return inputstring.replaceAll('/', '').replaceAll('\\', '');
}

// find the first data source in register and return it
function getDataSourceByName(data_source_name) {
    let found_data_source = null;
    DATA_SOURCE_REGISTER.forEach(function(data_source) {
        if (data_source['name'] === data_source_name) {
            found_data_source = data_source['object'];
        }
    });
    return found_data_source;
}

class NSMessage {
    // common message format for http, websocket, and mqtt messages
    // if this came from the broker via a topic, that gets set within the message, otherwise it is blank and you must set it yourself
    constructor(_msg=null) {
        this._data = null;
        if (_msg !== null) {
            this.from_json(_msg)
        } else {
            this._data = {
                'id': String(uuid4()),
                'sender': 'Unknown',
                'origin': null,
                'target': 'all',
                'topic': null,
                'content': {},
            }
        }
    }
    to_json() {
        let _string = '';
        try {
            _string = JSON.stringify(this._data)
        } catch (ex) {
            console.error('Exception while dumping NSMessage to json: ' + ex);
            _string = '';
        }
        return _string;
    }
    from_json(_json) {
        let _parsed = {};
        try {
            _parsed = JSON.parse(_json);
        } catch (ex) {
            console.error('Exception while parsing NSMessage from json: ' + ex);
            _parsed = {};
        }
        this._data = _parsed;
    }

    set_key(key, value) {
        if (key === 'id') {
            console.error('Cannot change the id of a message!');
        } else {
            try {
                this._data[key] = value;
            } catch (ex) {
                console.error('Exception while setting key: ' + key + ', ex: ' + ex);
            }
        }
    }
    get_key(key) {
        let _value = null;
        try {
            _value = this._data[key];
        } catch (ex) {
            console.error('Exception while getting key: ' + key + ', ex: ' + ex);
            _value = null;
        }
        return _value;
    }
}
