#!/usr/bin/env python3
# Netboot Studio library: Distributed Object

#    This file is part of Netboot Studio, a system for managing netboot clients
#    Copyright (C) 2020-2021 James Bishop (james@bishopdynamics.com)


import uuid

class DistributedObject:
    base_topic = '/DistributedObject'

    def __init__(self, seed_object=None):
        self.id = str(uuid.uuid4())
        self.topic = '%s/%s' % (self.base_topic, self.id)
        self.data = {}
        self.callbacks = {}
        if seed_object:
            self.data = seed_object
        self.start_sync()

    def start_sync(self):
        # setup all the subscriptions and connections to sync this object starting now

    def stop(self):
        # stop all sync processes/threads whatever

    def address_to_topic(self, address):
        # take address: some.thing.like.this
        #   and turn into /DistributedObject/3895086e-1ccb-4143-98a2-91ef8acb212b/some/thing/like/this
        object_topic = address.replace('.', '/')
        return '%s/%s' % (self.topic, object_topic)

    def subscribe_to_change(self, address, callback):
        # add a callback to execute when an address or one of its children changes


    def get(self, address):
        # take address: some.thing.like.this
        #   and turn it into self.data['some']['thing']['like']['this']
        #   then return the value of that key, or None

    def set(self, address, value):
        # take address: some.thing.like.this
        #   and turn it into self.data['some']['thing']['like']['this']
        #   then set that value to given (creating object chain as needed)
        #   then send an update message using address_to_topic()
        #       we can only really support objects that can be serialized and exist cross languages
        #       a value that is a dict, implies creation of a whole object, NOT setting that value to a json string or something stupid like that

