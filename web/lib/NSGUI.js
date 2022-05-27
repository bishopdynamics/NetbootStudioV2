/* eslint-disable max-len, no-unused-vars*/
/*
    Netboot Studio GUI helper functions
*/

/**
 * create a button
 * class is form-node-button
 * @param  {String} name
 * @return {Element} an a tag
 */
function createButton(name){
  let this_button = document.createElement('a');
  this_button.href = '#!';
  this_button.textContent = String(name);
  this_button.classList.add('modal-close');
  this_button.classList.add('waves-effect');
  this_button.classList.add('blue-grey');
  this_button.classList.add('btn-flat');
  this_button.classList.add('form-node-button');
  return this_button;
}

/**
 * create a span to be used as a label, with text Camelcase
 * class is form-node-label
 * @param  {text} name
 * @return {Element} a span element
 */
function createLabel(name) {
  const labeltext = camelCase(name);
  const label = document.createElement('span');
  label.classList.add('form-node-label');
  label.innerHTML = labeltext;
  return label;
}

/**
 * create a checkbox with the given value
 * class is form-node-input
 * @param  {boolean} value
 * @return {Element} a checkbox element
 */
function createCheckbox(value) {
  const checkbox_uuid = uuid4();
  const label = document.createElement('label');
  label.setAttribute('for', checkbox_uuid)
  const input = document.createElement('input');
  input.setAttribute('type', 'checkbox');
  input.setAttribute('id', checkbox_uuid);
  input.checked = value;
  input.enabled = true;
  input.classList.add('form-node-input');
  input.classList.add('filled-in');
  label.appendChild(input);
  return input;
}

/**
 * create a number input with the given value
 * class is form-node-input
 * @param  {number} value
 * @return {Element} a number input element
 */
function createNumberInput(value) {
  const input = document.createElement('input');
  input.setAttribute('type', 'number');
  input.value = value;
  input.classList.add('form-node-input');
  return input;
}

/**
 * create a text input with the given value
 * class is form-node-input
 * @param  {string} value
 * @return {Element} a text input element
 */
function createTextInput(value) {
  const input = document.createElement('input');
  input.setAttribute('type', 'text');
  input.setAttribute('value', value);
  input.classList.add('form-node-input');
  return input;
}

/**
 * given a datatree populated with input elements, build the actual table
 * @param  {object} datatree
 * @return {Element} a table with all the input elements
 */
function renderDataTree(datatree) {
  const table = document.createElement('table');
  try {
    for (const key in datatree) {
      if (Object.prototype.hasOwnProperty.call(datatree, key)) {
        const row = document.createElement('tr');
        const labeltd = document.createElement('td');
        const inputtd = document.createElement('td');
        const labelelem = createLabel(key);
        labeltd.appendChild(labelelem);
        let inputelem = null;
        if (datatree[key] instanceof Element) {
          inputelem = datatree[key];
        } else {
          inputelem = renderDataTree(datatree[key]);
        }
        inputtd.appendChild(inputelem);
        row.appendChild(labeltd);
        row.appendChild(inputtd);
        table.appendChild(row);
      }
    }
  } catch (e) {
    console.error('exception while renderDataTree: ' + e);
  }
  return table;
}

/**
 * create a tree of input elements based on the values of keys in an object
 * @param  {object} inputobject the object to base it on
 * @param  {object} datatree optional existing datatree to add things to, used for recursion
 * @return {Element} a table row
 */
function buildDataTree(inputobject, datatree = null) {
  if (datatree === null) {
    datatree = JSON.parse(JSON.stringify(inputobject)); // making a deep copy so we can change it independently
  }
  try {
    for (const key in inputobject) {
      if (Object.prototype.hasOwnProperty.call(inputobject, key)) {
        const value = inputobject[key];
        let input = null;
        if (typeof value == 'boolean') {
          input = createCheckbox(value);
          datatree[key] = input;
        } else if (typeof value == 'number') {
          input = createNumberInput(value);
          datatree[key] = input;
        } else if (typeof value == 'string') {
          input = createTextInput(value);
          datatree[key] = input;
        } else if (typeof value == 'object') {
          datatree[key] = buildDataTree(value, datatree[key]);
        }
      }
    }
  } catch (e) {
    console.error('exception while buildDataTree: ' + e);
  }
  return datatree;
}

/**
 * update an the given object's values from the input elements in the datatree
 * datatree and object must have the exact same structure
 * @param  {object} inputdatatree the tree holding input elements
 * @param  {object} _object optional existing object to build upon, used for recursion
 * @return {object} object with updated values
 */
function objectFromDatatree(inputdatatree, _object = null) {
  let object = _object;
  if (object == null) {
    object = {};
  }
  const table = document.createElement('table');
  try {
    for (const key in inputdatatree) {
      if (Object.prototype.hasOwnProperty.call(inputdatatree, key)) {
        if (inputdatatree[key] instanceof Element) {
          if (inputdatatree[key].type == 'checkbox') {
            // this is a checkbox
            object[key] = inputdatatree[key].checked;
          } else if (inputdatatree[key].type == 'number') {
            // this is a number input
            object[key] = Number(inputdatatree[key].value);
          } else {
            // hopefully this is an input element that has a value property
            object[key] = inputdatatree[key].value;
          }
        } else {
          object[key] = {};
          objectFromDatatree(inputdatatree[key], object[key]);
        }
      }
    }
  } catch (e) {
    console.error('exception while updateObjectFromDatatree: ' + e);
  }
  return object;
}


/**
 * create a drop-down given the array of options and a value indicated the selected option
 * @param  {Array} options
 * @param  {any} value
 * @return {Element} a select element
 */
function renderSelect(options, value) {
  // return a selectbox using the given list of options, and a selected value
  const select = document.createElement('select');
  for (let i = 0; i < options.length; i++) {
    const option = document.createElement('option');
    option.value = options[i];
    option.text = options[i]; // TODO this could be stylized here
    select.appendChild(option);
  }
  try {
    select.value = value;
  } catch (e) {
    console.error('selected value: ' + value + ' was not found');
  }
  return select;
}

/**
 * create a form that can be flipped to a json editor
 * @param  {any} dataobject
 * @return {Element}
 */
function createFlippableInputForm(dataobject) {
  const container = document.createElement('div');
  const editorview = document.createElement('pre'); // editor docs say use a pre
  editorview.classList.add('form-node-input');
  const editbutton = document.createElement('button');
  const returnbutton = document.createElement('button');
  let datatree = buildDataTree(dataobject);
  let inputview = renderDataTree(datatree);
  let editor = new JsonEditor(editorview, dataobject);
  inputview.style.display = 'block';
  editorview.style.display = 'none';
  editbutton.style.display = 'block';
  editbutton.innerHTML = 'Edit';
  returnbutton.style.display = 'none';
  returnbutton.innerHTML = 'Return';
  editbutton.addEventListener('click', function() {
    const newobject = objectFromDatatree(datatree);
    editor = new JsonEditor(editorview, newobject);
    dataobject = newobject;
    inputview.style.display = 'none';
    editorview.style.display = 'block';
    returnbutton.style.display = 'block';
    editbutton.style.display = 'none';
  });
  returnbutton.addEventListener('click', function() {
    let newjson = null;
    try {
      newjson = editor.get();
    } catch (e) {
      alert(e);
      return;
    }
    const newdatatree = buildDataTree(newjson);
    console.log('json: ', newjson);
    console.log('datatree: ', newdatatree);
    inputview = renderDataTree(newdatatree);
    container.appendChild(inputview);
    datatree = newdatatree;
    inputview.style.display = 'block';
    editorview.style.display = 'none';
    returnbutton.style.display = 'none';
    editbutton.style.display = 'block';
  });
  container.getValue = function() {
    const newobject = objectFromDatatree(datatree);
    editor = new JsonEditor(editorview, newobject);
    dataobject = newobject;
    const currentjson = editor.get();
    return currentjson;
  };
  editbutton.style.width = '60px';
  editbutton.style.height = '20px';
  returnbutton.style.width = '60px';
  returnbutton.style.height = '20px';
  container.appendChild(editbutton);
  container.appendChild(returnbutton);
  container.appendChild(inputview);
  container.appendChild(editorview);
  container.editor = editor;
  return container;
}

