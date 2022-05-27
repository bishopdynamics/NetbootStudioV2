// NSDataSource
//


class NSDataSource {
    constructor(mqtt_client, name, static_data, on_change) {
        this.mqtt_client = mqtt_client;
        this.name = name;
        this.onchange = on_change;
        this.static_data = static_data;
        this.value = {};
        this.value_json = JSON.stringify(this.value);
        this.mqtt_topic = 'NetbootStudio/DataSources/' + this.name;
        this.setup();
    }

    setup() {
        // subscribe to topic
        console.log('setting up data source: ' + this.name);
        this.mqtt_client.subscribe(this.mqtt_topic);
        let request_message = {
            message_type: 'request'
        }
        this.mqtt_client.publish(this.mqtt_topic, JSON.stringify(request_message));
        // you can have multiple instances registered with the same name, handle_message will be called for all of them
        DATA_SOURCE_REGISTER.push({
            name: this.name,
            object: this
        })
    }

    handle_message(message) {
        // handle messages on our topic
        try {
            let message_dict = JSON.parse(message);
            // we only care about new_value
            // console.log('message for: ' + this.name + ', ' + message);
            if (message_dict['message_type'] === 'new_value' || message_dict['message_type'] === 'current_value') {
                const new_json = JSON.stringify(message_dict['value'])
                if (this.value_json !== new_json) {
                    console.log('new value for data_source: ' + this.name + ', value: ', message_dict['value']);
                    this.value = message_dict['value'];
                    this.value_json = new_json;
                    this.onchange(this.value, this.static_data);
                }

            }
        } catch (e) {
            console.error('exception while handling new_value: ' + e);
        }
    }

    get_value() {
        return this.value;
    }
}